"""
Phase 6 — error matrix and success-criteria tests (architecture §9).

Uses MockLLMClient only; no network required.
"""

from __future__ import annotations

import json

import pytest

from src.api.orchestrator import get_recommendations
from src.data.models import BudgetTier, UserPreferences
from src.filtering.candidate_filter import filter_candidates
from src.llm.client import MockLLMClient
from src.llm.parser import merge_recommendations, parse_llm_response
from src.llm.parser import ParsedLLMResponse, ParsedRecommendationItem


class TestErrorMatrixInvalidInput:
    """Architecture §9: Invalid user input → validation message, no side effects."""

    def test_empty_location_rejected(self, sample_store) -> None:
        client = MockLLMClient()
        prefs = UserPreferences(location="   ", budget=BudgetTier.LOW)
        response = get_recommendations(prefs, sample_store, client=client)
        assert response.validation_errors
        assert response.recommendations == []
        assert response.metadata.llm_used is False
        assert client.calls == []

    def test_unknown_location_rejected(self, sample_store) -> None:
        client = MockLLMClient()
        prefs = UserPreferences(location="Atlantis", budget=BudgetTier.LOW)
        response = get_recommendations(prefs, sample_store, client=client)
        assert response.validation_errors or response.message
        assert client.calls == []


class TestErrorMatrixZeroMatches:
    """Architecture §9: Zero filter matches → empty state, no LLM."""

    def test_strict_filters_skip_groq(self, sample_store) -> None:
        client = MockLLMClient()
        prefs = UserPreferences(
            location="Delhi",
            budget=BudgetTier.LOW,
            cuisine="French",
            min_rating=5.0,
        )
        response = get_recommendations(prefs, sample_store, client=client)
        assert response.recommendations == []
        assert response.metadata.llm_used is False
        assert client.calls == []


class TestErrorMatrixMalformedJson:
    """Architecture §9: Malformed LLM JSON → fallback ranking."""

    def test_bad_json_triggers_fallback(self, sample_store) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        client = MockLLMClient(response="Here are my picks: definitely not JSON")
        response = get_recommendations(prefs, sample_store, client=client)
        assert response.metadata.fallback_used is True
        assert len(response.recommendations) >= 1


class TestErrorMatrixHallucinatedIds:
    """Architecture §9: Hallucinated restaurant_id → dropped."""

    def test_invalid_ids_stripped(self, sample_restaurants) -> None:
        parsed = ParsedLLMResponse(
            recommendations=[
                ParsedRecommendationItem(
                    rank=1,
                    restaurant_id="hallucinated_999",
                    explanation="Fake place.",
                ),
                ParsedRecommendationItem(
                    rank=2,
                    restaurant_id="r_delhi_1",
                    explanation="Real place.",
                ),
            ]
        )
        merged = merge_recommendations(parsed, sample_restaurants)
        assert len(merged) == 1
        assert merged[0].restaurant.id == "r_delhi_1"


class TestSuccessCriteriaGrounded:
    """Context: recommendations grounded in dataset rows."""

    def test_all_recommendation_ids_in_candidates(self, sample_store) -> None:
        prefs = UserPreferences(location="Bangalore", budget=BudgetTier.LOW)
        filtered = filter_candidates(prefs, sample_store)
        candidate_ids = {c.id for c in filtered.candidates}
        payload = json.dumps(
            {
                "recommendations": [
                    {
                        "rank": 1,
                        "restaurant_id": filtered.candidates[0].id,
                        "explanation": "Matches Bangalore and low budget.",
                    }
                ],
                "summary": "Grounded pick.",
            }
        )
        response = get_recommendations(
            prefs, sample_store, client=MockLLMClient(response=payload)
        )
        for rec in response.recommendations:
            assert rec.restaurant.id in candidate_ids

    def test_parse_rejects_garbage(self) -> None:
        assert parse_llm_response("not json") is None


class TestFilterBeforeGenerate:
    """Context: filter runs before LLM; candidate count tracked."""

    def test_metadata_candidate_count(self, sample_store) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        response = get_recommendations(
            prefs, sample_store, client=MockLLMClient(response="{}")
        )
        assert response.metadata.candidate_count >= 1
        assert response.metadata.llm_used is True
