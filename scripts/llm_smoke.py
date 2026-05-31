"""
Phase 3 smoke test — filter candidates then call LLM (or mock).

Usage:
  python scripts/llm_smoke.py --mock
  python scripts/llm_smoke.py --location Bangalore --budget medium   # requires GROQ_API_KEY
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
from src.filtering import filter_candidates
from src.llm.client import GroqLLMClient, MockLLMClient
from src.llm.recommend import generate_recommendations

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 LLM smoke test")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM (no API key)")
    parser.add_argument("--location", default="Bangalore")
    parser.add_argument("--budget", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--cuisine", default="")
    parser.add_argument("--min-rating", type=float, default=0.0)
    args = parser.parse_args()

    store = load_restaurant_store()
    preferences = UserPreferences(
        location=args.location,
        budget=BudgetTier(args.budget),
        cuisine=args.cuisine or None,
        min_rating=args.min_rating,
    )

    filtered = filter_candidates(preferences, store)
    print(f"Candidates: {len(filtered.candidates)} (total matches: {filtered.total_matches})")
    if not filtered.candidates:
        print(filtered.message or "No candidates to send to LLM.")
        return

    client = MockLLMClient() if args.mock else GroqLLMClient()
    if args.mock:
        print("Using mock LLM client.")
    else:
        print("Using Groq client (requires GROQ_API_KEY).")

    result = generate_recommendations(
        preferences,
        filtered.candidates,
        store=store,
        client=client,
    )

    print(f"\nFallback used: {result.fallback_used}")
    if result.summary:
        print(f"Summary: {result.summary}")

    print("\nRecommendations:")
    for rec in result.recommendations:
        r = rec.restaurant
        cuisines = ", ".join(r.cuisines) or "N/A"
        cost = f"{r.cost:.0f}" if r.cost else "N/A"
        print(
            f"\n#{rec.rank} {r.name} ({r.locality or r.location})\n"
            f"  {cuisines} | rating {r.rating} | cost {cost}\n"
            f"  {rec.explanation}"
        )


if __name__ == "__main__":
    main()
