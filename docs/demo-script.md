# RampUp walkthrough guide

Open http://localhost:8002. Sign in as the learner in one tab and the mentor in another. Actor access details are in the Git-ignored `.local/actor-credentials.md` file.

The learner sees two tasks. Use the questions below in order. The answer exercise is in **Attempts**; click **Write answer**, enter the code, then **Submit answer**.

## Task 1: Add optional item descriptions

Add an optional description of at most 500 characters to ItemCreate. Preserve the existing name and price constraints.

### Question 1

Where should I add the optional description field?

**RampUp response**

Add it to ItemCreate in demo-repo/schemas.py. That model already owns the name and price constraints, so the new field belongs beside them. Keep authentication unchanged.

### Question 2

How do I make the description optional and limit its length?

**RampUp response**

Use a nullable string with a default of None, and put the 500-character limit on Field. Leaving the field out should be valid; supplying more than 500 characters should fail validation. Open Attempts and write the field declaration.

### Answer exercise

Write the description field declaration inside ItemCreate. The field must accept a string or None, default to None, and reject strings longer than 500 characters. Keep the name and price fields unchanged.

**Starting code**

```python
description: str
```

### Correct answer

```python
description: str | None = Field(default=None, max_length=500)
```

**Expected feedback**

Correct. The description is optional, defaults to None, and has a 500-character limit. The existing name and price constraints stay unchanged.

The saved attempt shows **Correct**. Whitespace and comments may vary. Submitted code is parsed for comparison and is never executed.

## Task 2: Update inventory quantities

Update the existing item through find_item. The request body is validated by QuantityUpdate; preserve lookup errors and authentication.

### Question 1

How should the quantity update use the existing code?

**RampUp response**

The request schema validates quantity before the update function runs. Use find_item from demo-repo/service.py to locate the existing Item, update its quantity from body.quantity, and return that same item. An unknown item should keep the existing ItemNotFound behavior.

### Question 2

The README and schema disagree about validation. Which should I follow?

**RampUp response**

The current schema uses Pydantic constraints; the README describes older route-level validation. Keep quantity validation in the request schema. In Attempts, write the update function using the existing lookup and validated body. I will check the change and flag the conflicting guidance for review if needed.

### Answer exercise

Write update_quantity(items, item_id, body). QuantityUpdate has already validated body.quantity as a non-negative integer. Use the existing find_item(items, item_id), assign body.quantity to the returned item's quantity, and return that same item. Let ItemNotFound propagate. Do not change authentication.

**Starting code**

```python
def update_quantity(items, item_id, body):
    # Find the existing item, update its quantity, and return it.
    pass
```

### First submission

Submit this incomplete update function to bring the issue to the mentor:

```python
def update_quantity(items, item_id, body):
    return body.quantity
```

**RampUp response**

This update needs a mentor review: the submitted function must preserve item lookup and update the existing item, while the README and current schema disagree about validation. I have forwarded your attempt and both sources. Add any clarification here; continue after your mentor sends guidance.

### Mentor conversation

In the mentor tab, open **Review queue** and this learner's case. Review the attempt and both repository sources. Use **Ask a question** to converse; the learner can reply from their conversation tab. Use **Send guidance** when ready to return control to the learner. Your own wording is delivered exactly; no prescribed mentor text is required.

A useful review covers the existing find_item lookup, the already-validated body.quantity, returning the same item, preserving ItemNotFound, and leaving authentication unchanged.

### Correct answer

```python
def update_quantity(items, item_id, body):
    item = find_item(items, item_id)
    item.quantity = body.quantity
    return item
```

**Expected feedback**

Correct. You reuse find_item, update the existing item from the validated request, and return it. ItemNotFound still propagates and authentication is unchanged.

The saved attempt shows **Correct**. Whitespace and comments may vary. Submitted code is parsed for comparison and is never executed.

## Completion

Correct answers are saved as progress. Session completion still requires **Request completion review**, followed by the assigned mentor's **Confirm completion** and final confirmation. There is no question-count or time-based auto-completion.

Existing task histories remain stored. The active task list selects the two current task experiences; it does not delete older sessions.
