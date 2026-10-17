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
TASK_CATALOG = [
    {
        "id": str(uuid5(NAMESPACE_URL, "rampup/demo/task/item-description")),
        "title": "Add optional item descriptions",
        "description": (
            "Problem: The item-creation endpoint accepts a name and price, but the inventory team also needs an optional description. The request must reject descriptions longer than 500 characters.\n\n"
            "Difficulty: Entry level\n\n"
            "Goal: Extend the request model and creation response to support an optional description while preserving the existing name and non-negative price rules. Do not change authentication.\n\n"
            "Code structure: demo-repo/schemas.py defines Pydantic request models. demo-repo/routes.py imports a schema and maps request fields into the response. Keep validation in the schema and make the route behavior match it."
        ),
        "assistance_mode": "CONCEPTS",
        "milestone": {
            "id": "optional-description",
            "title": "Extend item creation safely",
            "criteria": [
                "Make description optional and limit it to 500 characters",
                "Preserve the existing name and price constraints",
                "Return the supplied description from the create endpoint",
            ],
        },
    },
    {
        "id": TASK,
        "title": "Add inventory quantity updates",
        "description": (
            "Problem: The inventory API has a create route but no way to update an item's stock quantity. The onboarding README recommends route-level conditionals, while the current code validates request data with Pydantic schemas.\n\n"
            "Difficulty: Intermediate\n\n"
            "Goal: Design a quantity-update endpoint with a non-negative integer quantity. Explain how invalid input and an unknown item should be handled, and keep the protected authentication module unchanged.\n\n"
            "Code structure: demo-repo/schemas.py owns request validation; demo-repo/routes.py defines HTTP endpoints; demo-repo/service.py contains item lookup; demo-repo/errors.py defines the not-found domain error. demo-repo/architecture.md describes the route, schema, and service boundaries."
        ),
        "assistance_mode": "HINTS",
        "milestone": {
            "id": "validation",
            "title": "Design quantity validation and routing",
            "criteria": [
                "Identify the current schema validation convention and the outdated README guidance",
                "Explain how a non-negative quantity is represented and validated",
                "Describe how the route and service handle an unknown item",
                "Preserve authentication",
            ],
        },
        "configured_conflict": [
            "demo-repo/README.md",
            "demo-repo/schemas.py",
        ],
    },
    {
        "id": str(uuid5(NAMESPACE_URL, "rampup/demo/task/not-found")),
        "title": "Handle requests for missing items",
        "description": (
            "Problem: The service lookup raises ItemNotFound when an item ID is absent. A route that uses this service needs a clear HTTP behavior without leaking internal details.\n\n"
            "Difficulty: Advanced\n\n"
            "Goal: Trace the existing domain error and propose a consistent response for an unknown item. Keep the service responsible for lookup, the route responsible for HTTP adaptation, and authentication untouched.\n\n"
            "Code structure: demo-repo/service.py searches items and raises ItemNotFound from demo-repo/errors.py. demo-repo/routes.py owns HTTP endpoints, and demo-repo/architecture.md documents the boundary between routes and services."
        ),
        "assistance_mode": "ATTEMPT_REVIEW",
        "milestone": {
            "id": "missing-item-response",
            "title": "Map the missing-item error to an API response",
            "criteria": [
                "Trace ItemNotFound from service lookup to the API boundary",
                "Choose an appropriate client-visible status and safe response body",
                "Keep lookup logic out of the route and preserve authentication",
            ],
        },
    },
]
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
    for data in TASK_CATALOG:
        policy = {
            "assistance_mode": data["assistance_mode"],
            "protected_paths": ["demo-repo/auth.py"],
            "attempt_threshold": 3,
            "configured_conflict": data.get("configured_conflict", []),
        }
        task = db.get(Task, data["id"])
        if task is None:
            db.add(
                Task(
                    id=data["id"],
                    project_id=PROJECT,
                    learner_id=accounts[0].id,
                    mentor_id=accounts[1].id,
                    title=data["title"],
                    description=data["description"],
                    policy=policy,
                    milestones=[data["milestone"]],
                )
            )
        elif data["id"] == TASK:
            task.title = data["title"]
            task.description = data["description"]
            task.milestones = [data["milestone"]]
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
