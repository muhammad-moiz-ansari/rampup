from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import current_user, issue_token, passwords, public_user
from app.db import get_db
from app.errors import AppError, conflict
from app.models import (
    User,
    Task,
    LearningSession,
    Message,
    Escalation,
    MentorDecision,
    SourceChunk,
    Project,
)
from app.schemas import (
    Login,
    LoginOut,
    UserOut,
    TaskList,
    TaskOut,
    SessionCreate,
    SessionDetail,
    MessageCreate,
    AttemptCreate,
    EscalationCreate,
    CaseList,
    EscalationDetail,
    DecisionCreate,
    CompletionRequest,
    CompletionDecision,
    SessionList,
    Citation,
)
from app.workflow import (
    require_role,
    task_access,
    session_access,
    task_view,
    case_summary,
    case_view,
    session_view,
    begin_operation,
    finish_operation,
    touch,
    mutable,
    open_case,
    create_case,
    expire_runs,
)

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]
Key = Annotated[UUID, Header(alias="Idempotency-Key")]


@router.post("/auth/login", response_model=LoginOut)
def login(body: Login, db: DB):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    # Always verify a real hash to avoid distinguishing nonexistent accounts by timing.
    hashed = user.password_hash if user else DUMMY_HASH
    if not passwords.verify(body.password, hashed) or user is None:
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    return issue_token(user)


DUMMY_HASH = passwords.hash("unused-dummy-login-value")


@router.get("/auth/me", response_model=UserOut)
def me(user: Actor):
    return public_user(user)


@router.get("/tasks", response_model=TaskList)
def tasks(db: DB, user: Actor):
    field = Task.mentor_id if user.role == "MENTOR" else Task.learner_id
    assigned = list(
        db.scalars(
            select(Task).where(field == user.id).order_by(Task.created_at, Task.id)
        )
    )
    current = [task for task in assigned if task.policy.get("walkthrough_id")]
    return {
        "items": [
            task_view(db, task_access(db, t.id, user)) for t in (current or assigned)
        ]
    }


@router.get("/tasks/{task_id}", response_model=TaskOut)
def task_detail(task_id: UUID, db: DB, user: Actor):
    return task_view(db, task_access(db, task_id, user))


@router.post("/sessions", response_model=SessionDetail)
def start_session(body: SessionCreate, key: Key, db: DB, user: Actor):
    require_role(user, "LEARNER")
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    task = task_access(db, body.task_id, user)
    operation = begin_operation(db, user, "/sessions", key, body)
    if operation.status == "SUCCEEDED":
        return operation.response
    session = db.scalar(
        select(LearningSession).where(
            LearningSession.task_id == task.id, LearningSession.learner_id == user.id
        )
    )
    if session is None:
        session = LearningSession(
            task_id=task.id,
            learner_id=user.id,
            current_milestone_id=task.milestones[0]["id"],
        )
        db.add(session)
        db.flush()
    return finish_operation(db, operation, session, user)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def session_detail(session_id: UUID, db: DB, user: Actor):
    session = session_access(db, session_id, user, lock=True)
    expire_runs(db, session)
    result = session_view(db, session, user)
    db.commit()
    return result


@router.post("/sessions/{session_id}/messages", response_model=SessionDetail)
def add_message(
    session_id: UUID,
    body: MessageCreate,
    key: Key,
    request: Request,
    db: DB,
    user: Actor,
):
    from app.coach import submit_input

    return submit_input(
        db, user, session_id, body, key, "message", request.app.state.model
    )


@router.post("/sessions/{session_id}/attempts", response_model=SessionDetail)
def add_attempt(
    session_id: UUID,
    body: AttemptCreate,
    key: Key,
    request: Request,
    db: DB,
    user: Actor,
):
    from app.coach import submit_input

    require_role(user, "LEARNER")
    return submit_input(
        db, user, session_id, body, key, "attempt", request.app.state.model
    )


@router.post("/sessions/{session_id}/escalations", response_model=SessionDetail)
def escalate(session_id: UUID, body: EscalationCreate, key: Key, db: DB, user: Actor):
    require_role(user, "LEARNER")
    session = session_access(db, session_id, user, lock=True)
    operation = begin_operation(
        db, user, f"/sessions/{session_id}/escalations", key, body
    )
    if operation.status == "SUCCEEDED":
        return operation.response
    mutable(session)
    if session.state == "COMPLETION_REVIEW":
        conflict()
    create_case(db, session, "MANUAL", body.question)
    return finish_operation(db, operation, session, user)


@router.get("/mentor/escalations", response_model=CaseList)
def mentor_queue(db: DB, user: Actor, status: str = "OPEN"):
    require_role(user, "MENTOR")
    if status not in ("OPEN", "RESOLVED"):
        raise AppError(422, "INVALID_STATUS", "Use OPEN or RESOLVED.")
    query = (
        select(Escalation)
        .join(LearningSession)
        .join(Task)
        .where(Task.mentor_id == user.id, Escalation.status == status)
    )
    return {"items": [case_summary(db, case) for case in db.scalars(query)]}


@router.get("/escalations/{case_id}", response_model=EscalationDetail)
def escalation_detail(case_id: UUID, db: DB, user: Actor):
    case = db.get(Escalation, str(case_id))
    if case is None:
        raise AppError(404, "NOT_FOUND", "Case not found.")
    session_access(db, case.session_id, user)
    return case_view(db, case, user)


@router.post("/escalations/{case_id}/decision", response_model=SessionDetail)
def decision(case_id: UUID, body: DecisionCreate, key: Key, db: DB, user: Actor):
    require_role(user, "MENTOR")
    case = db.get(Escalation, str(case_id))
    if case is None:
        raise AppError(404, "NOT_FOUND", "Case not found.")
    session = session_access(db, case.session_id, user, lock=True)
    db.refresh(case, with_for_update=True)
    operation = begin_operation(db, user, f"/escalations/{case_id}/decision", key, body)
    if operation.status == "SUCCEEDED":
        return operation.response
    if case.revision != body.expected_revision:
        conflict(
            "STALE_REVISION", "This case changed. Refresh before sending guidance."
        )
    if case.status != "OPEN" or session.state not in (
        "WAITING_FOR_MENTOR",
        "MENTOR_ACTIVE",
    ):
        conflict()
    db.add(
        MentorDecision(
            case_id=case.id,
            reviewer_id=user.id,
            action=body.action,
            text=body.text,
            request_key=str(key),
            reviewed_revision=case.revision,
            proposal_snapshot=case.proposed_guidance,
        )
    )
    if body.action != "REJECT_SUGGESTION":
        db.add(
            Message(
                session_id=session.id,
                case_id=case.id,
                author="MENTOR",
                content=body.text,
            )
        )
    else:
        case.proposed_guidance = (
            ""  # Original proposal retained in mentor-only decision audit below.
        )
    if body.action == "SEND_GUIDANCE":
        case.status, session.state = "RESOLVED", "ACTIVE"
    elif body.action == "TAKE_OVER":
        session.state = "MENTOR_ACTIVE"
    case.revision += 1
    touch(session)
    return finish_operation(db, operation, session, user)


@router.post("/sessions/{session_id}/completion-request", response_model=SessionDetail)
def request_completion(
    session_id: UUID, body: CompletionRequest, key: Key, db: DB, user: Actor
):
    require_role(user, "LEARNER")
    session = session_access(db, session_id, user, lock=True)
    operation = begin_operation(
        db, user, f"/sessions/{session_id}/completion-request", key, body
    )
    if operation.status == "SUCCEEDED":
        return operation.response
    expire_runs(db, session)
    from app.models import AgentRun

    if db.scalar(
        select(AgentRun).where(
            AgentRun.session_id == session.id, AgentRun.status == "RUNNING"
        )
    ):
        conflict(
            "RUN_IN_PROGRESS",
            "Wait for the current coach turn before requesting completion.",
        )
    if session.version != body.expected_version:
        conflict(
            "STALE_VERSION", "Session changed. Refresh before requesting completion."
        )
    if session.state != "ACTIVE" or open_case(db, session):
        conflict()
    session.state = "COMPLETION_REVIEW"
    touch(session)
    return finish_operation(db, operation, session, user)


@router.get("/mentor/completion-reviews", response_model=SessionList)
def completion_queue(db: DB, user: Actor):
    require_role(user, "MENTOR")
    sessions = db.scalars(
        select(LearningSession)
        .join(Task)
        .where(Task.mentor_id == user.id, LearningSession.state == "COMPLETION_REVIEW")
    )
    return {
        "items": [
            {
                "id": s.id,
                "task_title": db.get(Task, s.task_id).title,
                "learner_name": db.get(User, s.learner_id).name,
                "state": s.state,
                "version": s.version,
                "updated_at": s.updated_at,
            }
            for s in sessions
        ]
    }


@router.post("/sessions/{session_id}/completion-decision", response_model=SessionDetail)
def decide_completion(
    session_id: UUID, body: CompletionDecision, key: Key, db: DB, user: Actor
):
    require_role(user, "MENTOR")
    session = session_access(db, session_id, user, lock=True)
    operation = begin_operation(
        db, user, f"/sessions/{session_id}/completion-decision", key, body
    )
    if operation.status == "SUCCEEDED":
        return operation.response
    if session.version != body.expected_version:
        conflict(
            "STALE_VERSION", "Session changed. Refresh before reviewing completion."
        )
    if session.state != "COMPLETION_REVIEW":
        conflict()
    session.state = "COMPLETED" if body.approved else "ACTIVE"
    db.add(Message(session_id=session.id, author="MENTOR", content=body.text))
    touch(session)
    return finish_operation(db, operation, session, user)


@router.get("/sources/{source_id}", response_model=Citation)
def source_detail(source_id: UUID, db: DB, user: Actor):
    from app.repository import citation

    source = db.get(SourceChunk, str(source_id))
    field = Task.mentor_id if user.role == "MENTOR" else Task.learner_id
    task = (
        db.scalar(
            select(Task).where(Task.project_id == source.project_id, field == user.id)
        )
        if source
        else None
    )
    if not task:
        raise AppError(404, "NOT_FOUND", "Source not found.")
    task_access(db, task.id, user)
    return citation(source, db.get(Project, source.project_id))
