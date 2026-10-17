import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.config import get_settings
from app.db import get_db, postgres_url, get_engine
from app.main import create_app
from scripts.seed_demo import seed, TASK
from app.models import User, Project, SourceChunk, Task, uid
from app.model_adapter import CoachResult, SupportReview


class FakeModel:
    def __init__(self):
        self.calls = 0
        self.classification = "UNRESOLVED"
        self.fail = False
        self.bad_citation = False

    def generate(self, context, toolbox):
        self.calls += 1
        if self.fail:
            raise TimeoutError("fake test timeout")
        evidence = context["evidence"][0]
        return CoachResult.model_validate(
            {
                "action": "HINT",
                "message": "Which boundary case follows from this schema constraint?",
                "milestone_id": context["milestone_id"],
                "citations": [
                    {
                        "source_id": evidence["source_id"],
                        "start_line": 999
                        if self.bad_citation
                        else evidence["start_line"],
                        "end_line": 999 if self.bad_citation else evidence["end_line"],
                        "quote": evidence["excerpt"],
                    }
                ],
                "attempt_assessment": {
                    "classification": self.classification,
                    "rationale": "Explicit test assessment.",
                }
                if context["input_kind"] == "attempt"
                else None,
                "escalation": None,
                "proposed_file_paths": [],
            }
        )

    def review(self, context, result):
        return SupportReview(
            supported=True,
            policy_compatible=True,
            rationale="Deterministic test reviewer",
        )


@pytest.fixture(scope="session")
def pg_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL required: database tests run only on real PostgreSQL"
        )
    parsed = __import__("sqlalchemy").engine.make_url(url)
    if not parsed.database or not parsed.database.endswith("_test"):
        raise RuntimeError(
            "Tests require a disposable database whose name ends in _test"
        )
    os.environ["DATABASE_URL"] = url
    os.environ["DATABASE_DIRECT_URL"] = url
    os.environ["JWT_SECRET"] = "test-only-secret-" + "x" * 48
    get_settings.cache_clear()
    get_engine.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(postgres_url(url), pool_size=8, max_overflow=4)
    yield engine
    engine.dispose()


@pytest.fixture
def system(pg_engine):
    from app.models import Base

    with pg_engine.begin() as connection:
        names = ", ".join('"' + name + '"' for name in Base.metadata.tables)
        connection.execute(text("TRUNCATE " + names + " CASCADE"))
    factory = sessionmaker(pg_engine, expire_on_commit=False)
    with factory() as db:
        seed(
            db,
            "learner@example.test",
            "test-learner-password",
            "mentor@example.test",
            "test-mentor-password",
            enable_walkthroughs=False,
        )
        db.add(
            User(
                id=uid(),
                email="unrelated@example.test",
                name="Unrelated",
                role="LEARNER",
                workspace_id=db.query(User).first().workspace_id,
                password_hash=__import__(
                    "app.auth", fromlist=["passwords"]
                ).passwords.hash("test-unrelated-password"),
            )
        )
        project = db.query(Project).first()
        project.commit_sha = "a" * 40
        task = db.get(Task, TASK)
        # Normal tests exercise AI without the explicitly configured demo conflict.
        task.policy = {**task.policy, "configured_conflict": []}
        db.add(
            SourceChunk(
                project_id=project.id,
                path="demo-repo/schemas.py",
                commit_sha="a" * 40,
                start_line=1,
                end_line=2,
                content="quantity validation schema\nUse Pydantic Field constraints.",
                search_document=__import__("sqlalchemy").func.to_tsvector(
                    "simple", "quantity validation schema Pydantic Field constraints"
                ),
            )
        )
        db.commit()
    app = create_app()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    model = FakeModel()
    app.state.model = model
    client = TestClient(app)
    tokens = {}
    for role in ("learner", "mentor", "unrelated"):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": f"{role}@example.test", "password": f"test-{role}-password"},
        )
        assert response.status_code == 200, response.text
        tokens[role] = response.json()["access_token"]

    def headers(role="learner", key=None):
        return {
            "Authorization": "Bearer " + tokens[role],
            "Idempotency-Key": key or str(uuid4()),
        }

    task_id = TASK
    response = client.post(
        "/api/v1/sessions", headers=headers(), json={"task_id": task_id}
    )
    assert response.status_code == 200, response.text
    yield {
        "client": client,
        "app": app,
        "factory": factory,
        "model": model,
        "headers": headers,
        "session": response.json(),
        "task_id": task_id,
    }
    client.close()
