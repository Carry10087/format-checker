from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.agent.codex_client import CodexClient
from app.agent.skill_loader import load_skill_bundle
from app.config import settings
from app.retrieval.local_kb import LocalKnowledgeRetriever
from app.retrieval.merge import merge_sources
from app.retrieval.web import WebRetriever
from app.schemas import HistoryItem, RunRequest, RunResponse, SourceDocument
from app.storage.history import HistoryRepository


class QueryOrchestrator:
    def __init__(self) -> None:
        self.codex = CodexClient()
        self.web_retriever = WebRetriever()
        self.local_retriever = LocalKnowledgeRetriever()
        self.history_repo = HistoryRepository()

    def run(self, request: RunRequest) -> RunResponse:
        run_id = uuid.uuid4().hex[:12]
        query_type = self._classify_query(request.query)

        web_sources = self.web_retriever.retrieve(request.query) if request.web_enabled else []
        local_sources = self.local_retriever.retrieve(request.query) if request.local_kb_enabled else []
        sources = merge_sources(web_sources, local_sources)

        if not sources:
            raise ValueError("No usable sources were collected. Enable more retrieval sources or add local knowledge.")

        skill_bundle = load_skill_bundle(settings.skill_path)
        prompt = self._build_prompt(request.query, query_type, sources, skill_bundle)
        final_answer = self.codex.generate(prompt)
        citations_present = bool(re.search(r"\[Note \d+\]\(#\)", final_answer))

        debug_trace = None
        if request.debug:
            debug_trace = {
                "query_type": query_type,
                "web_sources": [source.model_dump() for source in web_sources],
                "local_sources": [source.model_dump() for source in local_sources],
                "merged_sources": [source.model_dump() for source in sources],
                "skill_path": str(settings.skill_path),
            }

        response = RunResponse(
            run_id=run_id,
            status="completed",
            final_answer=final_answer,
            citations_present=citations_present,
            source_count=len(sources),
            debug_trace=debug_trace,
        )
        self.history_repo.append(
            HistoryItem(
                run_id=run_id,
                query=request.query,
                created_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                final_answer=final_answer,
                source_count=len(sources),
                citations_present=citations_present,
                debug_trace=debug_trace,
            )
        )
        return response

    def _classify_query(self, query: str) -> str:
        normalized = query.strip().lower()
        if len(normalized.split()) <= 2:
            return "entity"
        if any(keyword in normalized for keyword in ("how", "why", "what", "when", "which")):
            return "question"
        return "mixed"

    def _build_prompt(self, query: str, query_type: str, sources: list[SourceDocument], skill_bundle: str) -> str:
        notes_block = "\n\n".join(
            f'Note{i}\n\n```txt\nTitle: {source.title}\nSource Type: {source.source_type}\nSource: {source.url_or_path}\nContent: {source.content}\n```'
            for i, source in enumerate(sources, start=1)
        )

        return f"""You are Codex running as a local answer agent inside a desktop app.

Your task:
1. understand the user query
2. use the provided sources as the factual basis
3. produce a final answer only
4. strictly follow the supplied formatter skill and references
5. preserve or create [Note X](#) citations that map to the source blocks

Query Type: {query_type}
User Query: {query}

{skill_bundle}

## Retrieved Sources

{notes_block}

Return the final user-facing answer only. Do not include your analysis, heading map, or any source-framing language.
"""
