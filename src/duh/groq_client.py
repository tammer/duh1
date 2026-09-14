from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class ChatClient(Protocol):
    def chat_json(self, system: str, user: str) -> Any:
        """Return parsed JSON from a chat completion."""


def get_groq_api_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return key or None


def get_groq_model() -> str:
    return os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL


def parse_json_content(content: str) -> Any:
    """Parse JSON from a model reply, tolerating optional markdown fences."""
    text = content.strip()
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


class GroqClient:
    """Thin Groq chat wrapper that returns parsed JSON."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> None:
        key = api_key if api_key is not None else get_groq_api_key()
        if not key:
            raise ValueError("GROQ_API_KEY is required for the groq backend")
        self.model = model or get_groq_model()
        self.temperature = temperature
        from groq import Groq

        self._client = Groq(api_key=key)

    def chat_json(self, system: str, user: str) -> Any:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "[]"
        return parse_json_content(content)
