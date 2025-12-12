# app/services/item_service.py
from app.schemas.item import ItemCreate, ItemRead

_items: list[ItemRead] = []
_next_id = 1

def create_item(item: ItemCreate) -> ItemRead:
    global _next_id
    new_item = ItemRead(id=_next_id, **item.dict())
    _items.append(new_item)
    _next_id += 1
    return new_item

def list_items() -> list[ItemRead]:
    return _items

