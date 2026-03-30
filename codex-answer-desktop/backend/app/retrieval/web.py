from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.schemas import SourceDocument


class WebRetriever:
    SEARCH_URL = "https://html.duckduckgo.com/html/"

    def retrieve(self, query: str) -> list[SourceDocument]:
        params = {"q": query}
        response = requests.post(
            self.SEARCH_URL,
            data=urlencode(params),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        anchors = soup.select("a.result__a")[: settings.web_result_limit]
        for idx, anchor in enumerate(anchors, start=1):
            title = anchor.get_text(" ", strip=True)
            url = anchor.get("href", "")
            content = self._fetch_page_excerpt(url)
            if not content:
                continue
            results.append(
                SourceDocument(
                    title=title,
                    content=content,
                    source_type="web",
                    url_or_path=url,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    confidence=max(0.2, 1.0 - idx * 0.12),
                )
            )

        return results

    def _fetch_page_excerpt(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = " ".join(soup.stripped_strings)
            text = re.sub(r"\s+", " ", text)
            return text[:1800]
        except Exception:
            return ""
