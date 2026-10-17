# RampUp — Test Credentials & Access Guide

> **PRIVATE** — Git-ignored. Do not commit this file.

---

## 🌐 Application URLs

| Environment | URL |
|---|---|
| **Local dev** | http://localhost:8000 (backend) / http://localhost:5173 (Vite frontend) |
| **Local combined** | http://localhost:8002 (if running on port 8002) |
| **Cloud deployment** | https://alternate-cloudy-serpent-6983-docker-app.alternatefutures.ai |

---

## 👤 Demo Accounts (Pre-seeded)

### Demo Learner
| Field | Value |
|---|---|
| Email | `learner@example.test` |
| Password | `AXpQlPQ8N2J-Cw-XC4fP1rFm` |
| Role | LEARNER |
| Assigned Task | "Add inventory quantity updates" |

### Demo Mentor
| Field | Value |
|---|---|
| Email | `mentor@example.test` |
| Password | `sAAwqZFhh9pGUmiXya6afiRc` |
| Role | MENTOR |
| Assigned Task | Same task (reviews learner's work) |

---

## 🧪 QA Test Accounts (Codex-created)

### QA Learner
| Field | Value |
|---|---|
| Email | `qa-learner-b5c7f739@rampup.test` |
| Password | `uUUZGHeVm9ER4m0APbVG772taAw8jytc` |
| Role | LEARNER |

### QA Mentor
| Field | Value |
|---|---|
| Email | `qa-mentor-b5c7f739@rampup.test` |
| Password | `1Fq3d9Pg9SFP8WXuYbDweArNPf2QloGf` |
| Role | MENTOR |

### QA Outsider (no tasks assigned — used for access-denial testing)
| Field | Value |
|---|---|
| Email | `qa-outsider-b5c7f739@rampup.test` |
| Password | `kE5auJotdycAcRaIgti5x08Ltsw4AA-S` |
| Role | LEARNER (but has no assigned tasks) |

---

## 🤖 AI Coach (Server-side only)

The AI coach is **not** a human user account. It runs server-side using:
- **Model**: `gemini-3.1-flash-lite` (Google Gemini API)
- **API Key**: Stored in `.env` as `LLM_API_KEY` — never exposed to the frontend

---

## 🔑 Service Credentials (Server Environment)

These are in the root `.env` file (git-ignored):

| Variable | Purpose | Where Used |
|---|---|---|
| `DATABASE_URL` | Neon PostgreSQL pooled connection | Backend runtime |
| `DATABASE_DIRECT_URL` | Neon PostgreSQL direct connection | Alembic migrations |
| `JWT_SECRET` | Signs access tokens | Backend auth |
| `LLM_API_KEY` | Gemini API key | AI coach |
| `GITHUB_TOKEN` | GitHub REST API (optional, for rate limits) | Source indexing |

---

## 🚀 Quick Test Commands

```bash
# Login as learner (get token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"learner@example.test","password":"AXpQlPQ8N2J-Cw-XC4fP1rFm"}'

# Login as mentor
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"mentor@example.test","password":"sAAwqZFhh9pGUmiXya6afiRc"}'

# Health check
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

---

## 📝 Usage Tips

1. **Use separate browser tabs** (or incognito windows) for learner and mentor
2. Login tokens expire after **120 minutes**
3. The demo task is "Add inventory quantity updates" — the learner learns how to implement quantity updates in the demo inventory API without touching the protected `auth.py` module
4. To trigger an escalation manually, use the learner's "Request Mentor" button
5. To trigger automatic escalation, submit 3 consecutive UNRESOLVED attempts on the same milestone
