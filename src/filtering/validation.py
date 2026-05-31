"""Validate user preferences before filtering."""

from __future__ import annotations

from src.data.models import UserPreferences

MAX_ADDITIONAL_LEN = 500


def validate_preferences(
    preferences: UserPreferences,
    *,
    known_locations: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """
    Validate preferences.

    Returns (ok, errors). Warnings about unknown locations are not blocking.
    """
    errors: list[str] = []

    if not preferences.location.strip():
        errors.append("Location is required.")

    if preferences.min_rating < 0.0 or preferences.min_rating > 5.0:
        errors.append("Minimum rating must be between 0 and 5.")

    if preferences.additional_preferences and len(preferences.additional_preferences) > MAX_ADDITIONAL_LEN:
        errors.append(
            f"Additional preferences must be at most {MAX_ADDITIONAL_LEN} characters."
        )

    if preferences.num_recommendations < 1 or preferences.num_recommendations > 10:
        errors.append("Number of recommendations must be between 1 and 10.")

    if known_locations is not None and preferences.location.strip():
        from src.filtering.locations import resolve_location

        if resolve_location(preferences.location, known_locations) is None:
            sample = known_locations[:10]
            errors.append(
                f"Location '{preferences.location}' was not found. "
                f"Examples: {', '.join(sample)}"
                + ("..." if len(known_locations) > 10 else "")
            )

    return (len(errors) == 0, errors)
