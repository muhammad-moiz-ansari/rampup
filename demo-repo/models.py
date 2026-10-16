"""Inventory model context."""
from dataclasses import dataclass


@dataclass
class Item:
    id: str
    name: str
    price_cents: int
    quantity: int = 0
