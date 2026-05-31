"""
Phase 1 sample script — load store and print 5 restaurants.

Usage (from project root):
  python scripts/sample_phase1.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.loader import get_last_ingestion_stats, load_restaurant_store
from src.data.models import FilterCriteria

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    store = load_restaurant_store()
    stats = get_last_ingestion_stats()
    print(f"\nStore: {store.count()} restaurants")
    if stats:
        print(
            f"Ingestion: total={stats.total_rows} kept={stats.kept_rows} "
            f"dropped={stats.dropped_rows} source={stats.source}"
        )
        print(f"Budget tiers: {stats.budget_tier_counts}")
        print(f"Unique locations: {stats.unique_locations}")

    print("\n--- Sample restaurants (up to 5) ---")
    for restaurant in store.get_all()[:5]:
        cuisines = ", ".join(restaurant.cuisines) or "N/A"
        cost = f"{restaurant.cost:.0f}" if restaurant.cost is not None else "N/A"
        area = restaurant.locality or restaurant.location
        print(
            f"\n{restaurant.name} ({area}, {restaurant.location})\n"
            f"  Cuisine: {cuisines}\n"
            f"  Rating: {restaurant.rating} | Cost: {cost} | Budget: {restaurant.budget_tier.value}"
        )

    delhi = store.query(FilterCriteria(location="Delhi"))
    bangalore = store.query(FilterCriteria(location="Bangalore"))
    print(f"\nDelhi matches: {len(delhi)} | Bangalore matches: {len(bangalore)}")


if __name__ == "__main__":
    main()
