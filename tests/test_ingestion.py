"""Phase 1 ingestion and store tests."""

from __future__ import annotations

import pytest

from src.data.ingestion import (
    assign_budget_tiers,
    normalize_rows,
    _parse_cost,
    _parse_cuisines,
    _parse_rating,
)
from src.data.models import BudgetTier, FilterCriteria
from src.data.store import RestaurantStore


class TestParsing:
    def test_parse_cost_with_currency(self) -> None:
        assert _parse_cost("₹1,500 for two people") == 1500.0

    def test_parse_rating_with_slash(self) -> None:
        assert _parse_rating("4.1/5") == 4.1

    def test_parse_rating_sentinel(self) -> None:
        assert _parse_rating("NEW") is None

    def test_parse_cuisines_comma_separated(self) -> None:
        assert _parse_cuisines("Italian, Chinese") == ["Italian", "Chinese"]


class TestNormalizeRows:
    def test_keeps_valid_rows(self) -> None:
        rows = [
            {
                "name": "Test Cafe",
                "address": "Main Road, Connaught Place, Delhi",
                "location": "Connaught Place",
                "cuisines": "Italian, Chinese",
                "approx_cost(for two people)": "500",
                "rate": "4.2/5",
            },
            {
                "restaurant_name": "No Rating Place",
                "address": "Other Road, Delhi",
                "rate": "NEW",
            },
        ]
        restaurants, stats = normalize_rows(iter(rows))
        assert len(restaurants) == 1
        assert stats.total_rows == 2
        assert stats.dropped_rows == 1
        assert stats.drop_reasons.get("missing_rating") == 1

    def test_budget_tiers_assigned(self) -> None:
        rows = [
            {"name": "A", "address": "Street, X", "rate": "4.0", "approx_cost": "100"},
            {"name": "B", "address": "Street, X", "rate": "4.0", "approx_cost": "500"},
            {"name": "C", "address": "Street, X", "rate": "4.0", "approx_cost": "1000"},
        ]
        restaurants, stats = normalize_rows(iter(rows))
        assert len(restaurants) == 3
        tiers = {r.budget_tier for r in restaurants}
        assert BudgetTier.LOW in tiers
        assert BudgetTier.MEDIUM in tiers
        assert BudgetTier.HIGH in tiers
        assert sum(stats.budget_tier_counts.values()) == 3

    def test_city_extracted_from_address(self) -> None:
        rows = [
            {
                "name": "Valid",
                "address": "21st Main Road, Banashankari, Bangalore",
                "location": "Banashankari",
                "cuisines": "South Indian",
                "approx_cost": "600",
                "rate": "4.5/5",
            }
        ]
        restaurants, _ = normalize_rows(iter(rows))
        r = restaurants[0]
        assert r.location == "Bangalore"
        assert r.locality == "Banashankari"

    def test_required_fields_populated(self) -> None:
        rows = [
            {
                "name": "Valid",
                "address": "Some Street, Bengaluru",
                "cuisines": "South Indian",
                "price": 600,
                "aggregate_rating": 4.5,
            }
        ]
        restaurants, _ = normalize_rows(iter(rows))
        r = restaurants[0]
        assert r.name == "Valid"
        assert r.location == "Bangalore"
        assert r.cuisines == ["South Indian"]
        assert r.rating == 4.5
        assert r.budget_tier in BudgetTier
        assert r.id.startswith("r_")


class TestAssignBudgetTiers:
    def test_all_none_cost_defaults_medium(self) -> None:
        tiers = assign_budget_tiers([None, None])
        assert tiers == [BudgetTier.MEDIUM, BudgetTier.MEDIUM]

    def test_identical_costs_all_medium(self) -> None:
        tiers = assign_budget_tiers([500.0, 500.0, 500.0])
        assert all(t == BudgetTier.MEDIUM for t in tiers)


class TestRestaurantStore:
    def test_get_all_count(self, sample_store: RestaurantStore) -> None:
        assert sample_store.count() == 5

    def test_get_by_ids(self, sample_store: RestaurantStore) -> None:
        found = sample_store.get_by_ids(["r_delhi_1", "missing"])
        assert len(found) == 1
        assert found[0].name == "Spice Kitchen"

    def test_query_location_delhi(self, sample_store: RestaurantStore) -> None:
        results = sample_store.query(FilterCriteria(location="Delhi"))
        assert len(results) == 2

    def test_query_location_case_insensitive(self, sample_store: RestaurantStore) -> None:
        results = sample_store.query(FilterCriteria(location="delhi"))
        assert len(results) == 2

    def test_query_budget_and_rating(self, sample_store: RestaurantStore) -> None:
        results = sample_store.query(
            FilterCriteria(location="Bangalore", budget_tier=BudgetTier.LOW, min_rating=4.0)
        )
        assert len(results) == 1
        assert results[0].name == "Dosa Corner"

    def test_query_cuisine_partial(self, sample_store: RestaurantStore) -> None:
        results = sample_store.query(FilterCriteria(cuisine="indian"))
        assert len(results) >= 3

    def test_distinct_locations(self, sample_store: RestaurantStore) -> None:
        locations = sample_store.get_distinct_locations()
        assert "Delhi" in locations
        assert "Bangalore" in locations


@pytest.mark.integration
def test_huggingface_load_produces_restaurants() -> None:
    """Requires network; loads a small slice via full ingest (slow)."""
    from src.data.ingestion import load_raw_dataset, normalize_rows

    rows = load_raw_dataset(max_rows=200)
    restaurants, stats = normalize_rows(iter(rows))
    assert stats.total_rows == 200
    assert stats.kept_rows > 0
    assert all(r.budget_tier in BudgetTier for r in restaurants)
    assert all(0.0 <= r.rating <= 5.0 for r in restaurants)

    store = RestaurantStore(restaurants)
    locations = store.get_distinct_locations()
    assert len(locations) > 0
