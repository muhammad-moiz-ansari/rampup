"""Save input before network work, then lock/version-check before saving any output."""

from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.errors import AppError, conflict
from app.models import (
    Task,
    Project,
    Message,
    Attempt,
    AgentRun,
    Event,
    SourceChunk,
    IdempotencyRequest,
    now,
)
from app.model_adapter import CoachResult
from app.repository import normalize_path, protected, citation, search_sources
from app.workflow import (
    session_access,
    begin_operation,
    finish_operation,
    mutable,
    open_case,
    create_case,
    touch,
    expire_runs,
    messages,
    attempts,
)


class SnapshotTools:
    def __init__(self, engine, project_id, session_id):
        self.engine, self.project_id, self.session_id = engine, project_id, session_id
        self.retrieved = {}
        self.events = []
        self.calls = 0

    def search(self, query):
        with Session(self.engine) as db:
            project = db.get(Project, self.project_id)
            sources = search_sources(db, project, query)
            for source in sources:
                self.retrieved[source.id] = citation(source, project)
            return [self.retrieved[source.id] for source in sources]

    def __call__(self, name, args):
        self.calls += 1
        if self.calls > 4:
            raise ValueError("Tool budget exceeded")
        try:
            if (
                name == "search_project_context"
                and set(args) == {"query"}
                and isinstance(args["query"], str)
            ):
                value = self.search(args["query"][:1000])
            elif name == "read_project_file" and set(args) == {
                "path",
                "start_line",
                "end_line",
            }:
                path = normalize_path(args["path"])
                start, end = args["start_line"], args["end_line"]
                if (
                    not isinstance(start, int)
                    or not isinstance(end, int)
                    or not 1 <= start <= end
                    or end - start > 79
                ):
                    raise ValueError("Read bounds exceeded")
                with Session(self.engine) as db:
                    project = db.get(Project, self.project_id)
                    if path not in project.allowed_paths:
                        raise ValueError("Path not allowlisted")
                    source = db.scalar(
                        select(SourceChunk).where(
                            SourceChunk.project_id == project.id,
                            SourceChunk.commit_sha == project.commit_sha,
                            SourceChunk.path == path,
                            SourceChunk.start_line <= start,
                            SourceChunk.end_line >= end,
                        )
                    )
                    if not source:
                        value = {"error": "Pinned excerpt not found"}
                    else:
                        # Track the actual returned subrange; model cannot cite unreturned lines.
                        value = citation(source, project, start, end)
                        self.retrieved[source.id] = value
            elif name == "get_learning_history" and not args:
                with Session(self.engine) as db:
                    value = {
                        "messages": messages(db, self.session_id)[-15:],
                        "attempts": attempts(db, self.session_id)[-5:],
                    }
                    # Convert timestamps for tool transport.
                    import json

                    value = json.loads(json.dumps(value, default=str))
            else:
                raise ValueError("Unknown or invalid read tool")
            self.events.append(
                (
                    name,
                    "SUCCEEDED",
                    "Read pinned repository snapshot or session history.",
                )
            )
            return value
        except (ValueError, TypeError):
            self.events.append(
                (name[:100], "FAILED", "Read tool rejected invalid scope or bounds.")
            )
            return {"error": "Read tool rejected invalid scope or bounds"}


def validate_citations(result, toolbox):
    validated = []
    for item in result.citations:
        source = toolbox.retrieved.get(item.source_id)
        if (
            not source
            or not source["start_line"]
            <= item.start_line
            <= item.end_line
            <= source["end_line"]
        ):
            raise ValueError("Invalid citation range or source")
        excerpt = "\n".join(
            source["excerpt"].splitlines()[
                item.start_line - source["start_line"] : item.end_line
                - source["start_line"]
                + 1
            ]
        )
        if not item.quote.strip() or item.quote not in excerpt:
            raise ValueError("Supporting quote does not belong to retrieved source")
        validated.append(
            {
                **source,
                "start_line": item.start_line,
                "end_line": item.end_line,
                "excerpt": excerpt,
                "url": source["url"].split("#")[0]
                + f"#L{item.start_line}-L{item.end_line}",
            }
        )
    return validated


def submit_input(db, user, session_id, body, key, kind, model):
    session = session_access(db, session_id, user, lock=True)
    route = f"/sessions/{session_id}/{'messages' if kind == 'message' else 'attempts'}"
    operation = begin_operation(db, user, route, key, body)
    if operation.status == "SUCCEEDED":
        return operation.response
    mutable(session)
    expire_runs(db, session)
    # Clarifications and mentor messages must remain available during an in-flight model call.
    human_only = user.role == "MENTOR" or session.state in (
        "WAITING_FOR_MENTOR",
        "MENTOR_ACTIVE",
        "COMPLETION_REVIEW",
    )
    running = db.scalar(
        select(AgentRun).where(
            AgentRun.session_id == session.id, AgentRun.status == "RUNNING"
        )
    )
    if running and not human_only:
        conflict(
            "RUN_IN_PROGRESS",
            "A coach turn is already running. Retry after it finishes.",
        )
    if kind == "attempt" and session.state != "ACTIVE":
        conflict(
            "WAITING_FOR_MENTOR",
            "Add a clarification while the mentor reviews; attempts resume in ACTIVE.",
        )
    task = db.get(Task, session.task_id)
    if kind == "attempt":
        if body.milestone_id != session.current_milestone_id:
            raise AppError(
                422, "INVALID_MILESTONE", "Attempt must match the current milestone."
            )
        try:
            paths = [normalize_path(p) for p in body.file_paths]
        except ValueError:
            raise AppError(
                422, "INVALID_PATH", "Use safe repository-relative file paths."
            ) from None
    if operation.input_id:
        saved = db.get(Message if kind == "message" else Attempt, operation.input_id)
    else:
        if kind == "message":
            saved = Message(
                session_id=session.id, author=user.role, content=body.content
            )
        else:
            saved = Attempt(
                session_id=session.id,
                milestone_id=body.milestone_id,
                explanation=body.explanation,
                code=body.code,
                file_paths=paths,
                test_output=body.test_output,
            )
        db.add(saved)
        db.flush()
        operation.input_id = saved.id
        touch(session)
        case = open_case(db, session)
        if case:
            case.revision += 1
    if human_only:
        return finish_operation(db, operation, session, user)
    query = saved.content if kind == "message" else saved.explanation
    if kind == "attempt" and any(
        protected(p, task.policy["protected_paths"]) for p in saved.file_paths
    ):
        saved.assessment, saved.assessment_note, saved.assessed = (
            "NEEDS_REVIEW",
            "Supplied path matches protected policy; mentor review required.",
            True,
        )
        create_case(
            db,
            session,
            "PROTECTED_PATH",
            query,
            summary="An explicit attempt includes a protected path.",
        )
        return finish_operation(db, operation, session, user)
    project = db.get(Project, task.project_id)
    run = AgentRun(
        session_id=session.id,
        request_key=str(key),
        input_id=saved.id,
        input_kind=kind,
        session_version=session.version,
        expires_at=now() + timedelta(seconds=50),
    )
    db.add(run)
    db.flush()
    run_id, operation_id, project_id, version = (
        run.id,
        operation.id,
        project.id,
        session.version,
    )
    history = [
        {"author": m["author"], "content": m["content"][:2000]}
        for m in messages(db, session.id)[-12:]
    ]
    context = {
        "task": task.description,
        "policy": task.policy,
        "milestone_id": session.current_milestone_id,
        "input_kind": kind,
        "input": body.model_dump(mode="json"),
        "history": history,
    }
    conflict_pair = task.policy.get("configured_conflict", [])
    engine = db.get_bind()
    db.commit()  # Input/run are durable; release row locks before retrieval or network calls.
    toolbox = SnapshotTools(engine, project_id, str(session_id))
    try:
        evidence = toolbox.search(query)
        context["evidence"] = evidence
        result, verified, escalation_reason = None, [], None
        # Configured consistency question is explicit task policy, not simulated general reasoning.
        pair_sources = [s for s in evidence if s["path"] in conflict_pair]
        if len({s["path"] for s in pair_sources}) == 2:
            escalation_reason = "SOURCE_CONFLICT"
            verified = pair_sources
        elif not evidence:
            escalation_reason = "MISSING_EVIDENCE"
        else:
            result = CoachResult.model_validate(model.generate(context, toolbox))
            if (
                result.milestone_id != context["milestone_id"]
                or len(result.message) > 8000
            ):
                raise ValueError("Invalid model milestone or output size")
            verified = validate_citations(result, toolbox)
            for path in result.proposed_file_paths:
                if protected(path, context["policy"]["protected_paths"]):
                    escalation_reason = "PROTECTED_PATH"
            if result.action == "ESCALATE":
                if not result.escalation:
                    raise ValueError("Missing structured escalation")
                escalation_reason = result.escalation.reason
                if not set(result.escalation.evidence_source_ids) <= {
                    c["source_id"] for c in verified
                }:
                    raise ValueError("Escalation evidence was not cited")
                if (
                    escalation_reason == "SOURCE_CONFLICT"
                    and len({c["source_id"] for c in verified}) < 2
                ):
                    raise ValueError("Source conflict requires two valid excerpts")
            elif not verified:
                escalation_reason = "MISSING_EVIDENCE"
            else:
                review_context = {
                    **context,
                    "evidence": list(toolbox.retrieved.values()),
                }
                review = model.review(review_context, result)
                if (
                    not review.supported
                    or not review.policy_compatible
                    or "```" in result.message
                ):
                    escalation_reason = "MISSING_EVIDENCE"
        # Reacquire a fresh snapshot after network work; no late result can cross a case/version change.
        db.expire_all()
        session = session_access(db, session_id, user, lock=True)
        run = db.get(AgentRun, run_id)
        operation = db.get(IdempotencyRequest, operation_id)
        if (
            run.status != "RUNNING"
            or run.expires_at <= now()
            or session.version != version
            or session.state != "ACTIVE"
            or open_case(db, session)
        ):
            if run.status == "RUNNING":
                run.status, run.error_category, run.ended_at = (
                    "FAILED",
                    "SUPERSEDED",
                    now(),
                )
            return finish_operation(db, operation, session, user)
        saved = db.get(Message if kind == "message" else Attempt, operation.input_id)
        if kind == "attempt" and result and result.attempt_assessment:
            saved.assessment = result.attempt_assessment.classification
            saved.assessment_note = (
                "AI assessment (tests not executed): "
                + result.attempt_assessment.rationale[:2000]
            )
            saved.assessed = True
            db.flush()
            recent = list(
                db.scalars(
                    select(Attempt)
                    .where(
                        Attempt.session_id == session.id,
                        Attempt.milestone_id == session.current_milestone_id,
                        Attempt.assessed.is_(True),
                    )
                    .order_by(Attempt.created_at.desc())
                )
            )
            consecutive = 0
            for attempt in recent:
                if attempt.assessment == "PROGRESS":
                    break
                if attempt.assessment == "UNRESOLVED":
                    consecutive += 1
            if consecutive >= context["policy"]["attempt_threshold"]:
                escalation_reason = "REPEATED_ATTEMPTS"
            if saved.assessment == "PROGRESS" and not escalation_reason:
                milestones = db.get(Task, session.task_id).milestones
                index = next(
                    i
                    for i, m in enumerate(milestones)
                    if m["id"] == session.current_milestone_id
                )
                if index + 1 < len(milestones):
                    session.current_milestone_id = milestones[index + 1]["id"]
        if escalation_reason == "MISSING_EVIDENCE":
            session.missing_evidence_count += 1
            if session.missing_evidence_count < 2:
                db.add(
                    Message(
                        session_id=session.id,
                        author="AI",
                        content="I need a supporting repository excerpt before guiding this change. Which file or current behavior are you asking about?",
                    )
                )
                escalation_reason = None
                result = None
        else:
            session.missing_evidence_count = 0
        if escalation_reason:
            proposed = (
                result.escalation.proposed_guidance
                if result and result.escalation
                else (result.message if result else "")
            )
            summary = (
                result.escalation.summary
                if result and result.escalation
                else (
                    "Configured demo consistency question: outdated README conflicts with current schema guidance."
                    if escalation_reason == "SOURCE_CONFLICT"
                    else "Repository guidance requires human review."
                )
            )
            run.status, run.ended_at = "SUCCEEDED", now()
            create_case(
                db,
                session,
                escalation_reason,
                query,
                summary=summary,
                evidence=verified,
                proposal=proposed[:8000],
            )
        elif result:
            db.add(
                Message(
                    session_id=session.id,
                    author="AI",
                    content=result.message,
                    citations=verified,
                )
            )
        for tool, status, summary in toolbox.events:
            db.add(
                Event(session_id=session.id, tool=tool, status=status, summary=summary)
            )
        db.add(
            Event(
                session_id=session.id,
                tool="pinned_context",
                status="SUCCEEDED",
                summary=f"Read {len(evidence)} saved excerpts at the task's pinned commit; no code executed.",
            )
        )
        run.status, run.ended_at = "SUCCEEDED", now()
        touch(session)
        return finish_operation(db, operation, session, user)
    except Exception:
        db.rollback()
        db.expire_all()
        session = session_access(db, session_id, user, lock=True)
        run = db.get(AgentRun, run_id)
        operation = db.get(IdempotencyRequest, operation_id)
        if run.status != "RUNNING":
            return finish_operation(db, operation, session, user)
        run.status, run.error_category, run.ended_at = (
            "FAILED",
            "UPSTREAM_OR_VALIDATION",
            now(),
        )
        operation.status = "FAILED"
        db.add(
            Event(
                session_id=session.id,
                tool="coach",
                status="FAILED",
                summary="Coach failed or returned unsupported output. Input is saved; retry with the same key or request a mentor.",
            )
        )
        db.commit()
        raise AppError(
            503,
            "COACH_FAILED",
            "Your input was saved. Retry with the same key or request a mentor.",
            True,
        ) from None
