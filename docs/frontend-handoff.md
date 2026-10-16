# Frontend handoff

Shared branch: `codex/bootstrap` until its PR merges into `main`. Shared commit SHA will be recorded immediately after commit (and sent in chat). Do not assume an unmerged scaffold is on main.

You own `frontend/**`, `docs/frontend-notes.md`, and `docs/demo-script.md`. Backend changes will preserve those paths after this initial starter.

Use Node 24 LTS and npm: `cd frontend`, `npm ci`, `npm run dev`; check with `npm run typecheck` and `npm run build`.

Start `feat/frontend-shell` from the shared commit/branch. Make small PRs and integrate every 60–90 minutes.

API prefix: `/api/v1`. Bearer access token from login; sessionStorage is acceptable for this demo, clear on logout. Send a fresh UUID `Idempotency-Key` for each mutation except login; reuse the same key/body to retry. Enums are uppercase, fields snake_case, IDs UUID strings, timestamps UTC. See `contracts/api-contract.md` and `contracts/examples/`. Always render evidence and model output as text.

At scaffold time: only `/healthz` and `/readyz` are implemented. Readiness returns 503 until migrations/database are ready. All application endpoints are planned and will be added on the backend branch; real OpenAPI is exported as implemented.

Vite proxies `/api` to `http://localhost:8000`; production uses same-origin `/api/v1` and compiled assets served by FastAPI. Backend requests may take 45 seconds; use a 60-second client timeout.

One milestone for the initial task. Only mentor completion decisions finish a task. Pending case proposals are redacted to an empty string for learners; never display internal draft guidance from mentor fixtures to learners.

Bootstrap commit: 205853879753a07199575db0ce6a9f5af9fa53b6, pushed to origin/codex/bootstrap. Start with git fetch origin; git switch -c feat/frontend-shell 205853879753a07199575db0ce6a9f5af9fa53b6. main awaits PR integration.

Update: bootstrap PR #1 merged normally after green CI; shared main merge commit is `98e031448632c964dd9cb8e15492ff076d3d1817`. Frontend teammates may start from origin/main now. Existing frontend branches can merge origin/main normally.

Backend integration branch: `feat/backend-foundation`. All contract application routes are implemented there, with generated `contracts/openapi.json`. Authentication, manual handoff, decisions, completion, retry and authorization are tested against PostgreSQL. AI requires server-side LLM_API_KEY/LLM_MODEL and indexed sources; model failure returns 503 with saved input, so offer retry using the same key and a manual mentor button. Waiting/takeover/completion-review learner messages save without AI. Explicit attempts require ACTIVE.

After sending a clarification, refresh the pending case revision. A 409 STALE_REVISION or STALE_VERSION requires refreshing before another decision. Successful idempotent retries return the original response, which can be older than the current session; refresh GET /sessions/{id} for the latest state.

Case detail keeps the public contract shape; learner proposed_guidance is always empty. Mentor GET /sessions/{id} exposes current learner clarifications in messages. Case GET refreshes saved attempts and delivered hints/mentor messages; use the session message history to display the full discussion.
