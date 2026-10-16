## 4. Shared API contract

All application routes use `/api/v1`. IDs are strings containing UUIDs. Timestamps are UTC ISO 8601 strings. JSON field names use `snake_case`. All mutation requests except login carry an `Idempotency-Key` UUID header. Protected routes use `Authorization: Bearer <token>`.

### Enumerations

```text
Role: LEARNER | MENTOR
SessionState: ACTIVE | WAITING_FOR_MENTOR | MENTOR_ACTIVE |
              COMPLETION_REVIEW | COMPLETED
CaseStatus: OPEN | RESOLVED
Reason: MANUAL | REPEATED_ATTEMPTS | MISSING_EVIDENCE |
        SOURCE_CONFLICT | PROTECTED_PATH
AssistanceMode: HINTS | CONCEPTS | ATTEMPT_REVIEW
DecisionAction: SEND_GUIDANCE | ASK_QUESTION | TAKE_OVER | REJECT_SUGGESTION
MessageAuthor: LEARNER | AI | MENTOR | SYSTEM
RunStatus: RUNNING | SUCCEEDED | FAILED
```

Integration failures are represented as failed runs and retryable errors, not clinical-style risk scores or invented confidence percentages. A learner can request a mentor after a failure.

### Endpoints

| Method / path | Body / result | Access |
| --- | --- | --- |
| `POST /auth/login` | `{email,password}` → token + user | Public |
| `GET /auth/me` | Current user | Signed in |
| `GET /tasks` | `{items: Task[]}` | Assigned learner or mentor |
| `GET /tasks/{id}` | `Task` | Authorized workspace |
| `POST /sessions` | `{task_id}` → `SessionDetail` | Assigned learner |
| `GET /sessions/{id}` | `SessionDetail` | Owner or assigned mentor |
| `POST /sessions/{id}/messages` | `{content}` → `SessionDetail` | Owner or assigned mentor, as described below |
| `POST /sessions/{id}/attempts` | `{milestone_id,explanation,code,file_paths,test_output}` → `SessionDetail` | Owner |
| `POST /sessions/{id}/escalations` | `{reason:"MANUAL",question}` → `SessionDetail` | Owner |
| `GET /mentor/escalations?status=OPEN` | `{items: EscalationSummary[]}` | Assigned mentor |
| `GET /escalations/{id}` | `EscalationDetail` | Session owner or assigned mentor |
| `POST /escalations/{id}/decision` | `{action,expected_revision,text}` → `SessionDetail` | Assigned mentor |
| `POST /sessions/{id}/completion-request` | `{expected_version}` → `SessionDetail` | Owner, active only |
| `GET /mentor/completion-reviews` | `{items: SessionSummary[]}` | Assigned mentor |
| `POST /sessions/{id}/completion-decision` | `{expected_version,approved,text}` → `SessionDetail` | Assigned mentor |
| `GET /sources/{id}` | Verified source excerpt and metadata | Authorized workspace |

Absolute health routes: `GET /healthz` checks process health; `GET /readyz` checks database reachability and schema readiness. These do not expose credentials or schema details.

**Message behavior:** In `ACTIVE`, a learner message can trigger AI. In waiting/takeover states, save learner clarifications without calling AI. Mentor messages are saved as human messages and do not automatically resolve the case. Resolution goes through the decision endpoint. Completed sessions are read-only. Use a mentor decision to reopen learning after a rejected completion request.

### Response shapes

```typescript
type User = { id: string; name: string; role: "LEARNER" | "MENTOR" };
type Task = {
  id: string; title: string; description: string;
  repository: { owner: string; name: string; commit_sha: string };
  assistance_mode: "HINTS" | "CONCEPTS" | "ATTEMPT_REVIEW";
  protected_paths: string[]; attempt_threshold: number;
  milestones: { id: string; title: string; criteria: string[] }[];
};
type Citation = {
  source_id: string; path: string; commit_sha: string;
  start_line: number; end_line: number; excerpt: string; url: string;
};
type Message = {
  id: string; author: "LEARNER" | "AI" | "MENTOR" | "SYSTEM";
  content: string; citations: Citation[]; created_at: string;
};
type Attempt = {
  id: string; milestone_id: string; explanation: string; code: string;
  file_paths: string[]; test_output: string | null;
  assessment: "UNRESOLVED" | "PROGRESS" | "NEEDS_REVIEW";
  assessment_note: string; created_at: string;
};
type Activity = {
  id: string; tool: string; status: "SUCCEEDED" | "FAILED";
  summary: string; created_at: string;
};
type EscalationSummary = {
  id: string; session_id: string; task_title: string; learner_name: string;
  reason: string; status: "OPEN" | "RESOLVED";
  revision: number; created_at: string;
};
type EscalationDetail = EscalationSummary & {
  learner_question: string; milestone_id: string;
  summary: string; unresolved_question: string;
  evidence: Citation[]; attempts: Attempt[]; prior_hints: Message[];
  proposed_guidance: string; mentor_messages: Message[];
};
type SessionSummary = {
  id: string; task_title: string; learner_name: string;
  state: string; version: number; updated_at: string;
};
type SessionDetail = {
  id: string; task_id: string; task: Task; state: string;
  current_milestone_id: string; version: number;
  messages: Message[]; attempts: Attempt[]; activity: Activity[];
  open_escalation: EscalationDetail | null;
  latest_run: { id: string; status: "RUNNING" | "SUCCEEDED" | "FAILED" } | null;
  updated_at: string;
};
```

Use actual enum unions in implementation rather than loose strings where possible. The mentor case GET must refresh `attempts` and messages from saved records so later learner clarifications are visible. Increment the case revision when new information changes the review context.

Login returns `{access_token,token_type:"bearer",expires_at,user}`. A session-create request returns an existing open task session for the learner if one already exists; enforce uniqueness rather than creating duplicates on refresh.

Decision example:

```json
{
  "action": "SEND_GUIDANCE",
  "expected_revision": 2,
  "text": "Use the request-schema pattern in the current route. The README refers to the old implementation. Explain where you would put the quantity constraint before writing the endpoint."
}
```

Errors from application code use:

```json
{
  "error": {
    "code": "STALE_REVISION",
    "message": "This case changed. Refresh before sending guidance.",
    "retryable": false,
    "request_id": "request-uuid"
  }
}
```

Normalize FastAPI validation errors into this envelope too. Use 401 for missing/expired credentials, 403 for a role violation, 404 for inaccessible IDs, 409 for stale revisions or incompatible workflow states, 422 for invalid input, and 503 for recoverable upstream failures. State conflicts include codes such as `WAITING_FOR_MENTOR` and `RUN_IN_PROGRESS`.

Requests that generate AI can wait synchronously for up to about 45 seconds. The client shows progress and uses a longer timeout, such as 60 seconds. The learner input/attempt must already be saved if generation fails. Retrying the same operation uses the same idempotency key and must not duplicate the input. A fresh successful user operation gets a fresh key.


## MVP decisions
One milestone initially; PROGRESS saves an assessment but does not complete the task. Learner case responses redact proposed_guidance. Upstream-failed operations can retry the same saved input/key; successful retries replay their original response. A different body with the same key returns 409.
