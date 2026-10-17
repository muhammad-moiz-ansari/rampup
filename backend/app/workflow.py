"""Transactional state changes; all mutations take the session row lock first."""

import hashlib
import json
from sqlalchemy import select
from app.errors import AppError, conflict
from app.models import (
    User,
    Task,
    Project,
    LearningSession,
    Message,
    Attempt,
    Escalation,
    AgentRun,
    Event,
    IdempotencyRequest,
    now,
)
from app.enums import Role
from app.schemas import SessionDetail, EscalationDetail


def require_role(user, role):
    if user.role != role:
        raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot perform this action.")


def task_access(db, task_id, user):
    task = db.get(Task, str(task_id))
    project = db.get(Project, task.project_id) if task else None
    assigned = task and (
        (user.role == Role.LEARNER and task.learner_id == user.id)
        or (user.role == Role.MENTOR and task.mentor_id == user.id)
    )
    if not assigned or project.workspace_id != user.workspace_id:
        raise AppError(404, "NOT_FOUND", "Task not found.")
    return task


def session_access(db, session_id, user, lock=False):
    query = select(LearningSession).where(LearningSession.id == str(session_id))
    if lock:
        query = query.with_for_update()
    session = db.scalar(query)
    if not session:
        raise AppError(404, "NOT_FOUND", "Session not found.")
    task_access(db, session.task_id, user)
    return session


def task_view(db, task):
    from app.walkthroughs import exercise_view, experience

    project = db.get(Project, task.project_id)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "repository": {
            "owner": project.owner,
            "name": project.name,
            "commit_sha": project.commit_sha,
        },
        **{
            key: task.policy[key]
            for key in ("assistance_mode", "protected_paths", "attempt_threshold")
        },
        "milestones": task.milestones,
        "exercise": exercise_view(task),
        "suggested_questions": (experience(task) or {}).get("questions", []),
    }


def record_view(record, fields):
    return {key: getattr(record, key) for key in fields.split()}


def messages(db, session_id):
    return [
        record_view(m, "id author content citations created_at")
        for m in db.scalars(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at, Message.id)
        )
    ]


def attempts(db, session_id):
    return [
        record_view(
            a,
            "id milestone_id explanation code file_paths test_output assessment assessment_note created_at",
        )
        for a in db.scalars(
            select(Attempt)
            .where(Attempt.session_id == session_id)
            .order_by(Attempt.created_at, Attempt.id)
        )
    ]


def case_summary(db, case):
    session = db.get(LearningSession, case.session_id)
    task = db.get(Task, session.task_id)
    return {
        **record_view(case, "id session_id reason status revision created_at"),
        "task_title": task.title,
        "learner_name": db.get(User, session.learner_id).name,
    }


def case_view(db, case, user):
    history = messages(db, case.session_id)
    mentor = user.role == Role.MENTOR
    return EscalationDetail.model_validate(
        {
            **case_summary(db, case),
            **record_view(
                case, "learner_question milestone_id unresolved_question evidence"
            ),
            "summary": case.summary
            if mentor
            else "A mentor is reviewing your question and repository evidence.",
            "attempts": attempts(db, case.session_id),
            "prior_hints": [m for m in history if m["author"] == "AI"],
            "proposed_guidance": case.proposed_guidance if mentor else "",
            "mentor_messages": [m for m in history if m["author"] == "MENTOR"],
        }
    ).model_dump(mode="json")


def open_case(db, session):
    return db.scalar(
        select(Escalation).where(
            Escalation.session_id == session.id, Escalation.status == "OPEN"
        )
    )


def touch(session):
    session.version += 1
    session.updated_at = now()


def expire_runs(db, session):
    runs = db.scalars(
        select(AgentRun).where(
            AgentRun.session_id == session.id, AgentRun.status == "RUNNING"
        )
    )
    for run in runs:
        if run.expires_at <= now():
            run.status, run.error_category, run.ended_at = "FAILED", "EXPIRED", now()
    db.flush()


def session_view(db, session, user):
    db.flush()
    case = open_case(db, session)
    run = db.scalar(
        select(AgentRun)
        .where(AgentRun.session_id == session.id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    result = {
        **record_view(
            session, "id task_id state current_milestone_id version updated_at"
        ),
        "task": task_view(db, db.get(Task, session.task_id)),
        "messages": messages(db, session.id),
        "attempts": attempts(db, session.id),
        "activity": [
            record_view(e, "id tool status summary created_at")
            for e in db.scalars(
                select(Event)
                .where(Event.session_id == session.id)
                .order_by(Event.created_at, Event.id)
            )
        ],
        "open_escalation": case_view(db, case, user) if case else None,
        "latest_run": {"id": run.id, "status": run.status} if run else None,
    }
    return SessionDetail.model_validate(result).model_dump(mode="json")


def begin_operation(db, user, route, key, body):
    digest = hashlib.sha256(
        json.dumps(
            body.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    operation = db.scalar(
        select(IdempotencyRequest).where(
            IdempotencyRequest.user_id == user.id,
            IdempotencyRequest.route == route,
            IdempotencyRequest.key == str(key),
        )
    )
    if operation:
        if operation.body_hash != digest:
            conflict(
                "IDEMPOTENCY_CONFLICT",
                "This key was already used with a different request body.",
            )
        return operation
    operation = IdempotencyRequest(
        user_id=user.id, route=route, key=str(key), body_hash=digest
    )
    db.add(operation)
    db.flush()
    return operation


def finish_operation(db, operation, session, user):
    result = session_view(db, session, user)
    operation.response, operation.status = result, "SUCCEEDED"
    db.commit()
    return result


def mutable(session):
    if session.state == "COMPLETED":
        conflict("SESSION_COMPLETED", "Completed sessions are read-only.")


def create_case(
    db, session, reason, question, summary=None, evidence=None, proposal=""
):
    mutable(session)
    case = open_case(db, session)
    if case:
        return case
    case = Escalation(
        session_id=session.id,
        reason=reason,
        milestone_id=session.current_milestone_id,
        learner_question=question,
        summary=summary or "Learner requested mentor support.",
        unresolved_question=question,
        evidence=evidence or [],
        proposed_guidance=proposal,
    )
    db.add(case)
    session.state = "WAITING_FOR_MENTOR"
    touch(session)
    for run in db.scalars(
        select(AgentRun).where(
            AgentRun.session_id == session.id, AgentRun.status == "RUNNING"
        )
    ):
        run.status, run.error_category, run.ended_at = "FAILED", "SUPERSEDED", now()
    db.flush()
    return case
