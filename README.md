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
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

In another terminal: `cd frontend`, `npm ci`, `npm run dev`. Backend health: http://localhost:8000/healthz; actual OpenAPI: http://localhost:8000/openapi.json. Readiness is 503 until a reachable database has the migration applied.

Tests: from `backend`, run `../.venv/Scripts/python.exe -m pytest tests -q`. Full image: from root, `docker compose up --build`.

See [API contract](contracts/api-contract.md), [frontend handoff](docs/frontend-handoff.md), [progress](docs/backend-progress.md), and [external setup](docs/setup-required.md). Migration, seed, indexing and deployment steps will be documented with their implementation.
