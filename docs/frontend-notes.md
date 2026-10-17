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
