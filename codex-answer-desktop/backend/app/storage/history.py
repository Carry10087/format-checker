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
