from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.orchestrator import QueryOrchestrator
from app.schemas import (
    AppConfig,
    HealthResponse,
    HistoryResponse,
    HistoryUpdateRequest,
    RunRequest,
    RunResponse,
    TranslateRequest,
    TranslateResponse,
)
from app.storage.config_repo import ConfigRepository
from app.storage.history import HistoryRepository


app = FastAPI(title="Codex Answer Desktop Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = QueryOrchestrator()
config_repo = ConfigRepository()
history_repo = HistoryRepository()


def localize_error(exc: Exception) -> str:
    detail = str(exc).strip()
    if not detail:
        return "发生未知错误，请稍后重试。"

    if "No usable sources were collected." in detail:
        return "没有找到可用资料。请把问题描述得更具体，或开启网络检索、本地知识库后再试。"

    if detail.startswith("Skill not found:"):
        skill_path = detail.split(":", 1)[1].strip()
        return f"未找到规则文件：{skill_path}。请检查 CODEX_SKILL_PATH 配置。"

    if detail.startswith("History item not found:"):
        return "没有找到对应的历史会话，可能已经被删除。"

    if any(token in detail for token in ("401 Client Error", "403 Client Error", "Unauthorized", "invalid_api_key")):
        return "模型接口鉴权失败，请检查 API Key 是否正确，或重新生成新的 Key。"

    if "404 Client Error" in detail and "/chat/completions" in detail:
        return "模型接口地址不正确，请检查 CODEX_AGENT_API_URL 是否填写正确。"

    if "429 Client Error" in detail:
        return "模型接口请求过于频繁，或者当前账户额度不足，请稍后再试。"

    if any(token in detail for token in ("500 Server Error", "502 Server Error", "503 Server Error", "504 Server Error")):
        return "模型接口暂时不可用，请稍后再试。"

    if any(
        token in detail
        for token in (
            "Connection refused",
            "Failed to establish a new connection",
            "Max retries exceeded",
            "timed out",
            "Read timed out",
            "ConnectTimeout",
            "Name or service not known",
            "Temporary failure in name resolution",
        )
    ):
        return "无法连接到模型接口，请检查网络和 CODEX_AGENT_API_URL。"

    return detail


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ready", timestamp=datetime.utcnow())


@app.post("/api/run", response_model=RunResponse)
def run_task(request: RunRequest) -> RunResponse:
    try:
        return orchestrator.run(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=localize_error(exc)) from exc


@app.post("/api/translate", response_model=TranslateResponse)
def translate_text(request: TranslateRequest) -> TranslateResponse:
    try:
        return orchestrator.translate_text(
            request.text,
            request.run_id,
            model=request.model,
            reasoning_effort=request.reasoning_effort,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=localize_error(exc)) from exc


@app.get("/api/history", response_model=HistoryResponse)
def list_history() -> HistoryResponse:
    return HistoryResponse(items=history_repo.list_items())


@app.put("/api/history/{run_id}")
def update_history(run_id: str, request: HistoryUpdateRequest):
    try:
        return history_repo.update(run_id, request.model_dump(exclude_unset=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=localize_error(ValueError(f"History item not found: {run_id}"))) from exc


@app.delete("/api/history/{run_id}", response_model=HistoryResponse)
def delete_history(run_id: str) -> HistoryResponse:
    try:
        history_repo.delete(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=localize_error(ValueError(f"History item not found: {run_id}"))) from exc
    return HistoryResponse(items=history_repo.list_items())


@app.get("/api/config", response_model=AppConfig)
def get_config() -> AppConfig:
    return config_repo.get()


@app.put("/api/config", response_model=AppConfig)
def save_config(config: AppConfig) -> AppConfig:
    return config_repo.save(config)
