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

The user explicitly approved runtime-secret upload and deployment capped at $2. Alternate Futures now reports the RampUp/rampup confidential service ACTIVE with 0.5 CPU, 1 GiB memory, 2 GiB disk, port 8000 and /healthz probe. Displayed rate: $0.080/hour. The platform warns that environment values go to its selected provider; that disclosure was included in approval.

Uploaded runtime names: DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, APP_ENV, PORT, ACCESS_TOKEN_TTL_MINUTES, GITHUB_OWNER, GITHUB_REPO, GITHUB_REF, REPOSITORY_PROVIDER. Demo passwords and GitHub tokens were excluded. The temporary filtered env file was removed after import; root .env remains ignored.

Public URL: https://alternate-cloudy-serpent-6983-docker-app.alternatefutures.ai

Deployed code/image: `c5a667f7b220c2cede6c6b3ea907dd8d783a3a6c`, `ghcr.io/muhammad-moiz-ansari/rampup:sha-c5a667f7b220c2cede6c6b3ea907dd8d783a3a6c`, digest `sha256:a786e8e2adf81686bcd0b12f3709a434bc110ffdebca5488ac693280516348ca`. Main checks and image release succeeded; anonymous manifest access returned HTTP 200.

The first public requests return platform HTTP 503 Provisioning; the container terminal cannot connect yet. After routing finishes, verify public /healthz and /readyz, both demo logins, actual model/GitHub connectivity from the container, and pending-case persistence across redeploy. Workstation/Neon checks do not establish deployed-container behavior. Docker is absent locally; GitHub CI verifies image builds. Record actual outcomes in progress notes.
