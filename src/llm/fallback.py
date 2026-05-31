"""Fallback recommendations when the LLM fails."""

from __future__ import annotations

from config import settings
from src.data.models import Recommendation, Restaurant, UserPreferences


def _sort_key(restaurant: Restaurant) -> tuple[float, float]:
    cost = restaurant.cost if restaurant.cost is not None else float("inf")
    return (-restaurant.rating, cost)


def build_fallback_explanation(preferences: UserPreferences, restaurant: Restaurant) -> str:
    parts = [
        f"Matched your filters for {preferences.location}",
        f"{preferences.budget.value} budget",
    ]
    if preferences.cuisine:
        parts.append(f"{preferences.cuisine} cuisine")
    if preferences.min_rating > 0:
        parts.append(f"rating at least {preferences.min_rating}")
    area = restaurant.locality or restaurant.location
    return (
        f"{'; '.join(parts)}. "
        f"{restaurant.name} in {area} has a {restaurant.rating} rating."
    )


def build_fallback_recommendations(
    candidates: list[Restaurant],
    preferences: UserPreferences,
    *,
    top_k: int | None = None,
) -> list[Recommendation]:
    """Top filter-sorted restaurants with template explanations."""
    k = top_k if top_k is not None else settings.TOP_RECOMMENDATIONS
    sorted_candidates = sorted(candidates, key=_sort_key)[:k]
    return [
        Recommendation(
            rank=index,
            restaurant=restaurant,
            explanation=build_fallback_explanation(preferences, restaurant),
        )
        for index, restaurant in enumerate(sorted_candidates, start=1)
    ]
