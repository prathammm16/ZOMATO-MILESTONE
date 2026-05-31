"""Phase 3 LLM parser and fallback tests."""

from __future__ import annotations

import json

import pytest

from src.data.models import BudgetTier, UserPreferences
from src.llm.client import MockLLMClient
from src.llm.fallback import build_fallback_recommendations
from src.llm.parser import (
    extract_json_object,
    merge_recommendations,
    parse_llm_response,
)
from src.llm.parser import ParsedLLMResponse, ParsedRecommendationItem
from src.llm.recommend import generate_recommendations


SAMPLE_JSON = json.dumps(
    {
        "recommendations": [
            {
                "rank": 1,
                "restaurant_id": "r_delhi_2",
                "explanation": "Great Italian options in Delhi within your budget.",
            },
            {
                "rank": 2,
                "restaurant_id": "r_delhi_1",
                "explanation": "Solid North Indian choice for your location.",
            },
            {
                "rank": 99,
                "restaurant_id": "fake_id",
                "explanation": "Should be dropped.",
            },
        ],
        "summary": "Two strong Delhi picks.",
    }
)


class TestExtractJson:
    def test_parses_plain_json(self) -> None:
        data = extract_json_object(SAMPLE_JSON)
        assert data is not None
        assert len(data["recommendations"]) == 3

    def test_parses_markdown_fenced_json(self) -> None:
        fenced = f"```json\n{SAMPLE_JSON}\n```"
        data = extract_json_object(fenced)
        assert data is not None

    def test_malformed_returns_none(self) -> None:
        assert extract_json_object("not json at all") is None


class TestParseLlmResponse:
    def test_valid_response(self) -> None:
        parsed = parse_llm_response(SAMPLE_JSON)
        assert parsed is not None
        assert len(parsed.recommendations) == 3
        assert parsed.summary == "Two strong Delhi picks."

    def test_empty_list(self) -> None:
        parsed = parse_llm_response('{"recommendations": []}')
        assert parsed is not None
        assert parsed.recommendations == []


class TestMergeRecommendations:
    def test_drops_invalid_ids(self, sample_restaurants) -> None:
        parsed = parse_llm_response(SAMPLE_JSON)
        assert parsed is not None
        merged = merge_recommendations(parsed, sample_restaurants, top_k=5)
        ids = {r.restaurant.id for r in merged}
        assert "fake_id" not in ids
        assert len(merged) == 2

    def test_renumbers_and_sorts_by_rank(self, sample_restaurants) -> None:
        parsed = ParsedLLMResponse(
            recommendations=[
                ParsedRecommendationItem(rank=2, restaurant_id="r_delhi_1", explanation="B"),
                ParsedRecommendationItem(rank=1, restaurant_id="r_delhi_2", explanation="A"),
            ]
        )
        merged = merge_recommendations(parsed, sample_restaurants)
        assert merged[0].restaurant.id == "r_delhi_2"
        assert merged[1].restaurant.id == "r_delhi_1"

    def test_empty_explanation_gets_template(self, sample_restaurants) -> None:
        parsed = ParsedLLMResponse(
            recommendations=[
                ParsedRecommendationItem(rank=1, restaurant_id="r_delhi_1", explanation="  "),
            ]
        )
        merged = merge_recommendations(parsed, sample_restaurants)
        assert merged[0].explanation


class TestFallback:
    def test_fallback_returns_top_five(self, sample_restaurants) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        results = build_fallback_recommendations(sample_restaurants, prefs, top_k=5)
        assert len(results) == 5
        assert results[0].rank == 1
        assert all(r.explanation for r in results)

    def test_fallback_delhi_low_one_match(self, sample_store, sample_restaurants) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        from src.filtering import filter_candidates

        filtered = filter_candidates(prefs, sample_store)
        results = build_fallback_recommendations(filtered.candidates, prefs)
        assert len(results) == 1
        assert results[0].restaurant.name == "Spice Kitchen"


class TestGenerateRecommendations:
    def test_mock_client_success(self, sample_restaurants) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.MEDIUM)
        client = MockLLMClient(response=SAMPLE_JSON)
        result = generate_recommendations(
            prefs,
            [r for r in sample_restaurants if r.location == "Delhi"],
            client=client,
        )
        assert not result.fallback_used
        assert len(result.recommendations) >= 1
        assert result.recommendations[0].explanation

    def test_parse_failure_uses_fallback(self, sample_restaurants) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        client = MockLLMClient(response="Sorry, I cannot help.")
        delhi = [r for r in sample_restaurants if r.location == "Delhi"]
        result = generate_recommendations(prefs, delhi, client=client)
        assert result.fallback_used
        assert len(result.recommendations) >= 1

    def test_empty_candidates(self) -> None:
        prefs = UserPreferences(location="Delhi", budget=BudgetTier.LOW)
        result = generate_recommendations(prefs, [], client=MockLLMClient())
        assert result.recommendations == []
        assert not result.fallback_used

    def test_default_mock_builds_from_candidates(self, sample_restaurants) -> None:
        prefs = UserPreferences(location="Bangalore", budget=BudgetTier.MEDIUM)
        candidates = [r for r in sample_restaurants if r.location == "Bangalore"]
        result = generate_recommendations(prefs, candidates, client=MockLLMClient())
        assert not result.fallback_used
        assert all(r.restaurant.id in {c.id for c in candidates} for r in result.recommendations)
