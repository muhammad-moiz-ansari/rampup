"""Bounded task experiences with server-owned dialogue and static answer checks."""

import ast
import re
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.models import Escalation, Event, Message, SourceChunk, now
from app.repository import citation
from app.workflow import create_case, finish_operation, messages, touch


EXPERIENCES = {
    "description": {
        "id": str(uuid5(NAMESPACE_URL, "rampup/walkthrough/description/v1")),
        "title": "Add optional item descriptions",
        "level": "Entry level",
        "mode": "CONCEPTS",
        "milestone": "optional-description",
        "goal": "Add an optional description of at most 500 characters to ItemCreate. Preserve the existing name and price constraints.",
        "path": "demo-repo/schemas.py",
        "questions": [
            "Where should I add the optional description field?",
            "How do I make the description optional and limit its length?",
        ],
        "responses": [
            "Add it to ItemCreate in demo-repo/schemas.py. That model already owns the name and price constraints, so the new field belongs beside them. Keep authentication unchanged.",
            "Use a nullable string with a default of None, and put the 500-character limit on Field. Leaving the field out should be valid; supplying more than 500 characters should fail validation. Open Attempts and write the field declaration.",
        ],
        "prompt": "Write the description field declaration inside ItemCreate. The field must accept a string or None, default to None, and reject strings longer than 500 characters. Keep the name and price fields unchanged.",
        "starter": "description: str",
        "answer": "description: str | None = Field(default=None, max_length=500)",
        "answer_label": "Corrected field declaration",
        "success": "Correct. The description is optional, defaults to None, and has a 500-character limit. The existing name and price constraints stay unchanged.",
        "retry": "Not quite. Check all three requirements: a nullable string, a default of None, and max_length=500 on Field.",
    },
    "quantity": {
        "id": str(uuid5(NAMESPACE_URL, "rampup/walkthrough/quantity/v1")),
        "title": "Update inventory quantities",
        "level": "Intermediate",
        "mode": "HINTS",
        "milestone": "validation",
        "goal": "Update the existing item through find_item. The request body is validated by QuantityUpdate; preserve lookup errors and authentication.",
        "path": "demo-repo/service.py",
        "questions": [
            "How should the quantity update use the existing code?",
            "The README and schema disagree about validation. Which should I follow?",
        ],
        "responses": [
            "The request schema validates quantity before the update function runs. Use find_item from demo-repo/service.py to locate the existing Item, update its quantity from body.quantity, and return that same item. An unknown item should keep the existing ItemNotFound behavior.",
            "The current schema uses Pydantic constraints; the README describes older route-level validation. Keep quantity validation in the request schema. In Attempts, write the update function using the existing lookup and validated body. I will check the change and flag the conflicting guidance for review if needed.",
        ],
        "prompt": "Write update_quantity(items, item_id, body). QuantityUpdate has already validated body.quantity as a non-negative integer. Use the existing find_item(items, item_id), assign body.quantity to the returned item's quantity, and return that same item. Let ItemNotFound propagate. Do not change authentication.",
        "starter": "def update_quantity(items, item_id, body):\n    # Find the existing item, update its quantity, and return it.\n    pass",
        "answer": "def update_quantity(items, item_id, body):\n    item = find_item(items, item_id)\n    item.quantity = body.quantity\n    return item",
        "answer_label": "Corrected update_quantity function",
        "first_answer": "def update_quantity(items, item_id, body):\n    return body.quantity",
        "handoff": "This update needs a mentor review: the submitted function must preserve item lookup and update the existing item, while the README and current schema disagree about validation. I have forwarded your attempt and both sources. Add any clarification here; continue after your mentor sends guidance.",
        "success": "Correct. You reuse find_item, update the existing item from the validated request, and return it. ItemNotFound still propagates and authentication is unchanged.",
        "retry": "Not quite. Use find_item(items, item_id), assign body.quantity to that item's quantity, and return the same item. Keep the existing lookup error behavior.",
    },
}


def experience(task):
    return EXPERIENCES.get(task.policy.get("walkthrough_id"))


def exercise_view(task):
    data = experience(task)
    if not data:
        return None
    return {key: data[key] for key in ("prompt", "starter", "answer_label", "path")}


def normalize_question(value):
    return re.sub(r"\s+", " ", value.strip()).rstrip("?.!").casefold()


def correct_answer(value, expected):
    # Parse for comparison only. Learner code is never compiled or executed.
    value = value.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:python)?\s*\n", "", value)
        value = re.sub(r"\n```$", "", value)
    try:
        return ast.dump(ast.parse(value), include_attributes=False) == ast.dump(
            ast.parse(expected), include_attributes=False
        )
    except (SyntaxError, ValueError, RecursionError):
        return False


def handle_walkthrough(db, task, project, session, saved, kind, run, operation, user):
    data = experience(task)
    if not data:
        return None
    key = task.policy["walkthrough_id"]
    source_paths = [data["path"]]
    if key == "quantity":
        source_paths += ["demo-repo/README.md", "demo-repo/schemas.py"]
    sources = list(
        db.scalars(
            select(SourceChunk)
            .where(
                SourceChunk.project_id == project.id,
                SourceChunk.commit_sha == project.commit_sha,
                SourceChunk.path.in_(source_paths),
            )
            .order_by(SourceChunk.path, SourceChunk.start_line)
        )
    )
    evidence = [citation(source, project) for source in sources]
    db.add(
        Event(
            session_id=session.id,
            tool="pinned_context",
            status="SUCCEEDED",
            summary=f"Read {len(evidence)} pinned repository excerpts for the current task.",
        )
    )
    case_summary = "README and current schema disagree about quantity validation."
    prior_case = db.scalar(
        select(Escalation)
        .where(
            Escalation.session_id == session.id,
            Escalation.summary == case_summary,
        )
        .order_by(Escalation.created_at.desc())
    )
    if kind == "message":
        normalized = normalize_question(saved.content)
        index = next(
            (
                i
                for i, q in enumerate(data["questions"])
                if normalize_question(q) == normalized
            ),
            None,
        )
        history = messages(db, session.id)
        if index == 1 and not any(
            m["author"] == "AI" and m["content"] == data["responses"][0]
            for m in history
        ):
            response = (
                "Start with this question so we can establish the context: "
                + data["questions"][0]
            )
        elif index is not None:
            response = data["responses"][index]
            if key == "quantity" and index == 1:
                if prior_case and prior_case.status == "RESOLVED":
                    response = "Your mentor has reviewed this source conflict. Follow their delivered guidance, then open Attempts to write the update function."
        else:
            response = (
                "Keep the task focused on this requirement: "
                + data["goal"]
                + " Ask one of the task questions, open Attempts, or ask your mentor for more context."
            )
    else:
        db.add(
            Event(
                session_id=session.id,
                tool="answer_review",
                status="SUCCEEDED",
                summary="Reviewed the submitted answer against the task criteria; no code executed.",
            )
        )
        if key == "quantity" and not (prior_case and prior_case.status == "RESOLVED"):
            saved.assessment, saved.assessed = "NEEDS_REVIEW", True
            saved.assessment_note = "Your mentor needs to resolve the validation approach before this exercise continues."
            create_case(
                db,
                session,
                "SOURCE_CONFLICT",
                saved.explanation,
                summary=case_summary,
                evidence=evidence,
            )
            response = data["handoff"]
        else:
            accepted = correct_answer(saved.code or saved.explanation, data["answer"])
            saved.assessment = "PROGRESS" if accepted else "UNRESOLVED"
            saved.assessed = True
            saved.assessment_note = data["success"] if accepted else data["retry"]
            response = saved.assessment_note
    db.add(
        Message(
            session_id=session.id, author="AI", content=response, citations=evidence
        )
    )
    run.status, run.ended_at = "SUCCEEDED", now()
    run.error_category = None
    touch(session)
    return finish_operation(db, operation, session, user)
