import json
import httpx
import pytest
from app.config import get_settings
from app.gemini_adapter import GeminiGenerateContent
from app.model_factory import configured_model
from test_adapters import result_json


def gemini_response(parts):
    return httpx.Response(
        200,
        json={
            "candidates": [
                {"finishReason": "STOP", "content": {"role": "model", "parts": parts}}
            ]
        },
    )


def test_gemini_keeps_model_choice_header_auth_and_tool_signatures(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-only-gemini-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-configured-test")
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    get_settings.cache_clear()
    assert isinstance(configured_model(), GeminiGenerateContent)
    bodies, executions = [], []

    def handler(request):
        assert request.url.path.endswith("/gemini-configured-test:generateContent")
        assert request.headers["x-goog-api-key"] == "test-only-gemini-key"
        assert "key" not in request.url.params
        body = json.loads(request.content)
        bodies.append(body)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        if len(bodies) == 1:
            assert {t["name"] for t in body["tools"][0]["functionDeclarations"]} == {
                "search_project_context",
                "read_project_file",
                "get_learning_history",
            }
            return gemini_response(
                [
                    {
                        "thoughtSignature": "opaque-test-signature",
                        "functionCall": {
                            "name": "get_learning_history",
                            "args": {},
                            "id": "call-1",
                        },
                    }
                ]
            )
        if len(bodies) == 2:
            assert (
                body["contents"][-2]["parts"][0]["thoughtSignature"]
                == "opaque-test-signature"
            )
            assert (
                body["contents"][-1]["parts"][0]["functionResponse"]["id"] == "call-1"
            )
            return gemini_response([{"text": json.dumps(result_json())}])
        return gemini_response(
            [
                {
                    "text": json.dumps(
                        {
                            "supported": True,
                            "policy_compatible": True,
                            "rationale": "Test reviewer",
                        }
                    )
                }
            ]
        )

    adapter = GeminiGenerateContent(transport=httpx.MockTransport(handler))
    result = adapter.generate({}, lambda name, args: executions.append(name) or [])
    assert executions == ["get_learning_history"]
    assert adapter.review({}, result).supported
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "mode,expected_calls,expected_executions", [("bad_schema", 2, 0), ("tools", 5, 4)]
)
def test_gemini_repair_and_read_tool_budget(
    monkeypatch, mode, expected_calls, expected_executions
):
    monkeypatch.setenv("LLM_API_KEY", "test-only-gemini-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-configured-test")
    get_settings.cache_clear()
    requests, executions = [], []

    def handler(request):
        requests.append(request)
        if mode == "bad_schema":
            return gemini_response([{"text": '{"bad":"schema"}'}])
        return gemini_response(
            [{"functionCall": {"name": "get_learning_history", "args": {}}}]
        )

    adapter = GeminiGenerateContent(transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        adapter.generate({}, lambda name, args: executions.append(name) or [])
    assert len(requests) == expected_calls
    assert len(executions) == expected_executions
    get_settings.cache_clear()
