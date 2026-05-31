"""Location helpers for preference input and UI dropdowns."""

from __future__ import annotations

from src.data.constants import CITY_ALIASES
from src.data.store import RestaurantStore


def _normalize(value: str) -> str:
    return value.strip().casefold()


def resolve_location(user_input: str, known_locations: list[str] | None = None) -> str | None:
    """
    Resolve user location to a canonical city or locality name.

    Matches alias (bengaluru -> Bangalore), exact city, or neighborhood in *known_locations*.
    Returns None when *known_locations* is set and no match is found.
    """
    text = user_input.strip()
    if not text:
        return None

    key = _normalize(text)
    alias = CITY_ALIASES.get(key)
    canonical = alias or text

    if known_locations:
        by_key = {_normalize(loc): loc for loc in known_locations}
        if key in by_key:
            return by_key[key]
        if _normalize(canonical) in by_key:
            return by_key[_normalize(canonical)]
        return None

    return canonical


def get_location_options(store: RestaurantStore) -> dict[str, list[str]]:
    """
    Lists for UI dropdowns.

    Returns:
        cities: distinct city names
        localities: distinct neighborhood names (sample of store)
    """
    return {
        "cities": store.get_distinct_locations(),
        "localities": store.get_distinct_localities(),
    }


def get_cuisine_options(store: RestaurantStore) -> list[str]:
    """Distinct cuisine names from the loaded dataset (cache / HF)."""
    return store.get_distinct_cuisines()
