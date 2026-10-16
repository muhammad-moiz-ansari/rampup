import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import create_app
from app.schemas import SessionDetail, EscalationDetail


def test_contract_examples_match_real_schemas():
    root = Path(__file__).resolve().parents[2] / "contracts" / "examples"
    SessionDetail.model_validate(json.loads((root / "session.json").read_text()))
    EscalationDetail.model_validate(json.loads((root / "case.json").read_text()))


def test_spa_fallback_cannot_swallow_api_routes(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>Test shell</title>")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path))
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        assert "Test shell" in client.get("/learner/demo").text
        for path in ("/api", "/api/unknown", "/api/v1/unknown"):
            for method in (client.get, client.post):
                response = method(path)
                assert response.status_code == 404
                assert response.json()["error"]["code"] == "NOT_FOUND"
                assert response.headers["content-type"].startswith("application/json")
    get_settings.cache_clear()
