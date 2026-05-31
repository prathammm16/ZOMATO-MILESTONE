"""Parse and validate LLM JSON responses."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from src.data.models import Recommendation, Restaurant
from src.data.store import RestaurantStore

logger = logging.getLogger(__name__)


class ParsedRecommendationItem(BaseModel):
    rank: int = Field(ge=1)
    restaurant_id: str
    explanation: str = ""


class ParsedLLMResponse(BaseModel):
    recommendations: list[ParsedRecommendationItem] = Field(default_factory=list)
    summary: str | None = None


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object or array from LLM text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return {"recommendations": data}
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    match = re.search(r"\[[\s\S]*\]", cleaned)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return {"recommendations": data}
        except json.JSONDecodeError:
            pass

    return None


def parse_llm_response(raw: str) -> ParsedLLMResponse | None:
    """Parse raw LLM text into a validated structure."""
    data = extract_json_object(raw)
    if data is None:
        logger.warning("Could not extract JSON from LLM response.")
        return None

    items = data.get("recommendations", data.get("items", []))
    if not isinstance(items, list):
        return None

    try:
        return ParsedLLMResponse(
            recommendations=[ParsedRecommendationItem(**item) for item in items],
            summary=data.get("summary"),
        )
    except (ValidationError, TypeError) as exc:
        logger.warning("LLM JSON schema validation failed: %s", exc)
        return None


def merge_recommendations(
    parsed: ParsedLLMResponse,
    candidates: list[Restaurant],
    store: RestaurantStore | None = None,
    *,
    top_k: int = 5,
) -> list[Recommendation]:
    """
    Merge parsed LLM output with restaurant records.

    Drops hallucinated IDs and empty explanations (uses template).
    """
    by_id = {r.id: r for r in candidates}
    if store:
        for rid in {item.restaurant_id for item in parsed.recommendations}:
            if rid not in by_id:
                extra = store.get_by_ids([rid])
                if extra:
                    by_id[rid] = extra[0]

    valid_ids = set(by_id.keys())
    merged: list[Recommendation] = []

    for item in sorted(parsed.recommendations, key=lambda x: x.rank):
        if item.restaurant_id not in valid_ids:
            logger.warning("Dropping hallucinated restaurant_id: %s", item.restaurant_id)
            continue
        explanation = item.explanation.strip()
        if not explanation:
            explanation = "Matches your filters and preferences."
        merged.append(
            Recommendation(
                rank=item.rank,
                restaurant=by_id[item.restaurant_id],
                explanation=explanation,
            )
        )

    merged.sort(key=lambda r: r.rank)
    return merged[:top_k]
