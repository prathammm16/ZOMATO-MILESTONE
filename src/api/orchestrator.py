"""
Application orchestrator — single entry point for recommendations (Phase 4).

Flow: validate → filter → Groq LLM → parse → RecommendationResponse
"""

from __future__ import annotations

import logging
import time

from src.data.models import (
    RecommendationMetadata,
    RecommendationResponse,
    UserPreferences,
)
from src.data.store import RestaurantStore
from src.filtering.candidate_filter import filter_candidates
from src.filtering.locations import get_location_options
from src.filtering.validation import validate_preferences
from src.llm.client import GroqLLMClient, LLMClient
from src.llm.recommend import generate_recommendations

logger = logging.getLogger(__name__)


def get_recommendations(
    preferences: UserPreferences,
    store: RestaurantStore,
    *,
    client: LLMClient | None = None,
) -> RecommendationResponse:
    """
    Run the full recommendation pipeline.

    - Invalid preferences → validation_errors, no filter/LLM call
    - Empty filter → message, llm_used=False
    - Success → Groq-ranked recommendations (or fallback if Groq/parse fails)
    """
    location_opts = get_location_options(store)
    known = location_opts["cities"] + location_opts["localities"]
    ok, errors = validate_preferences(preferences, known_locations=known)
    if not ok:
        logger.info("Validation failed: %s", errors)
        return RecommendationResponse(
            message="; ".join(errors),
            validation_errors=errors,
            metadata=RecommendationMetadata(
                filters_applied=_preference_filters(preferences),
            ),
        )

    filter_result = filter_candidates(preferences, store)
    metadata = RecommendationMetadata(
        candidate_count=len(filter_result.candidates),
        total_matches=filter_result.total_matches,
        truncated=filter_result.truncated,
        filters_applied=filter_result.filters_applied,
    )

    if not filter_result.candidates:
        logger.info("No candidates after filter: %s", filter_result.message)
        return RecommendationResponse(
            message=filter_result.message,
            metadata=metadata,
        )

    groq_client = client if client is not None else GroqLLMClient()
    start = time.perf_counter()
    llm_result = generate_recommendations(
        preferences,
        filter_result.candidates,
        store=store,
        client=groq_client,
        top_k=preferences.num_recommendations,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    metadata.llm_used = True
    metadata.fallback_used = llm_result.fallback_used
    metadata.groq_latency_ms = round(latency_ms, 2)

    logger.info(
        "Pipeline complete: candidates=%s recommendations=%s fallback=%s groq_ms=%s",
        metadata.candidate_count,
        len(llm_result.recommendations),
        metadata.fallback_used,
        metadata.groq_latency_ms,
    )

    return RecommendationResponse(
        recommendations=llm_result.recommendations,
        summary=llm_result.summary,
        metadata=metadata,
    )


def _preference_filters(preferences: UserPreferences) -> dict[str, str | float | None]:
    return {
        "location": preferences.location,
        "budget": preferences.budget.value,
        "cuisine": preferences.cuisine,
        "min_rating": preferences.min_rating,
        "additional_preferences": preferences.additional_preferences,
        "num_recommendations": preferences.num_recommendations,
    }
