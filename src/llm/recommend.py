"""Orchestrate LLM recommendation generation (Phase 3)."""

from __future__ import annotations

import logging

from src.data.models import LLMRecommendationResult, Restaurant, UserPreferences
from src.data.store import RestaurantStore
from src.llm.client import GroqLLMClient, LLMClient, LLMConfig
from src.llm.fallback import build_fallback_recommendations
from src.llm.parser import merge_recommendations, parse_llm_response
from src.llm.prompts import build_json_retry_prompt, build_recommendation_prompt

logger = logging.getLogger(__name__)


def generate_recommendations(
    preferences: UserPreferences,
    candidates: list[Restaurant],
    store: RestaurantStore | None = None,
    *,
    client: LLMClient | None = None,
    config: LLMConfig | None = None,
    top_k: int | None = None,
) -> LLMRecommendationResult:
    """
    Rank and explain candidates using the LLM.

    On timeout, API error, or parse failure: returns fallback recommendations.
    """
    if not candidates:
        return LLMRecommendationResult(
            recommendations=[],
            summary=None,
            fallback_used=False,
            parse_success=True,
        )

    k = top_k if top_k is not None else preferences.num_recommendations
    llm_client = client or GroqLLMClient()
    llm_config = config or LLMConfig()

    system_prompt, user_prompt = build_recommendation_prompt(
        preferences, candidates, top_k=k
    )

    try:
        raw = llm_client.complete(system_prompt, user_prompt, llm_config)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return _fallback_result(preferences, candidates, k)

    parsed = parse_llm_response(raw)
    if parsed is None:
        try:
            retry_system, retry_user = build_json_retry_prompt(raw)
            raw = llm_client.complete(retry_system, retry_user, llm_config)
            parsed = parse_llm_response(raw)
        except Exception as exc:
            logger.error("LLM JSON retry failed: %s", exc)
            return _fallback_result(preferences, candidates, k)

    if parsed is None:
        logger.warning("LLM response could not be parsed; using fallback.")
        return _fallback_result(preferences, candidates, k)

    recommendations = merge_recommendations(
        parsed, candidates, store=store, top_k=k
    )
    if not recommendations:
        logger.warning("No valid recommendations after merge; using fallback.")
        return _fallback_result(preferences, candidates, k)

    return LLMRecommendationResult(
        recommendations=recommendations,
        summary=parsed.summary,
        fallback_used=False,
        parse_success=True,
    )


def _fallback_result(
    preferences: UserPreferences,
    candidates: list[Restaurant],
    top_k: int,
) -> LLMRecommendationResult:
    return LLMRecommendationResult(
        recommendations=build_fallback_recommendations(
            candidates, preferences, top_k=top_k
        ),
        summary=None,
        fallback_used=True,
        parse_success=False,
    )
