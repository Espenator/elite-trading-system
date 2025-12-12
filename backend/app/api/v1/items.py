# app/api/v1/items.py
from fastapi import APIRouter
from app.schemas.item import ItemCreate, ItemRead
from app.services.item_service import create_item, list_items

router = APIRouter()

@router.post("/", response_model=ItemRead)
def create_item_endpoint(item: ItemCreate):
    return create_item(item)

@router.get("/", response_model=list[ItemRead])
def list_items_endpoint():
    return list_items()

