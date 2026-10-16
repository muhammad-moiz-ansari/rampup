from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Text,
    Integer,
    ForeignKey,
    DateTime,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    workspace_id: Mapped[str] = mapped_column(Uuid(as_uuid=False))


class Project(Record, Base):
    __tablename__ = "projects"
    workspace_id: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    owner: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    commit_sha: Mapped[str] = mapped_column(String(40), default="")
    allowed_paths: Mapped[list] = mapped_column(JSONB, default=list)


class Task(Record, Base):
    __tablename__ = "tasks"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    learner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    mentor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    policy: Mapped[dict] = mapped_column(JSONB)
    milestones: Mapped[list] = mapped_column(JSONB)


class LearningSession(Record, Base):
    __tablename__ = "sessions"
    __table_args__ = (UniqueConstraint("task_id", "learner_id"),)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    learner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    current_milestone_id: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    version: Mapped[int] = mapped_column(Integer, default=1)
    missing_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Message(Record, Base):
    __tablename__ = "messages"
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    author: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    case_id: Mapped[str | None] = mapped_column(
        ForeignKey("escalations.id"), nullable=True
    )


class Attempt(Record, Base):
    __tablename__ = "attempts"
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    milestone_id: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    file_paths: Mapped[list] = mapped_column(JSONB)
    test_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str] = mapped_column(String(30), default="UNRESOLVED")
    assessment_note: Mapped[str] = mapped_column(
        Text, default="Not yet assessed; learner output is unverified."
    )
    assessed: Mapped[bool] = mapped_column(default=False)


class SourceChunk(Record, Base):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint("project_id", "commit_sha", "path", "start_line"),
        Index("ix_source_search", "search_document", postgresql_using="gin"),
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    commit_sha: Mapped[str] = mapped_column(String(40))
    path: Mapped[str] = mapped_column(String(400))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    search_document: Mapped[str] = mapped_column(TSVECTOR)


class Escalation(Record, Base):
    __tablename__ = "escalations"
    __table_args__ = (
        Index(
            "uq_open_case",
            "session_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    reason: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    milestone_id: Mapped[str] = mapped_column(String(100))
    learner_question: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    unresolved_question: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    proposed_guidance: Mapped[str] = mapped_column(Text, default="")


class MentorDecision(Record, Base):
    __tablename__ = "mentor_decisions"
    case_id: Mapped[str] = mapped_column(ForeignKey("escalations.id"))
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    request_key: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    reviewed_revision: Mapped[int] = mapped_column(Integer)
    proposal_snapshot: Mapped[str] = mapped_column(Text, default="")


class AgentRun(Record, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index(
            "uq_active_run",
            "session_id",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
        ),
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    request_key: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    error_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_id: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    input_kind: Mapped[str] = mapped_column(String(20))
    session_version: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Event(Record, Base):
    __tablename__ = "events"
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    tool: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)


class IdempotencyRequest(Record, Base):
    __tablename__ = "idempotency_requests"
    __table_args__ = (UniqueConstraint("user_id", "route", "key"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    route: Mapped[str] = mapped_column(String(300))
    key: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    body_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    input_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
