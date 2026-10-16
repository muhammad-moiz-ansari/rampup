from datetime import timezone
from typing import Literal, Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AfterValidator, AwareDatetime
from app.enums import (
    Role,
    SessionState,
    CaseStatus,
    Reason,
    AssistanceMode,
    DecisionAction,
    MessageAuthor,
    RunStatus,
    Assessment,
)

UTCDateTime = Annotated[
    AwareDatetime, AfterValidator(lambda value: value.astimezone(timezone.utc))
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Strict):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class UserOut(Strict):
    id: UUID
    name: str
    role: Role


class LoginOut(Strict):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: UTCDateTime
    user: UserOut


class Repository(Strict):
    owner: str
    name: str
    commit_sha: str


class Milestone(Strict):
    id: str
    title: str
    criteria: list[str]


class TaskOut(Strict):
    id: UUID
    title: str
    description: str
    repository: Repository
    assistance_mode: AssistanceMode
    protected_paths: list[str]
    attempt_threshold: int
    milestones: list[Milestone]


class Citation(Strict):
    source_id: UUID
    path: str
    commit_sha: str
    start_line: int
    end_line: int
    excerpt: str
    url: str


class MessageOut(Strict):
    id: UUID
    author: MessageAuthor
    content: str
    citations: list[Citation]
    created_at: UTCDateTime


class AttemptOut(Strict):
    id: UUID
    milestone_id: str
    explanation: str
    code: str
    file_paths: list[str]
    test_output: str | None
    assessment: Assessment
    assessment_note: str
    created_at: UTCDateTime


class Activity(Strict):
    id: UUID
    tool: str
    status: Literal["SUCCEEDED", "FAILED"]
    summary: str
    created_at: UTCDateTime


class EscalationSummary(Strict):
    id: UUID
    session_id: UUID
    task_title: str
    learner_name: str
    reason: Reason
    status: CaseStatus
    revision: int
    created_at: UTCDateTime


class EscalationDetail(EscalationSummary):
    learner_question: str
    milestone_id: str
    summary: str
    unresolved_question: str
    evidence: list[Citation]
    attempts: list[AttemptOut]
    prior_hints: list[MessageOut]
    proposed_guidance: str
    mentor_messages: list[MessageOut]


class SessionSummary(Strict):
    id: UUID
    task_title: str
    learner_name: str
    state: SessionState
    version: int
    updated_at: UTCDateTime


class RunOut(Strict):
    id: UUID
    status: RunStatus


class SessionDetail(Strict):
    id: UUID
    task_id: UUID
    task: TaskOut
    state: SessionState
    current_milestone_id: str
    version: int
    messages: list[MessageOut]
    attempts: list[AttemptOut]
    activity: list[Activity]
    open_escalation: EscalationDetail | None
    latest_run: RunOut | None
    updated_at: UTCDateTime


class TaskList(Strict):
    items: list[TaskOut]


class CaseList(Strict):
    items: list[EscalationSummary]


class SessionList(Strict):
    items: list[SessionSummary]


class SessionCreate(Strict):
    task_id: UUID


class MessageCreate(Strict):
    content: str = Field(min_length=1, max_length=8000)


class AttemptCreate(Strict):
    milestone_id: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=8000)
    code: str = Field(default="", max_length=16000)
    file_paths: list[str] = Field(default_factory=list, max_length=30)
    test_output: str | None = Field(default=None, max_length=8000)


class EscalationCreate(Strict):
    reason: Literal["MANUAL"] = "MANUAL"
    question: str = Field(min_length=1, max_length=8000)


class DecisionCreate(Strict):
    action: DecisionAction
    expected_revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=8000)


class CompletionRequest(Strict):
    expected_version: int = Field(ge=1)


class CompletionDecision(CompletionRequest):
    approved: bool
    text: str = Field(min_length=1, max_length=8000)
