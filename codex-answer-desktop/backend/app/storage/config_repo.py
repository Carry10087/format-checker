from __future__ import annotations

from app.config import settings
from app.schemas import AppConfig
from app.storage.json_store import JsonStore


class ConfigRepository:
    def __init__(self) -> None:
        self.store = JsonStore(
            settings.config_file,
            default=AppConfig(
                api_url=settings.api_url,
                model=settings.model,
                skill_path=str(settings.skill_path),
                local_kb_roots=settings.local_kb_roots,
            ).model_dump(),
        )

    def get(self) -> AppConfig:
        return AppConfig(**self.store.load())

    def save(self, config: AppConfig) -> AppConfig:
        self.store.save(config.model_dump())
        return config
