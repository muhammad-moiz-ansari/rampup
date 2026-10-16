"""Read-only inventory lookup example. Persistence is outside this exercise."""
from .errors import ItemNotFound


def find_item(items, item_id):
    for item in items:
        if item.id == item_id:
            return item
    raise ItemNotFound(item_id)
