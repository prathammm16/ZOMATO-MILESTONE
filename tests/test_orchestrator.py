"""Phase 4 orchestrator tests."""

from __future__ import annotations

import json

import pytest

from src.api.orchestrator import get_recommendations
from src.data.models import BudgetTier, UserPreferences
from src.llm.client import MockLLMClient

SAMPLE_JSON = json.dumps(
    {
        "recommendations": [
            {
                "rank": 1,
                "restaurant_id": "r_delhi_1",
                "explanation": "Fits your Delhi and budget preferences.",
            }
        ],
        "summary": "Best match in Delhi.",
    }
)


class TestGetRecommendations:
    def test_validation_error_no_llm(self, sample_store) -> None:
        prefs = UserPreferences(location="", budget=BudgetTier.LOW)
        response = get_recommendations(prefs, sample_store, client=MockLLMClient())
        assert response.validation_errors
        assert response.recommendations == []
        assert response.metadata.llm_used is False

    def test_empty_filter_no_llm(self, sample_store) -> None:
        prefs = UserPreferences(
            location="Delhi",
            budget=BudgetTier.LOW,
            cuisine="Italian",
            min_rating=5.0,
        )
        client = MockLLMClient()
        response = get_recommendations(prefs, sample_store, client=client)
        assert response.recommendations == []
        assert response.message is not None
        assert response.metadata.llm_used is False
        assert client.calls == []

    def test_success_with_mock_groq(self, sample_store) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        client = MockLLMClient(response=SAMPLE_JSON)
        response = get_recommendations(prefs, sample_store, client=client)
        assert len(response.recommendations) >= 1
        assert response.metadata.llm_used is True
        assert response.metadata.fallback_used is False
        assert response.metadata.candidate_count >= 1
        assert client.calls

    def test_fallback_metadata(self, sample_store) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        client = MockLLMClient(response="not valid json")
        response = get_recommendations(prefs, sample_store, client=client)
        assert response.recommendations
        assert response.metadata.llm_used is True
        assert response.metadata.fallback_used is True

    def test_metadata_filters_applied(self, sample_store) -> None:
        prefs = UserPreferences(
            location="Bangalore",
            budget=BudgetTier.MEDIUM,
            cuisine="North Indian",
        )
        response = get_recommendations(
            prefs, sample_store, client=MockLLMClient(response=SAMPLE_JSON)
        )
        assert response.metadata.filters_applied.get("location") == "Bangalore"
        assert response.metadata.filters_applied.get("budget") == "medium"

    def test_groq_latency_recorded(self, sample_store) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        response = get_recommendations(
            prefs, sample_store, client=MockLLMClient(response=SAMPLE_JSON)
        )
        assert response.metadata.groq_latency_ms is not None
        assert response.metadata.groq_latency_ms >= 0
