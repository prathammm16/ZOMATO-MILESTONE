"""Core data models for the restaurant recommendation pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BudgetTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Restaurant(BaseModel):
    """Normalized restaurant record stored in memory."""

    id: str
    name: str
    location: str  # City for filtering (e.g. Bangalore)
    locality: str | None = None  # Neighborhood from dataset `location` column
    cuisines: list[str] = Field(default_factory=list)
    cost: float | None = None
    budget_tier: BudgetTier
    rating: float = Field(ge=0.0, le=5.0)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}


class UserPreferences(BaseModel):
    """User-supplied dining preferences (Phase 2)."""

    location: str
    budget: BudgetTier
    cuisine: str | None = None
    min_rating: float = 0.0
    additional_preferences: str | None = None
    num_recommendations: int = Field(default=5, ge=1, le=10)

    @field_validator("location")
    @classmethod
    def strip_location(cls, value: str) -> str:
        return value.strip()

    @field_validator("cuisine")
    @classmethod
    def strip_cuisine(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("min_rating")
    @classmethod
    def clamp_min_rating(cls, value: float) -> float:
        return max(0.0, min(5.0, value))

    @field_validator("additional_preferences")
    @classmethod
    def trim_additional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return stripped[:500]


class FilterCriteria(BaseModel):
    """Structured filters for querying the restaurant store."""

    location: str | None = None
    budget_tier: BudgetTier | None = None
    cuisine: str | None = None
    min_rating: float = 0.0

    @field_validator("min_rating")
    @classmethod
    def clamp_min_rating(cls, value: float) -> float:
        return max(0.0, min(5.0, value))

    @classmethod
    def from_preferences(cls, preferences: UserPreferences) -> FilterCriteria:
        return cls(
            location=preferences.location,
            budget_tier=preferences.budget,
            cuisine=preferences.cuisine,
            min_rating=preferences.min_rating,
        )


class FilterResult(BaseModel):
    """Output of the candidate filter (no LLM)."""

    candidates: list[Restaurant] = Field(default_factory=list)
    message: str | None = None
    total_matches: int = 0
    truncated: bool = False
    filters_applied: dict[str, str | float | None] = Field(default_factory=dict)


class Recommendation(BaseModel):
    """A ranked restaurant recommendation with LLM explanation (Phase 3)."""

    rank: int = Field(ge=1)
    restaurant: Restaurant
    explanation: str


class LLMRecommendationResult(BaseModel):
    """Parsed output from the recommendation engine."""

    recommendations: list[Recommendation] = Field(default_factory=list)
    summary: str | None = None
    fallback_used: bool = False
    parse_success: bool = True


class RecommendationMetadata(BaseModel):
    """Pipeline metadata returned with final recommendations (Phase 4)."""

    candidate_count: int = 0
    total_matches: int = 0
    truncated: bool = False
    filters_applied: dict[str, str | float | None] = Field(default_factory=dict)
    llm_used: bool = False
    fallback_used: bool = False
    groq_latency_ms: float | None = None


class RecommendationResponse(BaseModel):
    """End-to-end orchestrator response (Phase 4)."""

    recommendations: list[Recommendation] = Field(default_factory=list)
    summary: str | None = None
    message: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    metadata: RecommendationMetadata = Field(default_factory=RecommendationMetadata)


class IngestionStats(BaseModel):
    """Summary of a dataset load and normalization run."""

    total_rows: int
    kept_rows: int
    dropped_rows: int
    drop_reasons: dict[str, int] = Field(default_factory=dict)
    budget_tier_counts: dict[str, int] = Field(default_factory=dict)
    unique_locations: int = 0
    source: str = "huggingface"
