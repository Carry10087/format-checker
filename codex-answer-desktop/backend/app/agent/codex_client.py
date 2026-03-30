from __future__ import annotations

import requests

from app.config import settings
from app.schemas import TokenUsage


class CodexClient:
    def generate(
        self,
        prompt: str,
        model: str | None = None,
        reasoning_effort: str | None = None,
        api_url: str | None = None,
    ) -> tuple[str, TokenUsage, str, str]:
        resolved_model = model or settings.model
        resolved_reasoning_effort = reasoning_effort or settings.reasoning_effort
        resolved_api_url = api_url or settings.api_url
        headers = {
            "Content-Type": "application/json",
        }
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"

        payload = {
            "model": resolved_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.2,
        }
        if resolved_reasoning_effort:
            payload["reasoning"] = {"effort": resolved_reasoning_effort}

        response = requests.post(resolved_api_url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )
        return data["choices"][0]["message"]["content"], token_usage, resolved_model, resolved_reasoning_effort
