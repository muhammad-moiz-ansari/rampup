# Task 1 Conversation

## Learner

Where should I add the description?

## RampUp

Start in `schemas.py`. `ItemCreate` is the request boundary; then check `routes.py` to see the same model passed to the create service and returned as `ItemRead`.

## Learner

What validation pattern should I follow?

## RampUp

Add the optional field beside the existing name and price fields in `ItemCreate`. Use a nullable string with a default of `None` and `max_length=500`; the route already passes that model through to creation.

## Learner Submission

Explanation:

> Add description as an optional string with a 500-character maximum. Keep the existing name and price validation unchanged, and include description in the `ItemRead` response.

Code:

```python
description: str | None = Field(default=None, max_length=500)
```

Files: `demo-repo/schemas.py`, `demo-repo/routes.py`

## RampUp

Your work meets the task criteria. Task complete.
