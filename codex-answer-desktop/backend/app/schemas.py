from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    title: str
    content: str
    source_type: str
    url_or_path: str
    timestamp: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class RunRequest(BaseModel):
    query: str
    web_enabled: bool = True
    local_kb_enabled: bool = True
    rules_profile: str = "strict-answer-formatter"
    debug: bool = False


class RunResponse(BaseModel):
    run_id: str
    status: str
    final_answer: str
    citations_present: bool
    source_count: int
    debug_trace: dict[str, Any] | None = None


class HistoryItem(BaseModel):
    run_id: str
    query: str
    created_at: str
    final_answer: str
    source_count: int
    citations_present: bool
    debug_trace: dict[str, Any] | None = None


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class AppConfig(BaseModel):
    api_url: str
    model: str
    skill_path: str
    local_kb_roots: list[str]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
