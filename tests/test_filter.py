"""Phase 2 preference validation and candidate filter tests."""

from __future__ import annotations

import pytest

from config import settings
from src.data.models import BudgetTier, UserPreferences
from src.filtering.candidate_filter import filter_candidates
from src.filtering.locations import get_cuisine_options, get_location_options, resolve_location
from src.filtering.validation import validate_preferences


class TestValidation:
    def test_rejects_empty_location(self) -> None:
        prefs = UserPreferences(location="   ", budget=BudgetTier.LOW)
        ok, errors = validate_preferences(prefs)
        assert not ok
        assert any("Location" in e for e in errors)

    def test_clamps_min_rating_to_valid_range(self) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW, min_rating=6.0)
        assert prefs.min_rating == 5.0

    def test_accepts_valid_preferences(self, sample_store) -> None:
        opts = get_location_options(sample_store)
        known = opts["cities"] + opts["localities"]
        prefs = UserPreferences(
            location="Delhi",
            budget=BudgetTier.MEDIUM,
            cuisine="Indian",
            min_rating=4.0,
        )
        ok, errors = validate_preferences(prefs, known_locations=known)
        assert ok
        assert errors == []

    def test_rejects_unknown_location(self, sample_store) -> None:
        opts = get_location_options(sample_store)
        known = opts["cities"] + opts["localities"]
        prefs = UserPreferences(location="Atlantis", budget=BudgetTier.LOW)
        ok, errors = validate_preferences(prefs, known_locations=known)
        assert not ok


class TestLocations:
    def test_resolve_bengaluru_alias(self, sample_store) -> None:
        cities = sample_store.get_distinct_locations()
        assert resolve_location("bengaluru", cities) == "Bangalore"

    def test_resolve_locality(self, sample_store) -> None:
        opts = get_location_options(sample_store)
        known = opts["cities"] + opts["localities"]
        assert resolve_location("Connaught Place", known) == "Connaught Place"

    def test_distinct_cuisines_from_store(self, sample_store) -> None:
        cuisines = get_cuisine_options(sample_store)
        assert cuisines == sorted(
            ["Chinese", "Italian", "Mughlai", "North Indian", "Seafood", "South Indian"],
            key=str.casefold,
        )


class TestCandidateFilter:
    def test_location_and_budget(self, sample_store) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        result = filter_candidates(prefs, sample_store)
        assert len(result.candidates) == 1
        assert result.candidates[0].name == "Spice Kitchen"
        assert result.candidates[0].budget_tier == BudgetTier.LOW

    def test_cuisine_narrows_results(self, sample_store) -> None:
        prefs = UserPreferences(
            location="Bangalore",
            budget=BudgetTier.MEDIUM,
            cuisine="Mughlai",
        )
        result = filter_candidates(prefs, sample_store)
        assert len(result.candidates) == 1
        assert result.candidates[0].name == "Biryani House"

    def test_min_rating_excludes_lower(self, sample_store) -> None:
        prefs = UserPreferences(
            location="Bangalore",
            budget=BudgetTier.LOW,
            min_rating=4.1,
        )
        result = filter_candidates(prefs, sample_store)
        assert result.candidates == []
        assert result.message is not None

    def test_impossible_combo_empty(self, sample_store) -> None:
        prefs = UserPreferences(
            location="Delhi",
            budget=BudgetTier.LOW,
            cuisine="Italian",
            min_rating=5.0,
        )
        result = filter_candidates(prefs, sample_store)
        assert result.candidates == []
        assert result.total_matches == 0

    def test_caps_at_max_candidates(self, sample_store) -> None:
        base = next(
            r
            for r in sample_store.get_all()
            if r.location == "Bangalore" and r.budget_tier == BudgetTier.LOW
        )
        many = [
            base.model_copy(update={"id": f"extra_{i}", "name": f"R{i}", "rating": 3.0 + i * 0.01})
            for i in range(30)
        ]
        from src.data.store import RestaurantStore

        big_store = RestaurantStore(sample_store.get_all() + many)
        prefs = UserPreferences(location="Bangalore", budget=BudgetTier.LOW)
        cap = 5
        result = filter_candidates(prefs, big_store, max_candidates=cap)
        assert len(result.candidates) == cap
        assert result.truncated is True

    def test_sorted_by_rating_desc(self, sample_store) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.HIGH)
        result = filter_candidates(prefs, sample_store)
        assert len(result.candidates) == 1
        assert result.candidates[0].rating == 4.8

    def test_never_exceeds_settings_cap(self, sample_store) -> None:
        prefs = UserPreferences(location="Bangalore", budget=BudgetTier.LOW)
        result = filter_candidates(prefs, sample_store, max_candidates=settings.MAX_CANDIDATES_TO_LLM)
        assert len(result.candidates) <= settings.MAX_CANDIDATES_TO_LLM

    def test_validation_error_skips_filter(self, sample_store) -> None:
        prefs = UserPreferences(location="", budget=BudgetTier.LOW)
        result = filter_candidates(prefs, sample_store)
        assert result.candidates == []
        assert "Location" in (result.message or "")
