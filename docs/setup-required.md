# Setup and verification status

## Verified

- Python 3.12.12 provisioned locally; Node 24/npm starter checks passed.
- Actual PostgreSQL migrations, idempotent seed and 40 tests passed. Local test database is disposable rampup_test on loopback port 55432.
- Neon direct migrations and pooled runtime connections verified from this workstation. Demo seed, live source indexing and real HTTP mentor workflow passed. A pending protected-path case survived actual backend process restart.
- GitHub read-only REST indexing, pinned citations and failed-refresh snapshot preservation verified. Git push/PR authentication works. Immutable GHCR images built/published by CI; anonymous manifest access verified for published backend images.
- User selected gemini-3.1-flash-lite after gemini-3.5-flash repeatedly returned 503 high demand. Live cited progressive hint succeeded with the new model; broad model quality is not guaranteed by one sample.

## Configured privately

Root .env contains DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY and LLM_MODEL. Never commit those values or put them in Vite variables. LLM_PROVIDER=auto infers Gemini for gemini- identifiers, otherwise OpenAI. Both Neon URLs retain TLS/channel-binding options. Demo login values remain in ignored .env and seeded hashes remain in PostgreSQL.

## Deployment action remaining

The existing Alternate Futures account is signed in. A RampUp project and undeployed rampup service draft are prepared with 0.5 CPU, 1 GiB memory, 2 GiB disk, confidential compute, a $2 total budget cap, port 8000 and /healthz probe. No compute deployment has been started. The platform warns that environment values go to its selected provider; approve the specific runtime-secret transmission and capped deployment before starting it.

Prepared runtime names: DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, APP_ENV, PORT, ACCESS_TOKEN_TTL_MINUTES, GITHUB_OWNER, GITHUB_REPO, GITHUB_REF, REPOSITORY_PROVIDER. Demo passwords and GitHub tokens are excluded from the filtered deployment env. The temporary file is ignored under .local; remove it after upload.

After final image publication and deployment: verify public /healthz and /readyz, both demo logins, actual model/GitHub connectivity from the container, and pending-case persistence across redeploy. Workstation/Neon checks do not establish deployed-container behavior. Record the final HTTPS URL, image tag/digest and commit in progress notes. Docker is absent locally; GitHub CI verifies image builds.
