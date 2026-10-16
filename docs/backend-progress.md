# Backend progress

2026-10-16: Read the complete implementation brief. Existing main is 3866061 (README only); fetched successfully. No applicable AGENTS.md. Bootstrap branch codex/bootstrap preserves remote history.

Shared scaffold being built. Available: Node 24.19.0, npm 11.17.0, Python 3.14.3, uv, git identity and remote read authentication. Missing on PATH: Docker, gh, psql. Model/database credentials are not currently supplied. Do not treat deployment or PostgreSQL tests as verified until recorded here.

Next: verify and publish scaffold, then PostgreSQL/auth and the manual learner → mentor → learner flow.

Scaffold checks: npm install succeeded (0 audit findings); npm run typecheck and npm run build passed (Vite 6.4.4). Python 3.12.12 provisioned with uv; health/readiness/API-404 test passed (1 test). Docker image not verified locally: Docker unavailable. PostgreSQL portable binaries downloaded for next phase. Model and hosted DB remain unconfigured.

2026-10-16 milestone A1/A2: Python 3.12.12 environment installed; portable PostgreSQL 17.11 runs on loopback 55432 under ignored .local/pgdata. Migrations 0001 + 0002 applied; alembic check reports no missing schema operations. Real hashed demo authentication, assignment-aware task/session/source/case access, idempotency, one-open-case/one-active-run indexes, revision-locked mentor decisions, redaction, and mentor-only completion are implemented. Tests: 19 passed against actual PostgreSQL (one dependency deprecation warning). Covers concurrency, exact-once delivery, retries, restart persistence, protected paths and late-run supersession. Fake model only; no live model test claimed. Ruff unused-import checks pass; Python source formatted.

Shared scaffold: 205853879753a07199575db0ce6a9f5af9fa53b6 pushed; PR #1 merged after successful checks as 98e031448632c964dd9cb8e15492ff076d3d1817. Both main Checks and Release image succeeded on GitHub. Published immutable image ghcr.io/muhammad-moiz-ansari/rampup:sha-98e031448632c964dd9cb8e15492ff076d3d1817. Docker build was verified by CI, not local Docker. Anonymous registry access and Alternate Futures deployment remain pending.

All contract application routes are now implemented on feat/backend-foundation. Real OpenAPI exported. Read-only REST adapter, source indexer, ten fictional demo source files and bounded OpenAI Responses adapter implemented; next verify live GitHub reads from the first pushed commit containing demo-repo, then run adapter/adversarial tests and backend PR CI. No frontend changes after the scaffold handoff.
