"""In-memory restaurant store with indexes for fast filtering."""

from __future__ import annotations

from collections import defaultdict

from src.data.constants import CITY_ALIASES
from src.data.models import BudgetTier, FilterCriteria, Restaurant


def _normalize_key(value: str) -> str:
    return value.strip().casefold()


def _cuisine_tokens(cuisines: list[str]) -> set[str]:
    return {_normalize_key(c) for c in cuisines}


class RestaurantStore:
    """Queryable in-memory store built at startup."""

    def __init__(self, restaurants: list[Restaurant]) -> None:
        self._by_id: dict[str, Restaurant] = {r.id: r for r in restaurants}
        self._all: list[Restaurant] = list(restaurants)
        self._by_location: dict[str, list[Restaurant]] = defaultdict(list)
        self._by_budget: dict[BudgetTier, list[Restaurant]] = defaultdict(list)
        self._by_cuisine: dict[str, list[Restaurant]] = defaultdict(list)
        self._localities: dict[str, str] = {}

        for restaurant in restaurants:
            loc_key = _normalize_key(restaurant.location)
            self._by_location[loc_key].append(restaurant)
            if restaurant.locality:
                loc_key = _normalize_key(restaurant.locality)
                self._by_location[loc_key].append(restaurant)
                if loc_key not in self._localities:
                    self._localities[loc_key] = restaurant.locality
            self._by_budget[restaurant.budget_tier].append(restaurant)
            for token in _cuisine_tokens(restaurant.cuisines):
                self._by_cuisine[token].append(restaurant)

    def get_all(self) -> list[Restaurant]:
        return list(self._all)

    def get_by_ids(self, ids: list[str]) -> list[Restaurant]:
        return [self._by_id[i] for i in ids if i in self._by_id]

    def get_distinct_locations(self) -> list[str]:
        seen: dict[str, str] = {}
        for restaurant in self._all:
            key = _normalize_key(restaurant.location)
            if key not in seen:
                seen[key] = restaurant.location
        return sorted(seen.values(), key=str.casefold)

    def get_distinct_localities(self) -> list[str]:
        return sorted(self._localities.values(), key=str.casefold)

    def get_distinct_cuisines(self) -> list[str]:
        """Unique cuisine labels from the dataset (for UI dropdowns)."""
        seen: dict[str, str] = {}
        for restaurant in self._all:
            for cuisine in restaurant.cuisines:
                label = cuisine.strip()
                if not label:
                    continue
                key = _normalize_key(label)
                if key not in seen:
                    seen[key] = label
        return sorted(seen.values(), key=str.casefold)

    def count(self) -> int:
        return len(self._all)

    def query(self, criteria: FilterCriteria) -> list[Restaurant]:
        """Apply filters; intersection of location, budget, cuisine, min_rating."""
        candidates: list[Restaurant] | None = None

        if criteria.location:
            loc_key = _normalize_key(criteria.location)
            # Also match canonical city aliases (e.g. bengaluru -> indexed under bangalore)
            candidates = list(self._by_location.get(loc_key, []))
            if not candidates:
                canonical = CITY_ALIASES.get(loc_key)
                if canonical:
                    candidates = list(self._by_location.get(_normalize_key(canonical), []))

        if criteria.budget_tier is not None:
            tier_list = list(self._by_budget.get(criteria.budget_tier, []))
            if candidates is None:
                candidates = tier_list
            else:
                tier_ids = {r.id for r in tier_list}
                candidates = [r for r in candidates if r.id in tier_ids]

        if criteria.cuisine:
            cuisine_key = _normalize_key(criteria.cuisine)
            cuisine_matches = [
                r
                for r in self._all
                if any(cuisine_key in token or token in cuisine_key for token in _cuisine_tokens(r.cuisines))
            ]
            if candidates is None:
                candidates = cuisine_matches
            else:
                match_ids = {r.id for r in cuisine_matches}
                candidates = [r for r in candidates if r.id in match_ids]

        if candidates is None:
            candidates = list(self._all)

        if criteria.min_rating > 0.0:
            candidates = [r for r in candidates if r.rating >= criteria.min_rating]

        return candidates
