"""Deliberate, idempotent seed. Existing passwords and learner history are preserved."""

import os
from uuid import uuid5, NAMESPACE_URL
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import passwords
from app.config import get_settings
from app.db import get_engine
from app.models import User, Project, Task

WORKSPACE = str(uuid5(NAMESPACE_URL, "rampup/demo/workspace"))
PROJECT = str(uuid5(NAMESPACE_URL, "rampup/demo/project"))
TASK = str(uuid5(NAMESPACE_URL, "rampup/demo/task"))
PATHS = [
    "demo-repo/README.md",
    "demo-repo/schemas.py",
    "demo-repo/routes.py",
    "demo-repo/architecture.md",
    "demo-repo/auth.py",
    "demo-repo/errors.py",
    "demo-repo/models.py",
    "demo-repo/service.py",
    "demo-repo/testing.md",
    "demo-repo/conventions.md",
]


def seed(
    db: Session,
    learner_email: str,
    learner_password: str,
    mentor_email: str,
    mentor_password: str,
):
    if learner_email.strip().lower() == mentor_email.strip().lower():
        raise ValueError("Demo accounts must have different emails")
    accounts = []
    for role, email, password in [
        ("LEARNER", learner_email, learner_password),
        ("MENTOR", mentor_email, mentor_password),
    ]:
        email = email.strip().lower()
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            if len(password) < 12:
                raise ValueError("Use demo passwords of at least 12 characters")
            user = User(
                email=email,
                password_hash=passwords.hash(password),
                name=f"Demo {role.title()}",
                role=role,
                workspace_id=WORKSPACE,
            )
            db.add(user)
            db.flush()
        if user.role != role or user.workspace_id != WORKSPACE:
            raise ValueError("Existing account has incompatible role/workspace")
        accounts.append(user)
    if not db.get(Project, PROJECT):
        settings = get_settings()
        db.add(
            Project(
                id=PROJECT,
                workspace_id=WORKSPACE,
                owner=settings.github_owner,
                name=settings.github_repo,
                commit_sha="",
                allowed_paths=PATHS,
            )
        )
        db.flush()
    if not db.get(Task, TASK):
        db.add(
            Task(
                id=TASK,
                project_id=PROJECT,
                learner_id=accounts[0].id,
                mentor_id=accounts[1].id,
                title="Add inventory quantity updates",
                description="Explain how to add quantity updates using current request validation, without touching authentication. Learner code is never executed by RampUp.",
                policy={
                    "assistance_mode": "HINTS",
                    "protected_paths": ["demo-repo/auth.py"],
                    "attempt_threshold": 3,
                    "configured_conflict": [
                        "demo-repo/README.md",
                        "demo-repo/schemas.py",
                    ],
                },
                milestones=[
                    {
                        "id": "validation",
                        "title": "Explain quantity validation",
                        "criteria": [
                            "Identify the current schema validation convention",
                            "Explain rejection of invalid quantities",
                            "Preserve authentication",
                        ],
                    }
                ],
            )
        )
    db.commit()


def main():
    # Settings loads the ignored root .env; passwords are deliberately not part of API settings.
    from dotenv import load_dotenv

    load_dotenv("../.env")
    load_dotenv(".env")
    required = (
        "DEMO_LEARNER_EMAIL",
        "DEMO_LEARNER_PASSWORD",
        "DEMO_MENTOR_EMAIL",
        "DEMO_MENTOR_PASSWORD",
    )
    if not all(os.getenv(key) for key in required):
        raise SystemExit("Set demo account variables in ignored .env before seeding.")
    with Session(get_engine()) as db:
        seed(db, *(os.environ[key] for key in required))
    print("Demo seed complete; existing accounts and history preserved.")


if __name__ == "__main__":
    main()
