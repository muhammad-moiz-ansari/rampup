"""Save input before network work, then lock/version-check before saving any output."""

from datetime import timedelta
import httpx
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
    Escalation,
    MentorDecision,
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

COACH_FAILURE_MESSAGES = {
    "MODEL_NOT_CONFIGURED": "AI coaching is not configured on the server. Check the server-side model and API key settings.",
    "MODEL_AUTH": "The AI provider rejected its server-side credentials. Check the API key and provider permissions.",
    "MODEL_RATE_LIMIT": "The AI provider is rate-limiting requests. Wait briefly, then retry.",
    "MODEL_CONFIGURATION": "The AI provider rejected the configured model or request settings. Check the server-side model configuration.",
    "MODEL_TIMEOUT": "The AI provider did not respond before the request timed out. Retry the saved request.",
    "MODEL_OUTPUT_INVALID": "The AI provider returned a response RampUp could not validate. Retry or ask your mentor.",
    "MODEL_UPSTREAM": "The AI provider returned an upstream error. Retry the saved request or ask your mentor.",
    "COACH_FAILURE": "AI coaching failed unexpectedly. Retry the saved request or ask your mentor.",
}
MODEL_HTTP_FAILURE_CATEGORIES = {
    400: "MODEL_CONFIGURATION",
    401: "MODEL_AUTH",
    403: "MODEL_AUTH",
    404: "MODEL_CONFIGURATION",
    429: "MODEL_RATE_LIMIT",
}


def model_http_failure_category(error):
    if error.response.status_code == 400:
        try:
            payload = error.response.json()
        except ValueError:
            payload = {}
        details = payload.get("error", {}).get("details", [])
        reasons = {
            detail.get("reason")
            for detail in details
            if isinstance(detail, dict)
        }
        provider_message = payload.get("error", {}).get("message", "").lower()
        if reasons.intersection({"API_KEY_INVALID", "API_KEY_SERVICE_BLOCKED"}) or (
            "api key not valid" in provider_message
        ):
            return "MODEL_AUTH"
    return MODEL_HTTP_FAILURE_CATEGORIES.get(
        error.response.status_code, "MODEL_UPSTREAM"
    )


class SnapshotTools:
    def __init__(self, engine, project_id, session_id, commit_sha=None):
        self.engine, self.project_id, self.session_id = engine, project_id, session_id
        with Session(engine) as db:
            self.commit_sha = commit_sha or db.get(Project, project_id).commit_sha
        self.retrieved = {}
        self.events = []
        self.calls = 0

    def search(self, query):
        with Session(self.engine) as db:
            project = db.get(Project, self.project_id)
            sources = search_sources(db, project, query, commit_sha=self.commit_sha)
            selected, budget = [], 12000
            for source in sources:
                item = citation(source, project)
                size = len(item["excerpt"])
                if size > 8000 or size > budget:
                    continue
                budget -= size
                self.retrieved[source.id] = item
                selected.append(item)
            return selected

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
                            SourceChunk.commit_sha == self.commit_sha,
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
                        if len(value["excerpt"]) > 8000:
                            raise ValueError("Read text budget exceeded")
                        self.retrieved[source.id] = value
            elif name == "get_learning_history" and not args:
                with Session(self.engine) as db:
                    value = {
                        "messages": messages(db, self.session_id)[-15:],
                        "attempts": attempts(db, self.session_id)[-5:],
                    }
                    value["messages"] = [
                        {"author": m["author"], "content": m["content"][:800]}
                        for m in value["messages"][-8:]
                    ]
                    value["attempts"] = [
                        {
                            "milestone_id": a["milestone_id"],
                            "explanation": a["explanation"][:800],
                            "assessment": a["assessment"],
                        }
                        for a in value["attempts"][-3:]
                    ]
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
    if kind == "attempt" and any(
        protected(p, task.policy["protected_paths"]) for p in saved.file_paths
    ):
        saved.assessment, saved.assessment_note, saved.assessed = (
            "NEEDS_REVIEW",
            "Supplied path matches protected policy; mentor review required.",
            True,
        )
        run.status, run.ended_at = "SUCCEEDED", now()
        create_case(
            db,
            session,
            "PROTECTED_PATH",
            query,
            summary="An explicit attempt includes a protected path.",
        )
        return finish_operation(db, operation, session, user)
    run_id, operation_id, project_id, version = (
        run.id,
        operation.id,
        project.id,
        session.version,
    )
    history = [
        {"author": m["author"], "content": m["content"][:1000]}
        for m in messages(db, session.id)[-8:]
    ]
    context = {
        "task": task.description,
        "policy": task.policy,
        "milestone_id": session.current_milestone_id,
        "input_kind": kind,
        "input": body.model_dump(mode="json"),
        "history": history,
    }
    payload = context["input"]
    for field, limit in (
        ("content", 6000),
        ("explanation", 3000),
        ("code", 6000),
        ("test_output", 2000),
    ):
        if isinstance(payload.get(field), str) and len(payload[field]) > limit:
            payload[field] = payload[field][:limit]
            context.setdefault("truncated_input_fields", []).append(field)
    if "file_paths" in payload:
        payload["file_paths"] = payload["file_paths"][:10]
    approved = db.scalars(
        select(MentorDecision)
        .join(Escalation)
        .where(
            Escalation.session_id == session.id,
            Escalation.milestone_id == session.current_milestone_id,
            Escalation.status == "RESOLVED",
            MentorDecision.action == "SEND_GUIDANCE",
        )
        .order_by(MentorDecision.created_at.desc())
        .limit(2)
    )
    context["approved_guidance"] = [decision.text[:1500] for decision in approved]
    conflict_pair = task.policy.get("configured_conflict", [])
    pinned_sha = project.commit_sha
    # A human resolution applies to this session/milestone and exact pinned evidence.
    # Do not reopen the same configured question on every subsequent learner turn.
    resolved = db.scalars(
        select(Escalation).where(
            Escalation.session_id == session.id,
            Escalation.milestone_id == session.current_milestone_id,
            Escalation.reason == "SOURCE_CONFLICT",
            Escalation.status == "RESOLVED",
        )
    )
    for previous in resolved:
        paths = {
            item["path"]
            for item in previous.evidence
            if item["commit_sha"] == pinned_sha
        }
        if conflict_pair and set(conflict_pair) <= paths:
            conflict_pair = []
            context["resolved_consistency_question"] = previous.unresolved_question
            break
    engine = db.get_bind()
    db.commit()  # Input/run are durable; release row locks before retrieval or network calls.
    toolbox = SnapshotTools(engine, project_id, str(session_id), pinned_sha)
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
            protected_proposal = any(
                protected(path, context["policy"]["protected_paths"])
                for path in result.proposed_file_paths
            )
            try:
                verified = validate_citations(result, toolbox)
            except ValueError:
                if not protected_proposal:
                    raise
            if protected_proposal:
                escalation_reason = "PROTECTED_PATH"
            elif result.action == "ESCALATE":
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
                    "evidence": verified,
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
            run.status == "RUNNING" and run.expires_at <= now()
        ) or run.error_category == "EXPIRED":
            run.status, run.error_category, run.ended_at = "FAILED", "EXPIRED", now()
            # An older expired call cannot finalize a new run for this saved input.
            active = db.scalar(
                select(AgentRun).where(
                    AgentRun.session_id == session.id,
                    AgentRun.status == "RUNNING",
                    AgentRun.id != run.id,
                )
            )
            if active:
                db.commit()
                raise AppError(
                    409,
                    "RUN_IN_PROGRESS",
                    "A retry is already running for this saved input.",
                )
            operation.status = "FAILED"
            db.commit()
            raise AppError(
                503,
                "RUN_EXPIRED",
                "Your input was saved. Retry with the same key or request a mentor.",
                True,
            )
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
    except AppError:
        raise
    except Exception as error:
        db.rollback()
        db.expire_all()
        session = session_access(db, session_id, user, lock=True)
        run = db.get(AgentRun, run_id)
        operation = db.get(IdempotencyRequest, operation_id)
        if run.status != "RUNNING":
            return finish_operation(db, operation, session, user)
        category = "COACH_FAILURE"
        if isinstance(error, (httpx.TimeoutException, TimeoutError)):
            category = "MODEL_TIMEOUT"
        elif isinstance(error, httpx.HTTPStatusError):
            category = model_http_failure_category(error)
        elif isinstance(error, RuntimeError) and str(error) == "MODEL_NOT_CONFIGURED":
            category = "MODEL_NOT_CONFIGURED"
        elif isinstance(error, ValueError):
            category = "MODEL_OUTPUT_INVALID"
        run.status, run.error_category, run.ended_at = (
            "FAILED",
            category,
            now(),
        )
        operation.status = "FAILED"
        db.add(
            Event(
                session_id=session.id,
                tool="coach",
                status="FAILED",
                summary=f"{COACH_FAILURE_MESSAGES[category]} Learner input is saved.",
            )
        )
        db.commit()
        raise AppError(
            503,
            "COACH_FAILED",
            f"Your input was saved, but {COACH_FAILURE_MESSAGES[category]} Retry the original request with the same key or ask your mentor.",
            True,
        ) from None
