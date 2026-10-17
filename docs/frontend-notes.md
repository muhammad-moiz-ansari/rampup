# Frontend progress

## 2026-10-17

Implemented the learner and mentor workspaces on `codex/frontend-workspaces`, starting from `origin/main` at `139e03a7ef9c2dff8a61e23ec5e1bf5f243ab7d2`. The supplied API documentation matches `contracts/openapi.json`. No backend contract, authorization or approval rules were changed.

The owner requested a terminal-inspired redesign: charcoal surfaces, off-white monospace text, neon green actions, Pixelify Sans headings, IBM Plex Mono body, `RampUp` branding and a prompt/cursor mark. Fonts are bundled locally through Fontsource. Conversation entries use a chronological prompt/reply layout, with a distinct amber mentor speaker label. Decorative slogans and miniature headings were removed. Narrow screens use a navigation dialog and task-detail drawer. Keyboard focus, reduced motion, labelled controls and native modal focus restoration are preserved.

### Working features

- Authentication, restoration, expiry and reconnect handling; role-specific navigation.
- Task list/details and policy display; tasks are read-only because the public API has no task-creation endpoint.
- Learner questions, attempts, source excerpts, citations, activity, manual mentor requests and paused clarifications.
- Mentor queue, case context, conversation, attempts, source evidence, edited guidance, questions, takeover and rejection.
- Completion requests, mentor return for changes, explicit completion confirmation and completed read-only history.
- Drafts scoped to the user and session in sessionStorage. Unsubmitted drafts remain in the current tab.
- Mutations retain the original body and idempotency key after an ambiguous response. Receipt recovery remains available after the underlying session changes. Fresh decisions require current revisions; stale context requires acknowledgement. Polling preserves drafts and cannot replace a newer session version with an older receipt.

### Verified

- TypeScript, seven API-client tests and a production build passed during implementation; rerun final commands below after edits.
- Real hosted API browser walkthrough: separate learner/mentor login; manual handoff; learner clarification; stale-context acknowledgement; mentor question; takeover; edited guidance; learner resume. A missed question receipt was recovered with its original operation key, and the question appeared once.
- A real pinned GitHub excerpt opened from a citation. Escape closed the drawer and restored focus to the citation button.
- Isolated local PostgreSQL database `rampup_ui_test`: fresh session, protected-path attempt, coaching pause, mentor queue, edited guidance, learner resume, completion request, return for changes, another request, stale-context acknowledgement, explicit final approval and completed state after reload. Model credentials were deliberately disabled in this test backend. This is workflow verification, not AI-quality verification.
- Visual inspection of the actual application in a 1280x900 desktop iframe and 390x844 mobile iframe. Temporary QA pages are removed before committing. Screenshots are in ignored `.local/frontend-retro-desktop.png` and `.local/frontend-retro-mobile.png`.
- Root `.env` remains ignored. No secret values are bundled or committed. The Gemini adapter and `gemini-3.1-flash-lite` configuration are unchanged. Existing limited model checks do not establish that an upgrade is necessary.

### Run and check

Use Node 24. In `frontend`, run `npm ci`, then `npm run dev`. The default proxy targets `http://localhost:8000`. To use another backend, set the server-only `RAMPUP_API_PROXY` in `frontend/.env.local`, following `.env.example`. Production assets use same-origin `/api/v1` and are served by FastAPI. Never put server credentials in `VITE_*` variables.

Checks: `npm run typecheck`, `npm run format:check`, `npm test`, `npm run build`. CI also runs backend PostgreSQL tests and builds the combined Docker image. Run `npm run format` before committing changed frontend sources.

The public deployment still needs the newly built image to show this frontend. A local successful build does not verify a cloud rollout. Do not change cloud secrets, compute/security settings or spending limits as part of the UI redesign.

### Release checkpoint

UI commit `6d32ea2098fb8e5e8f9b67b5205bec8053bed45b` was pushed in PR #7 and merged normally as `e29d2f7cba05361bc1d4c08511f5a1a4d7d290f0`. PR and main CI passed PostgreSQL tests, Ruff, frontend type/format/client/build checks and Docker build. Release-image CI also passed. Anonymous GHCR manifest access returned 200 for `ghcr.io/muhammad-moiz-ansari/rampup:sha-e29d2f7cba05361bc1d4c08511f5a1a4d7d290f0`, digest `sha256:9c756cf148ec6b7b24ec62d7323bcb84b1f72abb9e77058940e678e48b8ac61a`.

The same RampUp/rampup service was updated to that image. The portal's redeploy flow temporarily returned stale Not running states and allocated an incorrect Confidential instance with larger resources; that instance was terminated. A remaining queued replacement now shows Standard Europe, 0.50 CPU / 1.07 GB RAM / 2.15 GB disk, Creating lease. Requested total cap is reduced to $1.65, reserving past spend inside the existing $2 overall authorization. Runtime secrets and Gemini model were not edited. Public rollout is still pending at this checkpoint. Do not infer success from the portal's badge, submit another deployment while this one is pending, or leave any extra Confidential instance running.

Latest owner instruction supersedes those requested resources: **$2 total service cap exactly, 1 CPU, 2 GiB RAM, 4 GiB storage**, Standard compute. At resumption, the pending Europe lease already displayed these resource sizes. Deployment history now exposes the blocker: repeated `lease-create: tx rejected on-chain (code 32)`, `Akash tx rejected (code 32)` and a permanently failed attempt with `bid not open`. Cosmos SDK registers code 32 as incorrect account sequence. These errors occur before the app starts. Cancellation of the stuck pending lease is in progress; wait for CLOSED confirmation before a single fresh Standard submission with the owner's exact cap/resources. A different Standard region is the next attempt to obtain a fresh provider bid. Do not keep submitting overlapping leases. Evidence is saved in ignored `.local/deployment-lease-errors.png`. Runtime secrets, database data and Gemini configuration remain unchanged. Public endpoints still return the platform's no-active-deployment 503 at this checkpoint.

Clean attempt submitted after the previous request reached FAILED with `Akash tx rejected (code 32)`: Standard **US East**, explicit **$2 Total budget cap**, **1 CPU / 2 GiB RAM / 4 GiB disk**, same e29d2f7 image, no secret or port edits. The form was verified before submission and saved to ignored `.local/deployment-requested-settings.png`. The service shows Deploying with the correct resource sizes; wait for this attempt and inspect deployment history for the actual on-chain result. Do not treat the dashboard's provisional state as public readiness.
