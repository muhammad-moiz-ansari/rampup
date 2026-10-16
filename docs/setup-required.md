# Setup and verification status

## Verified

- Python 3.12.12 provisioned locally; Node 24/npm starter checks passed.
- Actual PostgreSQL migrations, idempotent seed and 40 tests passed. Local test database is disposable rampup_test on loopback port 55432.
- Neon direct migrations and pooled runtime connections verified from this workstation. Demo seed, live source indexing and real HTTP mentor workflow passed. A pending protected-path case survived actual backend process restart.
- GitHub read-only REST indexing, pinned citations and failed-refresh snapshot preservation verified. Git push/PR authentication works. Immutable GHCR images built/published by CI; anonymous manifest access verified for published backend images.
- User selected gemini-3.1-flash-lite after gemini-3.5-flash repeatedly returned 503 high demand. Live cited progressive hint succeeded with the new model; broad model quality is not guaranteed by one sample.

## Configured privately

Root .env contains DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY and LLM_MODEL. Never commit those values or put them in Vite variables. LLM_PROVIDER=auto infers Gemini for gemini- identifiers, otherwise OpenAI. Both Neon URLs retain TLS/channel-binding options. Demo login values remain in ignored .env and seeded hashes remain in PostgreSQL.

## Working public deployment

Confidential containers started correctly but the public URL repeatedly returned the platform's HTTP 503 Provisioning response, with terminal access also failing. At the user's renewed repair request, the user explicitly approved Standard compute and sending the existing runtime secrets to its selected provider without TEE isolation. The confidential instance was stopped before replacement. The unchanged c5 image is now reachable on Standard compute in Europe. This isolates the observed failure to the confidential deployment/routing path; no application-code change was needed.

Resources: 0.5 CPU, 1 GiB RAM and 2 GiB disk (dashboard displays 0.50 CPU / 1.07 GB / 2.15 GB). Displayed rate is $0.0036/hour, with a $1.70 remaining Total Budget Cap; prior trials left $4.81 from the initial $5 credit. This reserves earlier spend within the overall $2 authorization. Do not treat each redeployment as a fresh $2 allowance. Resource/environment controls reset after shutdown/navigation; explicitly reselect settings before future deployments. Inspect deployment history and stop leftover instances: the dashboard previously retained an earlier active instance after redeploy.

Existing project: https://clouds.alternatefutures.ai/org/oVmaFCcTQoasd3255_q-I/project/cmvbed1l50daoe41rch5fu0uo, service rampup (`cmvbed2760dare41riee1910e`). Source container port and PORT are 8000; Settings Ports maps public 80 → container 8000, HTTP. Health probe uses /healthz on 8000.

Uploaded runtime names: DATABASE_URL, DATABASE_DIRECT_URL, JWT_SECRET, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, APP_ENV, PORT, ACCESS_TOKEN_TTL_MINUTES, GITHUB_OWNER, GITHUB_REPO, GITHUB_REF, REPOSITORY_PROVIDER. Demo passwords and GitHub tokens were excluded. The temporary filtered env file was removed after import; root .env remains ignored.

Public URL: https://alternate-cloudy-serpent-6983-docker-app.alternatefutures.ai

Deployed code/image: `c5a667f7b220c2cede6c6b3ea907dd8d783a3a6c`, `ghcr.io/muhammad-moiz-ansari/rampup:sha-c5a667f7b220c2cede6c6b3ea907dd8d783a3a6c`, digest `sha256:a786e8e2adf81686bcd0b12f3709a434bc110ffdebca5488ac693280516348ca`. Main checks and image release succeeded; anonymous manifest access returned HTTP 200. Later documentation-only commits do not require replacing this code image.

Verified on the public Standard deployment: /healthz and /readyz HTTP 200; frontend HTML and both compiled assets HTTP 200; unknown API route JSON 404; both demo logins; saved manual case; paused learner clarification; exact-once edited mentor delivery and ACTIVE resume. Connected container terminal ran `python -m scripts.index_sources --ref 390be5aa21afa27b1336dfda8c5206b8bb5c0dc4` successfully: 10 real GitHub files / 10 chunks. This verifies deployed PostgreSQL/schema, authentication/workflow and outbound GitHub connectivity. The frontend remains the teammate-owned placeholder.

Pending: fresh cloud model check and pending-case persistence across cloud redeploy. The separate Gemini3.5/Neon/migrations/seed verification command was declined before execution, so no fresh results are claimed for it. Last inspected root .env and cloud LLM_MODEL remain gemini-3.1-flash-lite; native Gemini adapter is already implemented and cloud LLM_PROVIDER is gemini. Do not send the Gemini key to OpenAI. Earlier workstation checks remain historical results, not a fresh cloud model verification. Reusable HTTP probes accept `--base-url`; see runbook. Docker is absent locally; GitHub CI verifies image builds.
