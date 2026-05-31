"""
Load and normalize the Zomato dataset from Hugging Face.

Dataset: ManikaSaini/zomato-restaurant-recommendation (single zomato.csv, ~51k rows)

Column mapping (task 1.1 — actual HF rows may use any alias below):
  name     -> name, restaurant_name, Restaurant Name
  location -> location, city, listed_in(city), address, Listed In(City)
  cuisine  -> cuisines, cuisine, Cuisine
  cost     -> approx_cost(for two people), approx_cost, price, price_range, Average Cost
  rating   -> rate, rating, aggregate_rating, Aggregate rating
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
from datasets import load_dataset

from config import settings
from src.data.constants import CITY_ALIASES
from src.data.models import BudgetTier, IngestionStats, Restaurant

logger = logging.getLogger(__name__)

NAME_KEYS = ("name", "restaurant_name", "Restaurant Name", "restaurant name")
LOCATION_KEYS = (
    "location",
    "city",
    "listed_in(city)",
    "Listed In(City)",
    "address",
    "Address",
)
CUISINE_KEYS = ("cuisines", "cuisine", "Cuisines", "Cuisine")
COST_KEYS = (
    "approx_cost(for two people)",
    "approx_cost",
    "price",
    "price_range",
    "Average Cost",
    "average_cost",
    "cost",
)
RATING_KEYS = ("rate", "rating", "aggregate_rating", "Aggregate rating", "Rating")

RATING_SENTINELS = frozenset({"NEW", "N/A", "-", "NULL", ""})

def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            value = row[key]
            if isinstance(value, str) and not value.strip():
                continue
            return value
    return None


def _parse_cost(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text.replace(",", ""))
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def _parse_rating(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        rating = float(value)
        return rating if 0.0 <= rating <= 5.0 else None
    text = str(value).strip()
    if not text or text.upper() in RATING_SENTINELS:
        return None
    if "/" in text:
        text = text.split("/", 1)[0].strip()
    try:
        rating = float(text)
    except ValueError:
        return None
    if rating < 0.0:
        return 0.0
    if rating > 5.0:
        return 5.0
    return rating


def _parse_cuisines(value: Any) -> list[str]:
    if value is None:
        return []
    tokens: list[str] = []
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value).split(",")
    for part in parts:
        token = str(part).strip()
        if token:
            tokens.append(token)
    return list(dict.fromkeys(tokens))


def _normalize_location(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_city(name: str) -> str:
    key = name.strip().casefold()
    return CITY_ALIASES.get(key, name.strip())


def _city_from_address(address: Any) -> str | None:
    if address is None:
        return None
    parts = [p.strip() for p in str(address).split(",") if p.strip()]
    if not parts:
        return None
    return _normalize_city(parts[-1])


def _resolve_city_and_locality(row: dict[str, Any]) -> tuple[str | None, str | None]:
    """
    Prefer city parsed from address; fall back to location / listed_in(city) columns.

    HF schema: `location` is usually locality (Banashankari); city is in `address`.
    """
    address = _first_present(row, ("address", "Address"))
    city = _city_from_address(address)
    locality = _normalize_location(_first_present(row, ("location",)))
    listed_city = _normalize_location(_first_present(row, ("listed_in(city)", "Listed In(City)")))

    if not locality and listed_city:
        locality = listed_city

    if not city and listed_city:
        candidate = _normalize_city(listed_city)
        if candidate.casefold() in CITY_ALIASES or listed_city.casefold() in CITY_ALIASES:
            city = candidate
        else:
            locality = locality or listed_city

    if not city and locality:
        candidate = _normalize_city(locality)
        if locality.casefold() in CITY_ALIASES:
            city = candidate

    return city, locality


def _restaurant_id(name: str, location: str, row_index: int) -> str:
    payload = f"{name}|{location}|{row_index}".lower()
    digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
    return f"r_{digest}"


def assign_budget_tiers(costs: list[float | None]) -> list[BudgetTier]:
    """Assign low/medium/high from global 33rd and 66th percentiles (architecture §5.2)."""
    numeric = sorted(c for c in costs if c is not None)
    n = len(numeric)
    if n == 0:
        return [BudgetTier.MEDIUM] * len(costs)
    if len(set(numeric)) == 1:
        return [BudgetTier.MEDIUM] * len(costs)
    p33 = numeric[int(0.33 * (n - 1))]
    p66 = numeric[int(0.66 * (n - 1))]

    tiers: list[BudgetTier] = []
    for cost in costs:
        if cost is None:
            tiers.append(BudgetTier.MEDIUM)
        elif cost <= p33:
            tiers.append(BudgetTier.LOW)
        elif cost <= p66:
            tiers.append(BudgetTier.MEDIUM)
        else:
            tiers.append(BudgetTier.HIGH)
    return tiers


def normalize_rows(
    rows: Iterator[dict[str, Any]],
) -> tuple[list[Restaurant], IngestionStats]:
    """Map raw HF rows to Restaurant models; drop invalid rows."""
    total = 0
    kept: list[Restaurant] = []
    drop_reasons: dict[str, int] = {}

    def drop(reason: str) -> None:
        drop_reasons[reason] = drop_reasons.get(reason, 0) + 1

    parsed: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        total += 1
        name_raw = _first_present(row, NAME_KEYS)
        name = str(name_raw).strip() if name_raw is not None else ""
        city, locality = _resolve_city_and_locality(row)

        if not name:
            drop("missing_name")
            continue
        if not city:
            drop("missing_location")
            continue

        rating = _parse_rating(_first_present(row, RATING_KEYS))
        if rating is None:
            drop("missing_rating")
            continue

        cost = _parse_cost(_first_present(row, COST_KEYS))
        cuisines = _parse_cuisines(_first_present(row, CUISINE_KEYS))

        metadata = {
            k: v
            for k, v in row.items()
            if k
            not in set(NAME_KEYS + LOCATION_KEYS + CUISINE_KEYS + COST_KEYS + RATING_KEYS)
            and v is not None
        }
        if locality:
            metadata["locality"] = locality

        parsed.append(
            {
                "id": _restaurant_id(name, city, row_index),
                "name": name,
                "location": city,
                "locality": locality,
                "cuisines": cuisines,
                "cost": cost,
                "rating": rating,
                "raw_metadata": metadata,
            }
        )

    tiers = assign_budget_tiers([p["cost"] for p in parsed])
    tier_counts: dict[str, int] = {t.value: 0 for t in BudgetTier}

    for item, tier in zip(parsed, tiers, strict=True):
        tier_counts[tier.value] += 1
        kept.append(
            Restaurant(
                id=item["id"],
                name=item["name"],
                location=item["location"],
                locality=item.get("locality"),
                cuisines=item["cuisines"],
                cost=item["cost"],
                budget_tier=tier,
                rating=item["rating"],
                raw_metadata=item["raw_metadata"],
            )
        )

    locations = {r.location for r in kept}
    stats = IngestionStats(
        total_rows=total,
        kept_rows=len(kept),
        dropped_rows=total - len(kept),
        drop_reasons=drop_reasons,
        budget_tier_counts=tier_counts,
        unique_locations=len(locations),
    )
    logger.info(
        "Ingestion complete: total=%s kept=%s dropped=%s tiers=%s locations=%s",
        stats.total_rows,
        stats.kept_rows,
        stats.dropped_rows,
        stats.budget_tier_counts,
        stats.unique_locations,
    )
    return kept, stats


def _configure_hf_hub() -> None:
    token = settings.HF_TOKEN
    if not token:
        return
    os.environ.setdefault("HF_TOKEN", token)
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)


def iter_raw_dataset(
    dataset_id: str | None = None,
    *,
    max_rows: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream rows from Hugging Face without loading the full split into memory."""
    _configure_hf_hub()
    ds_id = dataset_id or settings.HF_DATASET_ID
    row_limit = max_rows if max_rows is not None else settings.HF_MAX_ROWS
    logger.info(
        "Streaming dataset from Hugging Face: %s (max_rows=%s)",
        ds_id,
        row_limit if row_limit is not None else "all",
    )
    stream = load_dataset(ds_id, split="train", streaming=True)
    if row_limit is not None:
        stream = stream.take(row_limit)
    for row in stream:
        yield dict(row)


def load_raw_dataset(
    dataset_id: str | None = None,
    *,
    max_rows: int | None = None,
) -> list[dict[str, Any]]:
    """Load rows from Hugging Face (train split) into a list — prefer iter_raw_dataset."""
    return list(iter_raw_dataset(dataset_id, max_rows=max_rows))


def load_from_huggingface(dataset_id: str | None = None) -> tuple[list[Restaurant], IngestionStats]:
    rows = iter_raw_dataset(dataset_id, max_rows=settings.HF_MAX_ROWS)
    return normalize_rows(rows)


def save_cache(restaurants: list[Restaurant], path: Path | None = None) -> Path:
    """Persist normalized restaurants to Parquet."""
    cache_path = path or settings.DATA_CACHE_PATH
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    records = [r.model_dump(mode="json") for r in restaurants]
    frame = pd.DataFrame(records)
    frame.to_parquet(cache_path, index=False)
    logger.info("Wrote cache to %s (%s rows)", cache_path, len(restaurants))
    return cache_path


def load_from_cache(path: Path | None = None) -> list[Restaurant] | None:
    """Load restaurants from Parquet cache if present."""
    cache_path = path or settings.DATA_CACHE_PATH
    if not cache_path.exists():
        return None
    frame = pd.read_parquet(cache_path)
    restaurants: list[Restaurant] = []
    for data in frame.to_dict(orient="records"):
        if isinstance(data.get("raw_metadata"), str):
            try:
                data["raw_metadata"] = json.loads(data["raw_metadata"])
            except json.JSONDecodeError:
                data["raw_metadata"] = {}
        if isinstance(data.get("cuisines"), str):
            data["cuisines"] = _parse_cuisines(data["cuisines"])
        data["budget_tier"] = BudgetTier(data["budget_tier"])
        restaurants.append(Restaurant(**data))
    logger.info("Loaded %s restaurants from cache %s", len(restaurants), cache_path)
    return restaurants


def ingest(
    *,
    use_cache: bool = True,
    force_refresh: bool | None = None,
) -> tuple[list[Restaurant], IngestionStats]:
    """
    Load restaurants from cache or Hugging Face.

    Returns (restaurants, stats). Stats are partial when served from cache.
    """
    refresh = settings.FORCE_REFRESH if force_refresh is None else force_refresh

    if use_cache and not refresh:
        cached = load_from_cache()
        if cached:
            stats = IngestionStats(
                total_rows=len(cached),
                kept_rows=len(cached),
                dropped_rows=0,
                unique_locations=len({r.location for r in cached}),
                source="cache",
            )
            return cached, stats

    restaurants, stats = load_from_huggingface()
    if not restaurants:
        raise RuntimeError(
            "No valid restaurants after ingestion. Check dataset schema or network."
        )
    save_cache(restaurants)
    return restaurants, stats
