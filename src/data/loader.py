"""Startup loader for the restaurant store."""

from __future__ import annotations

import logging

from src.data.ingestion import ingest
from src.data.models import IngestionStats
from src.data.store import RestaurantStore

logger = logging.getLogger(__name__)

_store: RestaurantStore | None = None
_last_stats: IngestionStats | None = None


def load_restaurant_store(
    *,
    use_cache: bool = True,
    force_refresh: bool | None = None,
) -> RestaurantStore:
    """
    Load dataset and build the in-memory store (call once at app init).

    Raises RuntimeError if ingestion yields zero restaurants.
    """
    global _store, _last_stats

    restaurants, stats = ingest(use_cache=use_cache, force_refresh=force_refresh)
    if not restaurants:
        raise RuntimeError("Restaurant store is empty after ingestion.")

    _store = RestaurantStore(restaurants)
    _last_stats = stats
    logger.info(
        "Restaurant store ready: %s restaurants, %s locations (source=%s)",
        _store.count(),
        stats.unique_locations,
        stats.source,
    )
    return _store


def get_restaurant_store() -> RestaurantStore:
    """Return the cached store or load it on first access."""
    global _store
    if _store is None:
        return load_restaurant_store()
    return _store


def get_last_ingestion_stats() -> IngestionStats | None:
    return _last_stats
