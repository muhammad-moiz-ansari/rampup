from scripts.seed_demo import TASK, TASK_CATALOG


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
        assert task["milestone"]["criteria"]