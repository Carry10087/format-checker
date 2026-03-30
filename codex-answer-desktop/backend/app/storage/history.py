from __future__ import annotations

from app.config import settings
from app.schemas import HistoryItem
from app.storage.json_store import JsonStore


class HistoryRepository:
    def __init__(self) -> None:
        self.store = JsonStore(settings.history_file, default=[])

    def list_items(self) -> list[HistoryItem]:
        raw = self.store.load()
        return [HistoryItem(**item) for item in raw][::-1]

    def append(self, item: HistoryItem) -> None:
        items = self.store.load()
        items.append(item.model_dump())
        self.store.save(items[-200:])

    def update(self, run_id: str, updates: dict) -> HistoryItem:
        items = self.store.load()

        for index, raw_item in enumerate(items):
            if raw_item.get("run_id") != run_id:
                continue

            current = HistoryItem(**raw_item)
            next_item = current.model_copy(update=updates)
            items[index] = next_item.model_dump()
            self.store.save(items[-200:])
            return next_item

        raise KeyError(run_id)

    def delete(self, run_id: str) -> None:
        items = self.store.load()
        next_items = [item for item in items if item.get("run_id") != run_id]
        if len(next_items) == len(items):
            raise KeyError(run_id)
        self.store.save(next_items)
