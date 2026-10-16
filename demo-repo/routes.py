"""Existing create route; request validation is delegated to the schema."""
from fastapi import APIRouter
from .schemas import ItemCreate

router = APIRouter()


@router.post('/items')
def create_item(body: ItemCreate):
    return {'name': body.name, 'price_cents': body.price_cents}


# Implementing a quantity update route is left to the learner.
