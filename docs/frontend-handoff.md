# Frontend handoff

Shared branch: `codex/bootstrap` until its PR merges into `main`. Shared commit SHA will be recorded immediately after commit (and sent in chat). Do not assume an unmerged scaffold is on main.

You own `frontend/**`, `docs/frontend-notes.md`, and `docs/demo-script.md`. Backend changes will preserve those paths after this initial starter.

Use Node 24 LTS and npm: `cd frontend`, `npm ci`, `npm run dev`; check with `npm run typecheck` and `npm run build`.

Start `feat/frontend-shell` from the shared commit/branch. Make small PRs and integrate every 60–90 minutes.

API prefix: `/api/v1`. Bearer access token from login; sessionStorage is acceptable for this demo, clear on logout. Send a fresh UUID `Idempotency-Key` for each mutation except login; reuse the same key/body to retry. Enums are uppercase, fields snake_case, IDs UUID strings, timestamps UTC. See `contracts/api-contract.md` and `contracts/examples/`. Always render evidence and model output as text.

At scaffold time: only `/healthz` and `/readyz` are implemented. Readiness returns 503 until migrations/database are ready. All application endpoints are planned and will be added on the backend branch; real OpenAPI is exported as implemented.

Vite proxies `/api` to `http://localhost:8000`; production uses same-origin `/api/v1` and compiled assets served by FastAPI. Backend requests may take 45 seconds; use a 60-second client timeout.

One milestone for the initial task. Only mentor completion decisions finish a task. Pending case proposals are redacted to an empty string for learners; never display internal draft guidance from mentor fixtures to learners.
