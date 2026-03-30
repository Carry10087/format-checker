from __future__ import annotations

import requests

from app.config import settings


class CodexClient:
    def generate(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"

        payload = {
            "model": settings.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.2,
        }

        response = requests.post(settings.api_url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
