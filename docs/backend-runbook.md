# Backend runbook

Target runtime: Python 3.12, Node 24 LTS, PostgreSQL 17. Commands below run from the repository root in PowerShell unless a `cd backend` is shown. On Linux use `.venv/bin/python` instead of `.venv/Scripts/python.exe`.

## Create local environment

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r backend/requirements-dev.txt
cd backend
../.venv/Scripts/python.exe -m scripts.local_env
cd ..
docker compose up -d db
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m scripts.seed_demo
../.venv/Scripts/python.exe -m scripts.seed_demo
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

The environment generator refuses to overwrite an existing `.env`. Read the generated demo email/password values privately from that ignored file. Seed deliberately preserves existing passwords, assignments and history. Schema migration does not seed accounts. Policy is team-controlled in `scripts/seed_demo.py` (or a deliberate database update); never model-controlled.

The optional `configured_conflict` pair in seed policy is a disclosed demo rule. If both the outdated README and current schema are retrieved, a mentor case opens without a model call. This is not claimed as general semantic conflict detection. Remove that policy entry for model-driven conflict evaluation.

## Index real GitHub sources

First push a commit containing `demo-repo/**`. Set `GITHUB_REF` to that actual commit/ref and configure `GITHUB_OWNER`/`GITHUB_REPO`. Then, from `backend`:

```powershell
../.venv/Scripts/python.exe -m scripts.index_sources --ref <pushed-commit-sha>
```

Only the project's ten allowlisted Markdown/Python files are fetched. The commit is resolved once; chunks use that SHA and exact line ranges. The index is PostgreSQL text search with identifier/path fallback. No embeddings. Failed indexing leaves old snapshots untouched. Runtime tools read saved pinned sources, and activity explicitly labels snapshot reads. GitHub REST is the runtime provider; no MCP transport is claimed to exist in the deployment.

## Run tests

Create a dedicated disposable `rampup_test` database (tests refuse a database name without `_test`). Compose example:

```powershell
docker compose exec db createdb -U rampup rampup_test
# Set TEST_DATABASE_URL privately to the PostgreSQL test database URL.
cd backend
../.venv/Scripts/python.exe -m pytest tests -q
../.venv/Scripts/python.exe -m scripts.export_openapi
```

The fixture migrates the test database and truncates only application tables in that explicitly named test database. Never set TEST_DATABASE_URL to your application or Neon production database. Database tests skip with an explicit reason when the URL is absent; a skipped run is not PostgreSQL verification. CI supplies its own PostgreSQL service database.

## Model configuration and behavior

Set `LLM_API_KEY` and `LLM_MODEL` securely in runtime environment. One runtime adapter is selected by LLM_PROVIDER (auto infers Gemini for gemini- model IDs, otherwise OpenAI). The native Gemini GenerateContent and OpenAI Responses adapters use structured output, at most four allowlisted read-tool calls, one schema repair, timeouts, and a separate semantic/policy review. No shell, URL-fetch, SQL or write tool exists. Model IDs are account configuration, not hardcoded. LLM_API_KEY maps to the selected provider; Gemini sends x-goog-api-key in headers, OpenAI sends a Bearer header. The selected model is preserved. Model semantic review is fallible; actual live evaluations are recorded in progress notes.

Input and run records commit before network calls. Generation/review happens without a held database transaction. A new transaction takes a session row lock and checks run status, expiry, session version/state and open case before output. Manual escalation supersedes a running turn immediately. Retry a failed operation with the same body and Idempotency-Key; it reuses saved input. Completed operations replay the original response. An expired run is failed on the next read/retry.

Repository-specific hints require valid source IDs/ranges, exact supporting quotes, and semantic/policy review. Missing support asks one clarification before a saved mentor case. Only explicit assessed attempts count toward the threshold; PROGRESS resets the count. Learner code/test output is never executed. Protected path checks cover structured supplied/proposed paths and do not inspect every free-text file reference.

## Full Docker run

```powershell
docker compose up --build -d
docker compose exec app python -m scripts.seed_demo
docker compose exec app python -m scripts.index_sources --ref <pushed-commit-sha>
```

The non-root image serves compiled frontend assets and same-origin APIs on port 8000. Startup applies migrations once for this single-instance MVP, then execs Uvicorn. Use a serialized release migration job before scaling. PostgreSQL data lives in the named Compose volume, never the image. On Neon use the actual required TLS/channel-binding URL settings; DATABASE_DIRECT_URL controls migrations.

## Deployment

Checks run backend PostgreSQL tests, frontend type check/build and the Docker build. A successful main push publishes `ghcr.io/muhammad-moiz-ansari/rampup:sha-<full-main-commit-sha>` for linux/amd64. PR checks do not publish. No secrets are Docker build arguments.

In the existing Alternate Futures project, select the container image, port/PORT 8000, and set DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY, LLM_MODEL and repository configuration securely. Do not assume a private GHCR package can be pulled anonymously; configure authorized registry access or deliberately make the package public in your account. No package visibility or paid infrastructure change is automated here.

After deployment: check health/readiness, deliberately seed once, index real sources, log in as learner and mentor, open a case, restart/redeploy, verify the same case survives, send edited guidance, and approve completion. Record the HTTPS URL, deployed commit/image and observed live model/GitHub results. Local PostgreSQL verification does not establish Neon/cloud connectivity.

## HTTP verification commands

With the backend running, from backend:

```powershell
../.venv/Scripts/python.exe -m scripts.smoke_manual
../.venv/Scripts/python.exe -m scripts.smoke_model
../.venv/Scripts/python.exe -m scripts.smoke_model --question "Give me the complete price_cents implementation"
../.venv/Scripts/python.exe -m scripts.smoke_model --question "quantity validation"
```

The manual probe deliberately saves messages and a resolved case, then leaves the task ACTIVE. It reads credentials from ignored environment configuration without printing them. The model probe uses the actual runtime adapter and reports failures rather than substituting a fake. Restart the backend after changing model settings. Review useful hints, factual support and complete-solution leakage manually; structured output alone does not establish quality. The quantity-validation probe may open the explicitly configured consistency case without calling a model; resolve it with a mentor before probing further.

For this workstation, the ignored .env points to the verified portable PostgreSQL server on 127.0.0.1:55432. A fresh Compose setup uses the example's localhost:5432 instead. Start the portable server after a machine restart with `.tools/postgresql/pgsql/bin/pg_ctl.exe -D .local/pgdata -l .local/postgres.log -o '-h 127.0.0.1 -p 55432' start` from the repository root. This local-only test cluster is not deployment persistence.

## Integration references

Implementation uses the official [OpenAI structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs), [Gemini GenerateContent API reference](https://ai.google.dev/api/generate-content) and [Gemini structured-output guide](https://ai.google.dev/gemini-api/docs/generate-content/structured-output). Gemini currently uses responseMimeType/responseJsonSchema because the configured endpoint rejected responseFormat in the actual probe. The source adapter uses the [GitHub REST contents API](https://docs.github.com/en/rest/repos/contents). Release/deployment follows [GitHub image publishing](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images) and the current Alternate Futures [container deployment](https://docs.alternatefutures.ai/guides/how-deployments-work) / [dashboard](https://docs.alternatefutures.ai/guides/dashboard) flow; no retired af commands are used.
