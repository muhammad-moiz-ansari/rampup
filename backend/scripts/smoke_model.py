"""One live coaching probe; records real responses/failures without a fake provider."""

import argparse
import os
from uuid import uuid4
import httpx
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--question",
        default="price_cents",
    )
    parser.add_argument(
        "--idempotency-key",
        default=None,
        help="Retry a saved probe using its original key and identical question",
    )
    args = parser.parse_args()
    load_dotenv("../.env")
    load_dotenv(".env")
    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": os.environ["DEMO_LEARNER_EMAIL"],
                "password": os.environ["DEMO_LEARNER_PASSWORD"],
            },
        )
        if login.status_code != 200:
            raise SystemExit(f"Login failed: HTTP {login.status_code}")
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        tasks = client.get("/api/v1/tasks", headers=headers).json()["items"]
        session = client.post(
            "/api/v1/sessions",
            json={"task_id": tasks[0]["id"]},
            headers={**headers, "Idempotency-Key": str(uuid4())},
        ).json()
        if session.get("state") != "ACTIVE":
            raise SystemExit(
                "Resolve the pending mentor/completion review before a live coach probe."
            )
        key = args.idempotency_key or str(uuid4())
        response = client.post(
            f"/api/v1/sessions/{session['id']}/messages",
            json={"content": args.question},
            headers={**headers, "Idempotency-Key": key},
        )
        if response.status_code != 200:
            error = response.json().get("error", {})
            print(
                f"Live coaching NOT verified: HTTP {response.status_code}, {error.get('code', 'UNKNOWN')}. Input saved if COACH_FAILED. Retry key: {key}."
            )
            raise SystemExit(1)
        result = response.json()
        print("Result state:", result["state"])
        print("Latest run:", result["latest_run"])
        if result["open_escalation"]:
            print("Saved case reason:", result["open_escalation"]["reason"])
            print(
                "Escalation does not by itself prove a live model call; configured conflicts can be deterministic."
            )
        elif result["messages"] and result["messages"][-1]["author"] == "AI":
            last = result["messages"][-1]
            print("Guidance:", last["content"])
            print("Citations:", [item["url"] for item in last["citations"]])
            print(
                "Review factual support, usefulness and solution leakage manually before claiming live quality."
            )


if __name__ == "__main__":
    main()
