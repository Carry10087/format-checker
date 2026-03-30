from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.orchestrator import QueryOrchestrator
from app.schemas import AppConfig, HealthResponse, HistoryResponse, RunRequest, RunResponse
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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ready", timestamp=datetime.utcnow())


@app.post("/api/run", response_model=RunResponse)
def run_task(request: RunRequest) -> RunResponse:
    try:
        return orchestrator.run(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/history", response_model=HistoryResponse)
def list_history() -> HistoryResponse:
    return HistoryResponse(items=history_repo.list_items())


@app.get("/api/config", response_model=AppConfig)
def get_config() -> AppConfig:
    return config_repo.get()


@app.put("/api/config", response_model=AppConfig)
def save_config(config: AppConfig) -> AppConfig:
    return config_repo.save(config)
