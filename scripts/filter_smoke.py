"""
Phase 2 CLI smoke test — filter candidates without LLM.

Usage (from project root):
  python scripts/filter_smoke.py
  python scripts/filter_smoke.py --location Bangalore --budget medium --cuisine Italian
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.loader import load_restaurant_store
from src.data.models import BudgetTier, UserPreferences
from src.filtering import filter_candidates, get_location_options

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 filter smoke test")
    parser.add_argument("--location", default="")
    parser.add_argument("--budget", choices=["low", "medium", "high"], default="")
    parser.add_argument("--cuisine", default="")
    parser.add_argument("--min-rating", type=float, default=None)
    args = parser.parse_args()

    print("Loading restaurant store...")
    store = load_restaurant_store()
    opts = get_location_options(store)
    print(f"Cities available: {', '.join(opts['cities'][:5])} ... ({len(opts['cities'])} total)")

    location = args.location or _prompt("Location (city or locality)", "Bangalore")
    budget_str = args.budget or _prompt("Budget (low/medium/high)", "medium")
    cuisine = args.cuisine or _prompt("Cuisine (optional)", "")
    min_rating_str = (
        str(args.min_rating)
        if args.min_rating is not None
        else _prompt("Minimum rating 0-5 (optional)", "0")
    )

    try:
        min_rating = float(min_rating_str) if min_rating_str else 0.0
    except ValueError:
        print("Invalid rating; using 0.")
        min_rating = 0.0

    preferences = UserPreferences(
        location=location,
        budget=BudgetTier(budget_str),
        cuisine=cuisine or None,
        min_rating=min_rating,
    )

    result = filter_candidates(preferences, store)
    print(f"\nTotal matches: {result.total_matches}")
    print(f"Returned: {len(result.candidates)} (truncated={result.truncated})")
    if result.message:
        print(f"Message: {result.message}")

    print("\nTop 3 candidates:")
    for restaurant in result.candidates[:3]:
        cuisines = ", ".join(restaurant.cuisines) or "N/A"
        area = restaurant.locality or restaurant.location
        print(f"  - {restaurant.name} ({area}) | {cuisines} | rating={restaurant.rating}")


if __name__ == "__main__":
    main()
