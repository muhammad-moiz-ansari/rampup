from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import select, func
from app.models import Escalation, SourceChunk
from app.main import create_app
from fastapi.testclient import TestClient
from app.db import get_db


def post(s, suffix, body, role="learner", key=None):
    return s["client"].post(
        f"/api/v1/sessions/{s['session']['id']}/{suffix}",
        json=body,
        headers=s["headers"](role, key),
    )


def case(s):
    response = post(
        s,
        "escalations",
        {"reason": "MANUAL", "question": "Please review quantity validation"},
    )
    assert response.status_code == 200, response.text
    return response.json()["open_escalation"]


def decide(
    s,
    case_id,
    revision,
    action="SEND_GUIDANCE",
    text="Exact edited human guidance",
    key=None,
    role="mentor",
):
    return s["client"].post(
        f"/api/v1/escalations/{case_id}/decision",
        json={"action": action, "expected_revision": revision, "text": text},
        headers=s["headers"](role, key),
    )


def test_auth_assignment_and_validation(system):
    s = system
    assert s["client"].get("/api/v1/tasks").status_code == 401
    assert (
        s["client"]
        .get(
            f"/api/v1/sessions/{s['session']['id']}", headers=s["headers"]("unrelated")
        )
        .status_code
        == 404
    )
    with s["factory"]() as db:
        source_id = db.scalar(select(SourceChunk.id))
    assert (
        s["client"]
        .get(f"/api/v1/sources/{source_id}", headers=s["headers"]("unrelated"))
        .status_code
        == 404
    )
    assert post(s, "messages", {"content": "x", "role": "MENTOR"}).status_code == 422
    assert (
        post(s, "messages", {"content": "x"}, key="not-a-uuid").json()["error"]["code"]
        == "VALIDATION_ERROR"
    )
    assert (
        post(
            s,
            "completion-decision",
            {"expected_version": 1, "approved": True, "text": "done"},
        ).status_code
        == 403
    )
    c = case(s)
    assert decide(s, c["id"], 1, role="learner").status_code == 403
    assert (
        s["client"]
        .get(f"/api/v1/escalations/{c['id']}", headers=s["headers"]("unrelated"))
        .status_code
        == 404
    )


def test_manual_loop_exact_once_and_stale_revision(system):
    s = system
    c = case(s)
    assert s["model"].calls == 0
    response = post(s, "messages", {"content": "Additional learner clarification"})
    assert response.json()["state"] == "WAITING_FOR_MENTOR"
    assert s["model"].calls == 0
    refreshed = (
        s["client"]
        .get(f"/api/v1/escalations/{c['id']}", headers=s["headers"]("mentor"))
        .json()
    )
    assert refreshed["revision"] == 2
    assert decide(s, c["id"], 1).status_code == 409
    assert (
        decide(s, c["id"], 2, "ASK_QUESTION", "What differs?").json()["state"]
        == "WAITING_FOR_MENTOR"
    )
    assert (
        decide(s, c["id"], 3, "REJECT_SUGGESTION", "REJECTED SECRET DRAFT").status_code
        == 200
    )
    assert (
        decide(s, c["id"], 4, "TAKE_OVER", "I will guide this review.").json()["state"]
        == "MENTOR_ACTIVE"
    )
    key = str(uuid4())
    approved = decide(s, c["id"], 5, key=key)
    replay = decide(s, c["id"], 5, key=key)
    assert approved.status_code == replay.status_code == 200
    assert approved.json() == replay.json()
    assert approved.json()["state"] == "ACTIVE"
    assert [m["content"] for m in approved.json()["messages"]].count(
        "Exact edited human guidance"
    ) == 1
    assert "REJECTED SECRET DRAFT" not in str(approved.json())
    assert decide(s, c["id"], 5, text="different", key=key).status_code == 409


def test_simultaneous_escalations_and_restart_persistence(system):
    s = system
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: post(
                    s, "escalations", {"reason": "MANUAL", "question": "help"}
                ),
                range(2),
            )
        )
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    with s["factory"]() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Escalation)
                .where(Escalation.status == "OPEN")
            )
            == 1
        )
    restarted = create_app()
    restarted.dependency_overrides[get_db] = s["app"].dependency_overrides[get_db]
    with TestClient(restarted) as client:
        detail = client.get(
            f"/api/v1/sessions/{s['session']['id']}", headers=s["headers"]()
        ).json()
        assert (
            detail["open_escalation"]["id"]
            == responses[0].json()["open_escalation"]["id"]
        )


def test_completion_requires_mentor_and_completed_is_read_only(system):
    s = system
    requested = post(
        s, "completion-request", {"expected_version": s["session"]["version"]}
    ).json()
    assert requested["state"] == "COMPLETION_REVIEW"
    changes = post(
        s,
        "completion-decision",
        {
            "expected_version": requested["version"],
            "approved": False,
            "text": "Explain one more boundary case",
        },
        "mentor",
    ).json()
    assert changes["state"] == "ACTIVE"
    requested = post(
        s, "completion-request", {"expected_version": changes["version"]}
    ).json()
    done = post(
        s,
        "completion-decision",
        {
            "expected_version": requested["version"],
            "approved": True,
            "text": "Reviewed and complete",
        },
        "mentor",
    ).json()
    assert done["state"] == "COMPLETED"
    assert post(s, "messages", {"content": "quantity"}).status_code == 409


def test_unique_session_and_body_key_conflict(system):
    s = system
    assert s["session"]["updated_at"].endswith("Z")
    response = s["client"].post(
        "/api/v1/sessions", json={"task_id": s["task_id"]}, headers=s["headers"]()
    )
    assert response.json()["id"] == s["session"]["id"]
    key = str(uuid4())
    assert (
        post(s, "messages", {"content": "quantity validation"}, key=key).status_code
        == 200
    )
    assert post(s, "messages", {"content": "other"}, key=key).status_code == 409


def test_simultaneous_mentor_decisions_only_one_wins(system):
    s = system
    c = case(s)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda text: decide(s, c["id"], c["revision"], text=text),
                ["first guidance", "second guidance"],
            )
        )
    assert sorted(r.status_code for r in responses) == [200, 409], [
        r.text for r in responses
    ]
    latest = (
        s["client"]
        .get(f"/api/v1/sessions/{s['session']['id']}", headers=s["headers"]())
        .json()
    )
    assert len([m for m in latest["messages"] if m["author"] == "MENTOR"]) == 1
