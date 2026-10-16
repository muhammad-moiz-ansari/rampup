# Frontend handoff

Shared backend code is on `main`, through merge commit `c5a667f7b220c2cede6c6b3ea907dd8d783a3a6c`. All application endpoints in `contracts/api-contract.md` are implemented; generated schemas are in `contracts/openapi.json`. Bootstrap commit was `205853879753a07199575db0ce6a9f5af9fa53b6` (PR #1); backend PRs #2–#4 also passed checks and merged normally.

You own `frontend/**`, `docs/frontend-notes.md`, and `docs/demo-script.md`. Backend changes will preserve those paths after this initial starter.

Use Node 24 LTS and npm: `cd frontend`, `npm ci`, `npm run dev`; check with `npm run typecheck` and `npm run build`.

For a new frontend branch, from the existing checkout:

```powershell
git fetch origin
git switch -c feat/frontend-shell origin/main
cd frontend
npm ci
npm run dev
```

If you already have a frontend branch, fetch and merge `origin/main` into it normally, preserving your UI. Make small PRs and integrate every 60–90 minutes.

API prefix: `/api/v1`. Bearer access token from login; sessionStorage is acceptable for this demo, clear on logout. Send a fresh UUID `Idempotency-Key` for each mutation except login; reuse the same key/body to retry. Enums are uppercase, fields snake_case, IDs UUID strings, timestamps UTC. See `contracts/api-contract.md` and `contracts/examples/`. Always render evidence and model output as text.

All application endpoints are implemented now. Readiness returns 503 if database/schema are unavailable. Backend run commands are in `docs/backend-runbook.md`; current deployment verification is in `docs/setup-required.md`. Demo credentials are in the owner's ignored root `.env`; obtain them privately, never commit them or expose them as Vite variables.

Vite proxies `/api` to `http://localhost:8000`; production uses same-origin `/api/v1` and compiled assets served by FastAPI. Backend requests may take 45 seconds; use a 60-second client timeout.

One milestone for the initial task. Only mentor completion decisions finish a task. Pending case proposals are redacted to an empty string for learners; never display internal draft guidance from mentor fixtures to learners.

Prioritize learner login/task/session → manual mentor request → mentor queue/case → edited guidance → learner resume. Then add cited coach/attempt input and completion review. The initial task has one milestone, `validation`.

Authentication, manual handoff, decisions, completion, retry and authorization are tested against PostgreSQL. AI requires server-side LLM_API_KEY/LLM_MODEL and indexed sources; model failure returns 503 with saved input, so offer retry using the same key and a manual mentor button. Waiting/takeover/completion-review learner messages save without AI. Explicit attempts require ACTIVE.

After sending a clarification, refresh the pending case revision. A 409 STALE_REVISION or STALE_VERSION requires refreshing before another decision. Successful idempotent retries return the original response, which can be older than the current session; refresh GET /sessions/{id} for the latest state.

Case detail keeps the public contract shape; learner proposed_guidance is always empty. Mentor GET /sessions/{id} exposes current learner clarifications in messages. Case GET refreshes saved attempts and delivered hints/mentor messages; use the session message history to display the full discussion.

Live integration update: Neon migrations, seed, repository indexing, authentication and the mentor loop are verified. A pending protected-path case survived an actual backend process restart. `gemini-3.1-flash-lite` produced a live progressive hint with valid GitHub citations; one separate probe failed output validation. These small samples are not a broad quality guarantee. The optional README/schema conflict is an explicitly configured demo rule. Full quality/deployment results are tracked in `docs/backend-progress.md`. The initial React page remains the agreed placeholder; frontend paths have been preserved since bootstrap.
