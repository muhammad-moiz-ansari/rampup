"""Write configured demo actor credentials to an ignored, owner-only local file."""

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".local" / "actor-credentials.md"
FIELDS = (
    ("DEMO_LEARNER_EMAIL", "Learner email"),
    ("DEMO_LEARNER_PASSWORD", "Learner password"),
    ("DEMO_MENTOR_EMAIL", "Mentor email"),
    ("DEMO_MENTOR_PASSWORD", "Mentor password"),
)


def main():
    load_dotenv(ROOT / ".env", override=False)
    missing = [key for key, _ in FIELDS if not os.getenv(key)]
    if missing:
        raise SystemExit("Missing demo account settings: " + ", ".join(missing))

    lines = [
        "# Local Demo Actor Credentials",
        "",
        "Local-only secrets. Do not commit, upload, or share this file.",
        "",
        "API base URL: http://localhost:8000/api/v1",
        "Interactive API docs: http://localhost:8000/docs",
        "Frontend starter: http://localhost:5173 (login/workflows are not implemented yet)",
        "",
    ]
    for key, label in FIELDS:
        lines.append(f"{label}: `{os.environ[key]}`")
    lines.extend(
        [
            "",
            "Roles: learner submits questions/attempts and requests completion; mentor handles assigned escalations and completion reviews.",
            "",
            "Regenerate after changing the demo variables in `.env` by running `python -m scripts.export_demo_credentials` from `backend/`.",
            "",
        ]
    )
    OUTPUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    OUTPUT.chmod(0o600)
    print("Wrote local demo actor credentials to .local/actor-credentials.md")


if __name__ == "__main__":
    main()