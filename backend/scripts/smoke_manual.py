"""Exercise the real HTTP learner → mentor → learner loop without model calls.

This deliberately creates messages and a resolved case using the seeded demo accounts.
Credentials are read from ignored environment configuration and never printed.
"""

import argparse
import os
from uuid import uuid4
import httpx
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    load_dotenv("../.env")
    load_dotenv(".env")
    with httpx.Client(
        base_url=args.base_url, timeout=60, follow_redirects=False
    ) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200
        tokens = {}
        for role in ("LEARNER", "MENTOR"):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": os.environ[f"DEMO_{role}_EMAIL"],
                    "password": os.environ[f"DEMO_{role}_PASSWORD"],
                },
            )
            assert response.status_code == 200, (
                f"{role} login failed: HTTP {response.status_code}"
            )
            tokens[role] = response.json()["access_token"]

        def headers(role, key=None):
            return {
                "Authorization": "Bearer " + tokens[role],
                "Idempotency-Key": key or str(uuid4()),
            }

        def post(path, body, role="LEARNER", key=None):
            response = client.post(
                "/api/v1" + path, json=body, headers=headers(role, key)
            )
            assert response.status_code == 200, f"{path}: HTTP {response.status_code}"
            return response.json()

        tasks = client.get("/api/v1/tasks", headers=headers("LEARNER")).json()["items"]
        session = post("/sessions", {"task_id": tasks[0]["id"]})
        if session["state"] == "COMPLETED":
            raise SystemExit(
                "Demo task already completed; smoke command preserves it and requires a fresh assigned task."
            )
        path = f"/sessions/{session['id']}"
        session = post(
            path + "/escalations",
            {
                "reason": "MANUAL",
                "question": "Smoke check: please review my next step.",
            },
        )
        assert session["state"] in ("WAITING_FOR_MENTOR", "MENTOR_ACTIVE")
        session = post(
            path + "/messages",
            {"content": "Smoke check clarification: I will preserve authentication."},
        )
        case = session["open_escalation"]
        guidance = "Human-approved smoke guidance " + str(uuid4())
        key = str(uuid4())
        decision = {
            "action": "SEND_GUIDANCE",
            "expected_revision": case["revision"],
            "text": guidance,
        }
        first = post(f"/escalations/{case['id']}/decision", decision, "MENTOR", key)
        replay = post(f"/escalations/{case['id']}/decision", decision, "MENTOR", key)
        assert first == replay
        latest = client.get("/api/v1" + path, headers=headers("LEARNER")).json()
        assert latest["state"] == "ACTIVE" and latest["open_escalation"] is None
        assert sum(m["content"] == guidance for m in latest["messages"]) == 1
        print(
            f"Verified HTTP logins, saved case, paused clarification, exact-once approved delivery and ACTIVE resume. Session {session['id']}."
        )


if __name__ == "__main__":
    main()
