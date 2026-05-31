"""Deterministic candidate filter — no LLM (Phase 2)."""

from __future__ import annotations

import logging

from config import settings
from src.data.models import FilterCriteria, FilterResult, Restaurant, UserPreferences
from src.data.store import RestaurantStore
from src.filtering.locations import get_location_options, resolve_location
from src.filtering.validation import validate_preferences

logger = logging.getLogger(__name__)


def _sort_key(restaurant: Restaurant) -> tuple[float, float]:
    cost = restaurant.cost if restaurant.cost is not None else float("inf")
    return (-restaurant.rating, cost)


def _dedupe(restaurants: list[Restaurant]) -> list[Restaurant]:
    seen: set[str] = set()
    unique: list[Restaurant] = []
    for restaurant in restaurants:
        if restaurant.id in seen:
            continue
        seen.add(restaurant.id)
        unique.append(restaurant)
    return unique


def _searchable_text(restaurant: Restaurant) -> str:
    parts = [
        restaurant.name,
        " ".join(restaurant.cuisines),
        restaurant.locality or "",
    ]
    metadata = restaurant.raw_metadata
    for key in ("dish_liked", "rest_type", "reviews_list", "address"):
        value = metadata.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts).casefold()


def _apply_additional_keywords(
    candidates: list[Restaurant],
    additional_preferences: str | None,
) -> list[Restaurant]:
    """Keyword filter on metadata when text is available (architecture §4.4 step 5)."""
    if not additional_preferences:
        return candidates

    keywords = [
        word.strip().casefold()
        for word in additional_preferences.split()
        if len(word.strip()) >= 3
    ]
    if not keywords:
        return candidates

    filtered: list[Restaurant] = []
    for restaurant in candidates:
        haystack = _searchable_text(restaurant)
        if any(keyword in haystack for keyword in keywords):
            filtered.append(restaurant)

    # If keywords eliminate everyone, keep pre-keyword set (EC-F10)
    if not filtered and candidates:
        logger.info(
            "Additional preference keywords matched no rows; keeping %s candidates for LLM context.",
            len(candidates),
        )
        return candidates

    return filtered


def _empty_message(preferences: UserPreferences, total_before_cap: int) -> str:
    hints = [
        "Try a different cuisine or leave cuisine blank.",
        "Lower the minimum rating.",
        "Change your budget tier (low, medium, high).",
    ]
    if total_before_cap == 0:
        return (
            f"No restaurants match your filters in {preferences.location}. "
            + " ".join(hints)
        )
    return (
        f"Found {total_before_cap} matches but none could be prepared for recommendations. "
        + " ".join(hints)
    )


def filter_candidates(
    preferences: UserPreferences,
    store: RestaurantStore,
    *,
    max_candidates: int | None = None,
    strict_location: bool = False,
) -> FilterResult:
    """
    Filter, sort, and cap restaurant candidates.

    Pipeline: validate → location resolve → store query → keyword filter → sort → cap.
    """
    location_opts = get_location_options(store)
    known = location_opts["cities"] + location_opts["localities"]
    ok, errors = validate_preferences(preferences, known_locations=known)
    if not ok:
        return FilterResult(
            candidates=[],
            message="; ".join(errors),
            filters_applied=_filters_applied_dict(preferences),
        )

    resolved_location = resolve_location(preferences.location, known)
    if strict_location and resolved_location is None:
        return FilterResult(
            candidates=[],
            message=(
                f"Location '{preferences.location}' was not found. "
                f"Available cities include: {', '.join(location_opts['cities'][:10])}"
            ),
            filters_applied=_filters_applied_dict(preferences),
        )

    prefs_for_query = preferences.model_copy(
        update={"location": resolved_location or preferences.location}
    )
    criteria = FilterCriteria.from_preferences(prefs_for_query)
    matches = _dedupe(store.query(criteria))
    matches = _apply_additional_keywords(matches, preferences.additional_preferences)

    total_matches = len(matches)
    matches.sort(key=_sort_key)

    cap = max_candidates if max_candidates is not None else settings.MAX_CANDIDATES_TO_LLM
    truncated = total_matches > cap
    candidates = matches[:cap]

    message = None
    if not candidates:
        message = _empty_message(preferences, total_matches)

    logger.info(
        "Filter: location=%s budget=%s total=%s returned=%s truncated=%s",
        preferences.location,
        preferences.budget.value,
        total_matches,
        len(candidates),
        truncated,
    )

    return FilterResult(
        candidates=candidates,
        message=message,
        total_matches=total_matches,
        truncated=truncated,
        filters_applied=_filters_applied_dict(preferences, resolved=resolved_location),
    )


def _filters_applied_dict(
    preferences: UserPreferences,
    *,
    resolved: str | None = None,
) -> dict[str, str | float | None]:
    return {
        "location": preferences.location,
        "resolved_location": resolved,
        "budget": preferences.budget.value,
        "cuisine": preferences.cuisine,
        "min_rating": preferences.min_rating,
        "additional_preferences": preferences.additional_preferences,
    }
