# RampUp

Repository learning with cited hints and a persistent mentor approval loop.

Python 3.12 / FastAPI / PostgreSQL 17 backend; React / TypeScript / Vite / Tailwind 4 frontend; Node 24 LTS. Frontend ownership transfers to the teammate after bootstrap.

## Local starter

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
# Edit .env with random local secrets and passwords first.
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r backend/requirements-dev.txt
docker compose up -d db
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m scripts.seed_demo
../.venv/Scripts/python.exe -m scripts.index_sources --ref 390be5aa21afa27b1336dfda8c5206b8bb5c0dc4
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

In another terminal: `cd frontend`, `npm ci`, `npm run dev`. Backend health: http://localhost:8000/healthz; actual OpenAPI: http://localhost:8000/openapi.json. Readiness is 503 until a reachable database has the migration applied.

Tests require a disposable PostgreSQL database whose name ends in `_test`; set `TEST_DATABASE_URL` to that database, then from `backend` run `../.venv/Scripts/python.exe -m pytest tests -q`. Never use the application database for tests. Full image: from root, `docker compose up --build`.

Before starting the backend, run migrations and deliberately seed from `backend`: `../.venv/Scripts/python.exe -m alembic upgrade head`, then `../.venv/Scripts/python.exe -m scripts.seed_demo`. Index evidence from a pushed commit containing `demo-repo/` using `../.venv/Scripts/python.exe -m scripts.index_sources --ref <pushed-commit-sha>`. Set LLM_API_KEY and LLM_MODEL for live coaching. Manual mentor handoff works without model credentials.

See [backend runbook](docs/backend-runbook.md) for complete local/Docker/migration/seed/index/test/deploy commands, [API contract](contracts/api-contract.md), [frontend handoff](docs/frontend-handoff.md), [progress](docs/backend-progress.md), and [external setup](docs/setup-required.md). Actual implemented schemas are in [OpenAPI](contracts/openapi.json).
