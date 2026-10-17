# Automation and Integrations

## Orchestration

RampUp does not use n8n or a separate workflow engine. The application owns a small, explicit orchestration flow in FastAPI and Python: routes authenticate and authorize each request, `coach.py` coordinates a bounded coaching turn, and `workflow.py` performs the transactional session and mentor-state changes. PostgreSQL persists inputs and runs before network calls; the app releases database locks while calling external services, then rechecks the session version and state before saving a result. Alembic manages schema changes.

This is application-specific orchestration, not a general-purpose automation builder. A learner request can trigger retrieval, a model response, validation, and possibly a mentor handoff. A mentor decision is an authenticated API action that is checked against the current case revision. Idempotency keys, run expiry, row locks, and database uniqueness constraints protect retries and concurrent decisions.

## Learning-session lifecycle

There is no fixed session duration or question quota. A learner session remains `ACTIVE` until the learner requests completion. That request moves it to `COMPLETION_REVIEW`; only the assigned mentor can approve it and move it to `COMPLETED`. A mentor can instead reject completion and return it to `ACTIVE`. Completed sessions are read-only. The session can also pause in `WAITING_FOR_MENTOR` or `MENTOR_ACTIVE` while an escalation is being resolved.

The seeded task sets `attempt_threshold` to **3**. It counts explicit submissions assessed as `UNRESOLVED` on the current milestone, looking back to the latest assessed `PROGRESS`; chat messages do not count. `PROGRESS` resets the count and advances to the next milestone when one exists. These are AI assessments, not verified test results: learner code and test output are never executed.

Other handoff paths are independent of that threshold:

- The learner can request a mentor at any time.
- An explicit submitted or AI-proposed path matching a protected-path rule triggers mentor review.
- When evidence is missing or fails support/policy checks, the coach asks for one clarification; a second unsupported turn escalates.
- The demo task explicitly configures a conflict between its README and schema guidance. This is a configured demo scenario, not a claim that general source conflicts are found by a universal conflict detector.

The time limits apply to a single AI turn, not the learning session: generation has a 32-second deadline, semantic review has a 10-second deadline, and persisted in-flight runs expire after 50 seconds. The model may make at most four app-provided read-tool calls per turn.

## Services

| Service | Use |
| --- | --- |
| PostgreSQL | Users, tasks, sessions, messages, attempts, mentor cases/decisions, run and idempotency records, and pinned source chunks. Built-in full-text search retrieves source chunks. |
| GitHub REST API | `scripts.index_sources` resolves a commit and reads configured allowlisted files. It stores bounded excerpts in PostgreSQL. Coaching turns search this pinned snapshot; they do not let the model browse GitHub directly. |
| OpenAI Responses API | Optional model provider for structured coaching and a separate support/policy review. |
| Google Gemini GenerateContent API | Alternative model provider, selected by `LLM_PROVIDER` or inferred from the model identifier. Only one provider is used for a given runtime configuration. |
| GitHub Actions and GHCR | CI runs checks and publishes immutable Docker images. This is build/release automation, not session orchestration. |
| Docker / deployment platform | Docker packages the app and PostgreSQL for local use. A hosted deployment is environment-specific; a successful local run does not imply that a public deployment is available. |

## Model tools and service boundary

The app defines three narrow, read-only function tools in `model_adapter.py` and exposes their implementations through `SnapshotTools` in `coach.py`:

- `search_project_context(query)` searches only the task's pinned, indexed repository excerpts.
- `read_project_file(path, start_line, end_line)` reads a bounded excerpt only from allowlisted, indexed paths and lines.
- `get_learning_history()` returns a bounded slice of this session's messages and attempts.

The model can request one of these functions, but it cannot execute it or call a service on its own. The backend validates each call, executes the app-owned function, bounds its response, and sends the result back to the model. Session and project identity come from authenticated server state, not model-supplied arguments. The GitHub token and model API key stay server-side. There is no shell, arbitrary URL fetch, SQL, repository write, code execution, or general external-service tool.

The model returns schema-constrained JSON. The backend validates the result, checks citation source IDs, ranges, and exact quoted text, and separately asks the selected model to review factual support and policy compatibility. That semantic review is fallible; state transitions, protected paths, thresholds, authorization, and final mentor approval remain server-controlled.

## Code map

- [`backend/app/routes.py`](../backend/app/routes.py): authentication, role checks, API endpoints, completion and mentor decisions.
- [`backend/app/coach.py`](../backend/app/coach.py): input persistence, context retrieval, model/tool loop, evidence checks, and escalation.
- [`backend/app/workflow.py`](../backend/app/workflow.py): session state, access rules, escalation records, idempotency, and transaction helpers.
- [`backend/app/model_adapter.py`](../backend/app/model_adapter.py) and [`backend/app/gemini_adapter.py`](../backend/app/gemini_adapter.py): provider adapters, tool declarations, structured output, and bounded requests.
- [`backend/app/repository.py`](../backend/app/repository.py) and [`backend/scripts/index_sources.py`](../backend/scripts/index_sources.py): allowlisted GitHub reads and commit-pinned indexing.
- [`backend/scripts/seed_demo.py`](../backend/scripts/seed_demo.py): the two demo actors, task, milestone, protected path, and demo escalation policy.

The current React frontend is still a starter screen; interactive learner and mentor workflows are available through the API, not yet through a complete site UI. For manual API testing, use FastAPI's `/docs` page while the backend is running.