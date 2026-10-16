import base64
import json
import httpx
import pytest
from app.repository import GitHubREST, normalize_path
from app.model_adapter import OpenAIResponses
from app.config import get_settings


def test_github_rest_is_allowlisted_pinned_and_read_only():
    seen = []

    def handler(request):
        seen.append(request)
        if "/commits/" in request.url.path:
            return httpx.Response(200, json={"sha": "a" * 40})
        return httpx.Response(
            200,
            json={
                "type": "file",
                "size": 6,
                "encoding": "base64",
                "content": base64.b64encode(b"line1\n").decode(),
            },
        )

    provider = GitHubREST(
        "owner",
        "repo",
        ["demo-repo/schemas.py"],
        transport=httpx.MockTransport(handler),
    )
    commit = provider.resolve_commit("owner", "repo", "main")
    assert (
        provider.read_file("owner", "repo", "demo-repo/schemas.py", commit) == "line1\n"
    )
    assert seen[-1].url.params["ref"] == "a" * 40
    assert all(request.method == "GET" for request in seen)
    with pytest.raises(ValueError):
        provider.read_file("other", "repo", "demo-repo/schemas.py", commit)
    with pytest.raises(ValueError):
        provider.read_file("owner", "repo", ".env", commit)
    with pytest.raises(ValueError):
        provider.read_file("owner", "repo", "demo-repo/schemas.py", "main")
    assert len(seen) == 2
    provider.client.close()


@pytest.mark.parametrize(
    "path", ["../.env", "/etc/passwd", r"C:\secret", "demo-repo/../auth.py", ".", ""]
)
def test_unsafe_repository_paths_rejected(path):
    with pytest.raises(ValueError):
        normalize_path(path)


def result_json():
    return {
        "action": "HINT",
        "message": "Which boundary case follows?",
        "milestone_id": "validation",
        "citations": [],
        "attempt_assessment": None,
        "escalation": None,
        "proposed_file_paths": [],
    }


def response(data):
    return httpx.Response(
        200,
        json={
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(data)}],
                }
            ],
        },
    )


def test_responses_adapter_uses_read_tools_then_structured_output(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-only-no-live-key")
    monkeypatch.setenv("LLM_MODEL", "configured-test-model")
    get_settings.cache_clear()
    bodies, tools = [], []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        assert body["model"] == "configured-test-model"
        assert body["store"] is False
        assert body["text"]["format"]["strict"] is True
        if len(bodies) == 1:
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "search_project_context",
                            "arguments": '{"query":"quantity"}',
                        }
                    ],
                },
            )
        if len(bodies) == 2:
            assert body["input"][-1]["type"] == "function_call_output"
            return response(result_json())
        return response(
            {
                "supported": True,
                "policy_compatible": True,
                "rationale": "Test-only reviewer response",
            }
        )

    model = OpenAIResponses(transport=httpx.MockTransport(handler))
    result = model.generate(
        {"milestone_id": "validation"},
        lambda name, args: tools.append((name, args)) or [],
    )
    assert result.action == "HINT"
    assert tools == [("search_project_context", {"query": "quantity"})]
    assert model.review({}, result).supported
    assert {t["name"] for t in bodies[0]["tools"]} == {
        "search_project_context",
        "read_project_file",
        "get_learning_history",
    }
    get_settings.cache_clear()


def test_model_schema_repairs_only_once(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-only-no-live-key")
    monkeypatch.setenv("LLM_MODEL", "configured-test-model")
    get_settings.cache_clear()
    calls = []

    def handler(request):
        calls.append(request)
        return response({"invalid": "schema"})

    model = OpenAIResponses(transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        model.generate({}, lambda name, args: [])
    assert len(calls) == 2
    get_settings.cache_clear()


def test_model_function_call_budget_is_four(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-only-no-live-key")
    monkeypatch.setenv("LLM_MODEL", "configured-test-model")
    get_settings.cache_clear()
    calls, executions = [], []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_" + str(len(calls)),
                        "name": "get_learning_history",
                        "arguments": "{}",
                    }
                ],
            },
        )

    model = OpenAIResponses(transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="budget"):
        model.generate({}, lambda name, args: executions.append(name) or [])
    assert len(executions) == 4
    get_settings.cache_clear()
