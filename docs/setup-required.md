# External setup

- Install/start Docker Desktop for Compose and local image verification. Python 3.12 is the target runtime; uv can provision a local managed interpreter.
- Set ignored `.env` from `.env.example`, including random JWT_SECRET (32+ characters), local database password, and both demo account passwords.
- Neon: create/use a project; store pooled DATABASE_URL and direct DATABASE_DIRECT_URL securely, preserving sslmode/channel-binding options. Migrations use the direct URL. No Neon connection has been verified.
- Model: set LLM_API_KEY and LLM_MODEL to an identifier available to your account. No model call has been verified.
- GitHub: existing git credentials can read the repository; push/API permissions still need verification. GITHUB_TOKEN is optional for public read-only source indexing and must remain server-side.
- Alternate Futures: sign in to the existing account/project, choose container image deployment, port 8000, set runtime secrets, deploy the immutable GHCR tag. No cloud deployment has been attempted. Package visibility changes require your account action/approval; verify anonymous pull if using a public image.

## Verified update (17 October 2026)

Neon runtime and direct URLs are now configured privately and verified from this workstation; schema, seed and source indexing succeeded. Real HTTP manual mentor loop on Neon passed. GitHub REST and public GHCR manifest access are verified. Model key accepted by Gemini model discovery; selected model gemini-3.5-flash is listed, but generation verification is still in progress after a transient provider failure. LLM_PROVIDER=auto infers Gemini from gemini- model IDs and otherwise OpenAI; no secret values belong in Vite.

Remaining: successful live coaching checks, final hardening PR/CI/release, and Alternate Futures deployment in the existing account/project. No cloud access token/project ID or logged-in deployment context has been supplied. Deployment consumes account credits; choose a concrete service/resource/spend cap before authorizing deployment. Verify database/model/GitHub from the deployed container and pending-case survival across redeploy; workstation checks do not establish those results.
