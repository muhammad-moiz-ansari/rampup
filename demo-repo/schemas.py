"""Current request schema convention: validate request fields in Pydantic schemas."""
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_cents: int = Field(ge=0)


# Quantity update schema is intentionally absent: it is the learner's task.
