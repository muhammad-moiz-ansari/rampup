# Setup and verification status

## Verified

- Python 3.12.12 provisioned locally; Node 24/npm starter checks passed.
- Actual PostgreSQL migrations, idempotent seed and 40 tests passed. Local test database is disposable rampup_test on loopback port 55432.
- Neon direct migrations and pooled runtime connections verified from this workstation. Demo seed, live source indexing and real HTTP mentor workflow passed. A pending protected-path case survived actual backend process restart.
- GitHub read-only REST indexing, pinned citations and failed-refresh snapshot preservation verified. Git push/PR authentication works. Immutable GHCR images built/published by CI; anonymous manifest access verified for published backend images.
- User selected gemini-3.1-flash-lite after gemini-3.5-flash repeatedly returned 503 high demand. Live cited progressive hint succeeded with the new model; broad model quality is not guaranteed by one sample.

## Configured privately

Root .env contains DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY and LLM_MODEL. Never commit those values or put them in Vite variables. LLM_PROVIDER=auto infers Gemini for gemini- identifiers, otherwise OpenAI. Both Neon URLs retain TLS/channel-binding options. Demo login values remain in ignored .env and seeded hashes remain in PostgreSQL.

## Deployment verification in progress

The user explicitly approved runtime-secret upload and confidential deployment capped at $2. Three confidential attempts started containers successfully but public routing remained unavailable. All instances have now been stopped to avoid charging for an unusable endpoint; service configuration/history and Neon data remain. Requested resources were 0.5 CPU, 1 GiB memory and 2 GiB disk; the provider allocated at least 1 CPU / 2 GB / 20 GB at $0.080/hour. Port 8000, an explicit public 80 → container 8000 HTTP mapping and /healthz probe are configured. A redeploy briefly left both old and replacement deployments active; each was explicitly terminated. Inspect deployment history after future redeploys.

Approval for Standard compute on this same service is pending because it removes TEE isolation and changes the selected provider. Do not start that fallback without the user's reply. Use a $1.90 remaining cap (or less) to reserve prior trial spend within the $2 overall authorization. Resource/environment controls reset after shutdown/navigation; explicitly reselect the approved settings immediately before deployment. The platform warns that environment values go to its selected provider; that disclosure was included in the initial confidential approval.

Uploaded runtime names: DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, APP_ENV, PORT, ACCESS_TOKEN_TTL_MINUTES, GITHUB_OWNER, GITHUB_REPO, GITHUB_REF, REPOSITORY_PROVIDER. Demo passwords and GitHub tokens were excluded. The temporary filtered env file was removed after import; root .env remains ignored.

Public URL: https://alternate-cloudy-serpent-6983-docker-app.alternatefutures.ai

Released code/image used in the stopped attempts: `c5a667f7b220c2cede6c6b3ea907dd8d783a3a6c`, `ghcr.io/muhammad-moiz-ansari/rampup:sha-c5a667f7b220c2cede6c6b3ea907dd8d783a3a6c`, digest `sha256:a786e8e2adf81686bcd0b12f3709a434bc110ffdebca5488ac693280516348ca`. Main checks and image release succeeded; anonymous manifest access returned HTTP 200.

Public requests returned platform HTTP 503 Provisioning even after logs showed Application startup complete and Uvicorn listening on 0.0.0.0:8000; terminal connections failed. Public app acceptance remains unverified. Once a deployment is reachable, verify public /healthz and /readyz, both demo logins, actual model/GitHub connectivity from the container, and pending-case persistence across redeploy. Workstation/Neon checks do not establish deployed-container behavior. Docker is absent locally; GitHub CI verifies image builds. Reusable HTTP probes accept `--base-url`; see runbook. Ignored `.local/cloud_probe.py open|verify` is prepared for the public protected-path/redeploy/completion-return check but has not succeeded yet. Record actual outcomes in progress notes.
