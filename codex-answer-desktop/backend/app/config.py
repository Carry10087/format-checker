from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / ".data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def resolve_default_skill_path() -> Path:
    candidates = [
        BASE_DIR.parent / "answer-format-rules" / "SKILL.md",
        Path.home() / ".codex" / "skills" / "strict-answer-formatter" / "SKILL.md",
        Path(r"C:\Users\EDY\.codex\skills\strict-answer-formatter\SKILL.md"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


DEFAULT_SKILL_PATH = resolve_default_skill_path()
DEFAULT_LOCAL_KB_ROOTS = [str(BASE_DIR / "docs")]
if DEFAULT_SKILL_PATH.parent.exists():
    DEFAULT_LOCAL_KB_ROOTS.insert(0, str(DEFAULT_SKILL_PATH.parent))


class Settings:
    api_url: str = os.getenv("CODEX_AGENT_API_URL", "http://127.0.0.1:9000/v1/chat/completions")
    api_key: str = os.getenv("CODEX_AGENT_API_KEY", "")
    model: str = os.getenv("CODEX_AGENT_MODEL", "gpt-5.2")
    reasoning_effort: str = os.getenv("CODEX_AGENT_REASONING_EFFORT", "medium")
    skill_path: Path = Path(os.getenv("CODEX_SKILL_PATH", str(DEFAULT_SKILL_PATH)))
    local_kb_roots: list[str] = [
        root for root in os.getenv("CODEX_LOCAL_KB_ROOTS", ";".join(DEFAULT_LOCAL_KB_ROOTS)).split(";") if root
    ]
    history_file: Path = DATA_DIR / "history.json"
    config_file: Path = DATA_DIR / "config.json"
    web_result_limit: int = int(os.getenv("CODEX_WEB_RESULT_LIMIT", "4"))
    local_result_limit: int = int(os.getenv("CODEX_LOCAL_RESULT_LIMIT", "4"))


settings = Settings()
