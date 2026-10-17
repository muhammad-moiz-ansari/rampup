"""Export the task dialogue and answer guide from the server definitions."""

from pathlib import Path
from app.walkthroughs import EXPERIENCES


def main():
    lines = [
        "# RampUp walkthrough guide",
        "",
        "Open http://localhost:8002. Sign in as the learner in one tab and the mentor in another. Actor access details are in the Git-ignored `.local/actor-credentials.md` file.",
        "",
        "The learner sees two tasks. Use the questions below in order. The answer exercise is in **Attempts**; click **Write answer**, enter the code, then **Submit answer**.",
        "",
    ]
    for index, (key, data) in enumerate(EXPERIENCES.items(), 1):
        lines += [f"## Task {index}: {data['title']}", "", data["goal"], ""]
        for number, (question, response) in enumerate(
            zip(data["questions"], data["responses"]), 1
        ):
            lines += [
                f"### Question {number}",
                "",
                question,
                "",
                "**RampUp response**",
                "",
                response,
                "",
            ]
        lines += [
            "### Answer exercise",
            "",
            data["prompt"],
            "",
            "**Starting code**",
            "",
            "```python",
            data["starter"],
            "```",
            "",
        ]
        if key == "quantity":
            lines += [
                "### First submission",
                "",
                "Submit this incomplete update function to bring the issue to the mentor:",
                "",
                "```python",
                data["first_answer"],
                "```",
                "",
                "**RampUp response**",
                "",
                data["handoff"],
                "",
                "### Mentor conversation",
                "",
                "In the mentor tab, open **Review queue** and this learner's case. Review the attempt and both repository sources. Use **Ask a question** to converse; the learner can reply from their conversation tab. Use **Send guidance** when ready to return control to the learner. Your own wording is delivered exactly; no prescribed mentor text is required.",
                "",
                "A useful review covers the existing find_item lookup, the already-validated body.quantity, returning the same item, preserving ItemNotFound, and leaving authentication unchanged.",
                "",
            ]
        lines += [
            "### Correct answer",
            "",
            "```python",
            data["answer"],
            "```",
            "",
            "**Expected feedback**",
            "",
            data["success"],
            "",
            "The saved attempt shows **Correct**. Whitespace and comments may vary. Submitted code is parsed for comparison and is never executed.",
            "",
        ]
    lines += [
        "## Completion",
        "",
        "Correct answers are saved as progress. Session completion still requires **Request completion review**, followed by the assigned mentor's **Confirm completion** and final confirmation. There is no question-count or time-based auto-completion.",
        "",
        "Existing task histories remain stored. The active task list selects the two current task experiences; it does not delete older sessions.",
        "",
    ]
    path = Path(__file__).resolve().parents[2] / "docs/demo-script.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("Updated docs/demo-script.md from task definitions.")


if __name__ == "__main__":
    main()
