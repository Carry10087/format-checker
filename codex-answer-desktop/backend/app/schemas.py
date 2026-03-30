from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


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
    model: str | None = None
    reasoning_effort: str | None = None


class RunResponse(BaseModel):
    run_id: str
    status: str
    final_answer: str
    citations_present: bool
    source_count: int
    model: str
    reasoning_effort: str = "medium"
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    translated_answer: str = ""
    translated_token_usage: TokenUsage | None = None
    debug_trace: dict[str, Any] | None = None


class HistoryItem(BaseModel):
    run_id: str
    query: str
    created_at: str
    final_answer: str
    source_count: int
    citations_present: bool
    model: str = ""
    reasoning_effort: str = "medium"
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    translated_answer: str = ""
    translated_token_usage: TokenUsage | None = None
    web_enabled: bool = True
    local_kb_enabled: bool = True
    debug: bool = False
    debug_trace: dict[str, Any] | None = None


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class HistoryUpdateRequest(BaseModel):
    query: str | None = None
    final_answer: str | None = None
    translated_answer: str | None = None
    translated_token_usage: TokenUsage | None = None
    citations_present: bool | None = None
    source_count: int | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    token_usage: TokenUsage | None = None
    web_enabled: bool | None = None
    local_kb_enabled: bool | None = None
    debug: bool | None = None
    debug_trace: dict[str, Any] | None = None


class TranslateRequest(BaseModel):
    text: str
    run_id: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None


class TranslateResponse(BaseModel):
    translated_text: str
    model: str
    reasoning_effort: str = "medium"
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class AppConfig(BaseModel):
    api_url: str
    model: str
    reasoning_effort: str = "medium"
    skill_path: str
    local_kb_roots: list[str]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
