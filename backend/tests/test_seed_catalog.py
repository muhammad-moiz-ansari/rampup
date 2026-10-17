from scripts.seed_demo import TASK, TASK_CATALOG
from app.coach import (
    COACH_FAILURE_MESSAGES,
    MODEL_HTTP_FAILURE_CATEGORIES,
    model_http_failure_category,
)
import httpx


def test_demo_task_catalog_has_distinct_levels_and_problem_context():
    assert len(TASK_CATALOG) == 3
    assert len({task["id"] for task in TASK_CATALOG}) == len(TASK_CATALOG)
    assert TASK in {task["id"] for task in TASK_CATALOG}
    assert {
        task["description"].split("Difficulty: ", 1)[1].splitlines()[0]
        for task in TASK_CATALOG
    } == {"Entry level", "Intermediate", "Advanced"}
    assert {task["assistance_mode"] for task in TASK_CATALOG} == {
        "CONCEPTS",
        "HINTS",
        "ATTEMPT_REVIEW",
    }
    for task in TASK_CATALOG:
        assert all(
            section in task["description"]
            for section in ("Difficulty:", "Problem:", "Goal:", "Code structure:")
        )
        assert task["description"].startswith("Problem:")
        tree = task["description"].split("Code structure:\n", 1)[1]
        assert tree.startswith("demo-repo/\n|")
        assert "\\-- auth.py" in tree
        assert task["milestone"]["criteria"]


def test_model_failure_messages_name_actionable_causes():
    assert "not configured" in COACH_FAILURE_MESSAGES["MODEL_NOT_CONFIGURED"]
    assert "credentials" in COACH_FAILURE_MESSAGES["MODEL_AUTH"]
    assert "rate-limiting" in COACH_FAILURE_MESSAGES["MODEL_RATE_LIMIT"]
    assert "timed out" in COACH_FAILURE_MESSAGES["MODEL_TIMEOUT"]
    assert "could not validate" in COACH_FAILURE_MESSAGES["MODEL_OUTPUT_INVALID"]
    assert MODEL_HTTP_FAILURE_CATEGORIES[404] == "MODEL_CONFIGURATION"


def test_invalid_google_api_key_is_classified_as_authentication_failure():
    response = httpx.Response(
        400,
        json={
            "error": {
                "message": "API key not valid. Please pass a valid API key.",
                "details": [
                    {
                        "reason": "API_KEY_INVALID",
                    }
                ],
            }
        },
    )
    error = httpx.HTTPStatusError(
        "Bad request", request=httpx.Request("POST", "https://example.test"), response=response
    )
    assert model_http_failure_category(error) == "MODEL_AUTH"