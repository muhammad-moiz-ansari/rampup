# External setup

- Install/start Docker Desktop for Compose and local image verification. Python 3.12 is the target runtime; uv can provision a local managed interpreter.
- Set ignored `.env` from `.env.example`, including random JWT_SECRET (32+ characters), local database password, and both demo account passwords.
- Neon: create/use a project; store pooled DATABASE_URL and direct DATABASE_DIRECT_URL securely, preserving sslmode/channel-binding options. Migrations use the direct URL. No Neon connection has been verified.
- Model: set LLM_API_KEY and LLM_MODEL to an identifier available to your account. No model call has been verified.
- GitHub: existing git credentials can read the repository; push/API permissions still need verification. GITHUB_TOKEN is optional for public read-only source indexing and must remain server-side.
- Alternate Futures: sign in to the existing account/project, choose container image deployment, port 8000, set runtime secrets, deploy the immutable GHCR tag. No cloud deployment has been attempted. Package visibility changes require your account action/approval; verify anonymous pull if using a public image.
