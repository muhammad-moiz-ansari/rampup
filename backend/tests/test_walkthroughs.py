from uuid import uuid4

from sqlalchemy import func, select

from app.models import Escalation, Project, SourceChunk, Task
from app.walkthroughs import EXPERIENCES, correct_answer


def activate(s, key):
    data = EXPERIENCES[key]
    with s["factory"]() as db:
        task = db.get(Task, data["id"])
        task.policy = {**task.policy, "walkthrough_id": key}
        project = db.get(Project, task.project_id)
        for path, content in (
            ("demo-repo/README.md", "Historical route-level quantity validation."),
            ("demo-repo/service.py", "def find_item(items, item_id): pass"),
        ):
            if not db.scalar(
                select(SourceChunk).where(
                    SourceChunk.project_id == project.id, SourceChunk.path == path
                )
            ):
                db.add(
                    SourceChunk(
                        project_id=project.id,
                        path=path,
                        commit_sha=project.commit_sha,
                        start_line=1,
                        end_line=1,
                        content=content,
                        search_document=func.to_tsvector("simple", content),
                    )
                )
        db.commit()
    session = (
        s["client"]
        .post("/api/v1/sessions", json={"task_id": data["id"]}, headers=s["headers"]())
        .json()
    )
    return data, session


def post(s, session, endpoint, body, role="learner", key=None):
    return s["client"].post(
        f"/api/v1/sessions/{session['id']}/{endpoint}",
        json=body,
        headers=s["headers"](role, key),
    )


def answer(s, session, data, code=None, key=None):
    return post(
        s,
        session,
        "attempts",
        {
            "milestone_id": session["current_milestone_id"],
            "explanation": data["prompt"],
            "code": code if code is not None else data["answer"],
            "file_paths": [data["path"]],
        },
        key=key,
    )


def test_entry_questions_answer_and_exact_once_delivery(system):
    s = system
    data, session = activate(s, "description")
    assert session["task"]["exercise"]["starter"] == data["starter"]
    assert "answer" not in session["task"]["exercise"]
    for q, response in zip(data["questions"], data["responses"]):
        session = post(s, session, "messages", {"content": q}).json()
        assert session["messages"][-1]["content"] == response
        assert session["state"] == "ACTIVE"
    key = str(uuid4())
    first = answer(s, session, data, key=key)
    assert first.status_code == 200
    assert answer(s, session, data, key=key).json() == first.json()
    session = first.json()
    assert len(session["attempts"]) == 1
    assert session["attempts"][0]["assessment"] == "PROGRESS"
    assert session["messages"][-1]["content"].startswith("Correct.")
    assert session["state"] == "ACTIVE"  # Completion still requires mentor approval.
    assert s["model"].calls == 0


def test_bad_entry_answer_gets_specific_feedback_then_accepts_correction(system):
    data, session = activate(system, "description")
    wrong = answer(
        system, session, data, "description: str = Field(max_length=501)"
    ).json()
    assert wrong["attempts"][-1]["assessment"] == "UNRESOLVED"
    assert "default of None" in wrong["messages"][-1]["content"]
    corrected = answer(system, wrong, data).json()
    assert corrected["attempts"][-1]["assessment"] == "PROGRESS"
    assert len(corrected["attempts"]) == 2


def test_second_question_does_not_skip_context(system):
    data, session = activate(system, "quantity")
    response = post(
        system, session, "messages", {"content": data["questions"][1]}
    ).json()
    assert response["messages"][-1]["content"].startswith("Start with this question")
    assert response["open_escalation"] is None


def test_intermediate_attempt_handoff_human_conversation_and_correction(system):
    s = system
    data, session = activate(s, "quantity")
    for q in data["questions"]:
        session = post(s, session, "messages", {"content": q}).json()
        assert session["state"] == "ACTIVE"
    key = str(uuid4())
    first = answer(s, session, data, data["first_answer"], key)
    assert first.status_code == 200
    session = first.json()
    assert answer(s, session, data, data["first_answer"], key).json() == session
    assert session["state"] == "WAITING_FOR_MENTOR"
    case = session["open_escalation"]
    assert case["reason"] == "SOURCE_CONFLICT"
    assert case["proposed_guidance"] == ""
    assert {c["path"] for c in case["evidence"]} >= {
        "demo-repo/README.md",
        "demo-repo/schemas.py",
    }
    assert answer(s, session, data).status_code == 409
    session = post(
        s,
        session,
        "messages",
        {"content": "Should find_item keep handling unknown IDs?"},
    ).json()
    path = f"/api/v1/escalations/{case['id']}/decision"
    stale = s["client"].post(
        path,
        json={
            "action": "SEND_GUIDANCE",
            "expected_revision": case["revision"],
            "text": "Use find_item.",
        },
        headers=s["headers"]("mentor"),
    )
    assert stale.status_code == 409
    latest = session["open_escalation"]
    decision = s["client"].post(
        path,
        json={
            "action": "SEND_GUIDANCE",
            "expected_revision": latest["revision"],
            "text": "Yes. Use find_item, assign body.quantity to the existing item, and return it. Keep ItemNotFound unchanged.",
        },
        headers=s["headers"]("mentor"),
    )
    assert decision.status_code == 200
    session = decision.json()
    assert session["state"] == "ACTIVE"
    final = answer(s, session, data).json()
    assert final["attempts"][-1]["assessment"] == "PROGRESS"
    assert s["model"].calls == 0
    with s["factory"]() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Escalation)
                .where(Escalation.session_id == session["id"])
            )
            == 1
        )


def test_answer_comparison_never_executes_code(tmp_path):
    marker = tmp_path / "executed"
    malicious = f"__import__('pathlib').Path({str(marker)!r}).write_text('unsafe')"
    assert not correct_answer(malicious, EXPERIENCES["description"]["answer"])
    assert not marker.exists()
    assert correct_answer(
        "# optional\ndescription: str|None=Field(default=None,max_length=500)",
        EXPERIENCES["description"]["answer"],
    )
