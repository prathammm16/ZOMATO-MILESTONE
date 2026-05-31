"""FastAPI backend for restaurant recommendations."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.api.orchestrator import get_recommendations
from src.data.loader import load_restaurant_store
from src.data.models import BudgetTier, RecommendationResponse, UserPreferences
from src.data.store import RestaurantStore
from src.filtering.locations import get_location_options

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Zomato AI Recommendation API",
    description="Backend API — filter + Groq LLM recommendations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendationRequest(BaseModel):
    location: str
    budget: Literal["low", "medium", "high"]
    cuisine: str | None = None
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    additional_preferences: str | None = None
    num_recommendations: int = Field(default=5, ge=1, le=10)


@lru_cache(maxsize=1)
def _get_store() -> RestaurantStore:
    return load_restaurant_store()


@app.on_event("startup")
def startup() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Loading restaurant store...")
    store = _get_store()
    logger.info("Backend ready: %s restaurants", store.count())


@app.get("/health")
def health() -> dict[str, str | int]:
    store = _get_store()
    return {"status": "ok", "restaurants": store.count()}


@app.get("/locations")
def locations() -> dict[str, list[str]]:
    store = _get_store()
    return get_location_options(store)


@app.post("/recommendations", response_model=RecommendationResponse)
def recommend(body: RecommendationRequest) -> RecommendationResponse:
    preferences = UserPreferences(
        location=body.location,
        budget=BudgetTier(body.budget),
        cuisine=body.cuisine,
        min_rating=body.min_rating,
        additional_preferences=body.additional_preferences,
        num_recommendations=body.num_recommendations,
    )
    try:
        return get_recommendations(preferences, _get_store())
    except Exception as exc:
        logger.exception("Recommendation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
