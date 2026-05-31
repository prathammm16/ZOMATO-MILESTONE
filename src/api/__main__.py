"""CLI entry: python -m src.api"""

from __future__ import annotations

import argparse
import logging
import sys

from src.data.loader import load_restaurant_store
from src.data.models import BudgetTier, UserPreferences
from src.api.orchestrator import get_recommendations
from src.llm.client import MockLLMClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 recommendation orchestrator")
    parser.add_argument("--mock", action="store_true", help="Use mock Groq client")
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

    client = MockLLMClient() if args.mock else None
    response = get_recommendations(preferences, store, client=client)

    if response.validation_errors:
        print("Validation errors:", "; ".join(response.validation_errors))
        sys.exit(1)

    if response.message and not response.recommendations:
        print(response.message)
        sys.exit(0)

    meta = response.metadata
    print(
        f"Candidates: {meta.candidate_count} | LLM used: {meta.llm_used} | "
        f"Fallback: {meta.fallback_used} | Groq ms: {meta.groq_latency_ms}"
    )
    if response.summary:
        print(f"\nSummary: {response.summary}")

    for rec in response.recommendations:
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
