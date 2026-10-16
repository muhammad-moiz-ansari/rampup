from fastapi.testclient import TestClient
from app.main import create_app


def test_health_and_truthful_readiness(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(create_app())
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 503
    assert client.get("/api/unknown").json()["error"]["code"] == "NOT_FOUND"
