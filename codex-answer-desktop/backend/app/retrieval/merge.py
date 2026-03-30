from __future__ import annotations

import hashlib

from app.schemas import SourceDocument


def merge_sources(*source_lists: list[SourceDocument]) -> list[SourceDocument]:
    merged: list[SourceDocument] = []
    seen: set[str] = set()

    for source_list in source_lists:
        for source in source_list:
            fingerprint = _fingerprint(source)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            merged.append(source)

    merged.sort(key=lambda item: item.confidence, reverse=True)
    return merged


def _fingerprint(source: SourceDocument) -> str:
    raw = f"{source.title}|{source.url_or_path}|{source.content[:300]}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()
