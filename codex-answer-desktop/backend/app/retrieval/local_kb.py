from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import settings
from app.schemas import SourceDocument


TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml"}


class LocalKnowledgeRetriever:
    def retrieve(self, query: str) -> list[SourceDocument]:
        tokens = self._tokenize(query)
        candidates: list[tuple[float, SourceDocument]] = []

        for root in settings.local_kb_roots:
            root_path = Path(root)
            if not root_path.exists():
                continue

            for path in root_path.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                content = self._read_text(path)
                if not content:
                    continue

                score, excerpt = self._score_content(content, tokens)
                if score <= 0:
                    continue

                candidates.append(
                    (
                        score,
                        SourceDocument(
                            title=path.name,
                            content=excerpt,
                            source_type="local_kb",
                            url_or_path=str(path),
                            timestamp=None,
                            confidence=min(0.95, 0.3 + score / 10),
                        ),
                    )
                )

        candidates.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in candidates[: settings.local_result_limit]]

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[A-Za-z0-9_]+", text) if len(token) > 1]

    def _read_text(self, path: Path) -> str:
        try:
            if path.suffix.lower() == ".json":
                return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False)
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _score_content(self, content: str, tokens: list[str]) -> tuple[float, str]:
        lowered = content.lower()
        hits = sum(lowered.count(token) for token in tokens)
        if hits == 0:
            return 0, ""

        excerpt = content[:2200]
        return float(hits), excerpt
