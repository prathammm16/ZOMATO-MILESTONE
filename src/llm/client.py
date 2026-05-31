"""LLM provider adapter."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    model: str = settings.GROQ_MODEL
    temperature: float = settings.GROQ_TEMPERATURE
    timeout_seconds: int = settings.GROQ_TIMEOUT_SECONDS
    api_key: str | None = settings.GROQ_API_KEY


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str, config: LLMConfig) -> str: ...


class GroqLLMClient:
    """Groq chat completions adapter (default for Phase 4)."""

    def complete(self, system_prompt: str, user_prompt: str, config: LLMConfig) -> str:
        api_key = config.api_key or settings.GROQ_API_KEY
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to Streamlit Secrets, .env, "
                "or pass config.api_key."
            )

        from groq import Groq

        client = Groq(api_key=api_key, timeout=config.timeout_seconds)
        response = client.chat.completions.create(
            model=config.model,
            temperature=config.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned empty content.")
        return content.strip()


class MockLLMClient:
    """Deterministic client for tests without API calls."""

    def __init__(self, response: str | None = None) -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str, config: LLMConfig) -> str:
        self.calls.append((system_prompt, user_prompt))
        if self._response is not None:
            return self._response
        return _default_mock_json(user_prompt)


def _default_mock_json(user_prompt: str) -> str:
    """Build minimal valid JSON from candidate ids embedded in the user prompt."""
    import re

    ids = re.findall(r'"id":\s*"([^"]+)"', user_prompt)
    if not ids:
        ids = ["r_mock_1"]
    items = []
    for rank, rid in enumerate(ids[:5], start=1):
        items.append(
            {
                "rank": rank,
                "restaurant_id": rid,
                "explanation": f"Matches your stated preferences (rank {rank}).",
            }
        )
    import json

    return json.dumps({"recommendations": items, "summary": "Top picks from your filters."})
