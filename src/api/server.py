"""FastAPI backend for restaurant recommendations."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from src.api.orchestrator import get_recommendations
from src.data.loader import load_restaurant_store
from src.data.models import BudgetTier, RecommendationResponse, UserPreferences
from src.data.store import RestaurantStore
from src.filtering.locations import get_location_options

logger = logging.getLogger(__name__)

_store: RestaurantStore | None = None
_store_error: str | None = None
_store_lock = threading.Lock()


def _load_store_worker() -> None:
    global _store, _store_error
    try:
        logger.info(
            "Loading restaurant store... (HF_MAX_ROWS=%s)",
            settings.HF_MAX_ROWS if settings.HF_MAX_ROWS is not None else "all",
        )
        loaded = load_restaurant_store()
        with _store_lock:
            _store = loaded
            _store_error = None
        logger.info("Backend ready: %s restaurants", loaded.count())
    except Exception as exc:
        logger.exception("Failed to load restaurant store")
        with _store_lock:
            _store = None
            _store_error = str(exc)


def _require_store() -> RestaurantStore:
    with _store_lock:
        if _store_error:
            raise HTTPException(
                status_code=503,
                detail=f"Restaurant dataset failed to load: {_store_error}",
            )
        if _store is None:
            raise HTTPException(
                status_code=503,
                detail="Restaurant dataset is still loading. Try again shortly.",
            )
        return _store


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    logging.basicConfig(level=logging.INFO)
    thread = threading.Thread(target=_load_store_worker, daemon=True)
    thread.start()
    yield


app = FastAPI(
    title="Zomato AI Recommendation API",
    description="Backend API — filter + Groq LLM recommendations",
    version="1.0.0",
    lifespan=lifespan,
)

_allow_all_origins = settings.CORS_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=not _allow_all_origins,
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


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Zomato AI Recommendation API",
        "health": "/health",
        "locations": "/locations",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str | int]:
    with _store_lock:
        if _store_error:
            return {"status": "error", "restaurants": 0, "detail": _store_error}
        if _store is None:
            return {"status": "loading", "restaurants": 0}
        return {"status": "ok", "restaurants": _store.count()}


@app.get("/locations")
def locations() -> dict[str, list[str]]:
    store = _require_store()
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
        return get_recommendations(preferences, _require_store())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Recommendation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
