#!/usr/bin/env python3
"""
Fellowship demo script (~2 minutes).

Walkthrough: load data -> set preferences -> filter -> Groq rank -> show top 3.

Note: this dataset is Bangalore-centric (no Delhi rows). Demo uses:
  Location: Bangalore | Budget: medium | Cuisine: Italian

Usage (from project root):
  python scripts/demo.py           # live Groq (requires GROQ_API_KEY)
  python scripts/demo.py --mock    # offline demo
"""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import settings
from src.api.orchestrator import get_recommendations
from src.data.loader import load_restaurant_store
from src.data.models import BudgetTier, UserPreferences
from src.llm.client import MockLLMClient

logging.basicConfig(level=logging.WARNING)

DEMO_PREFS = UserPreferences(
    location="Bangalore",
    budget=BudgetTier.MEDIUM,
    cuisine="Italian",
    min_rating=3.5,
)


def _section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _pause(seconds: float = 0.5) -> None:
    time.sleep(seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Zomato AI fellowship demo")
    parser.add_argument("--mock", action="store_true", help="Use mock Groq (no API key)")
    args = parser.parse_args()

    _section("1. Zomato AI Restaurant Recommendation System")
    print(
        textwrap.dedent(
            """
            Pipeline: Hugging Face dataset -> filter -> Groq LLM -> explanations

            Dataset: ManikaSaini/zomato-restaurant-recommendation
            LLM: Groq ({model})
            """
        ).strip().format(model=settings.GROQ_MODEL)
    )
    _pause()

    _section("2. Loading restaurant store")
    t0 = time.perf_counter()
    store = load_restaurant_store()
    print(f"Loaded {store.count():,} restaurants in {time.perf_counter() - t0:.1f}s")
    _pause()

    _section("3. User preferences")
    print(f"  Location : {DEMO_PREFS.location}")
    print(f"  Budget   : {DEMO_PREFS.budget.value}")
    print(f"  Cuisine  : {DEMO_PREFS.cuisine}")
    print(f"  Min rating: {DEMO_PREFS.min_rating}")
    print(
        "\n  (Plan example used Delhi; this dataset is mostly Bangalore — "
        "same flow applies.)"
    )
    _pause()

    client = MockLLMClient() if args.mock else None
    if args.mock:
        print("\n  [Mock mode — no Groq API call]")
    elif not settings.GROQ_API_KEY:
        print("\n  ERROR: Set GROQ_API_KEY in .env or use --mock")
        sys.exit(1)

    _section("4. Running pipeline (filter -> Groq -> rank)")
    t1 = time.perf_counter()
    response = get_recommendations(DEMO_PREFS, store, client=client)
    elapsed = time.perf_counter() - t1
    print(f"Completed in {elapsed:.1f}s")
    print(f"  Candidates screened : {response.metadata.candidate_count}")
    print(f"  Total filter matches: {response.metadata.total_matches}")
    print(f"  LLM used            : {response.metadata.llm_used}")
    print(f"  Fallback used       : {response.metadata.fallback_used}")
    if response.metadata.groq_latency_ms:
        print(f"  Groq latency        : {response.metadata.groq_latency_ms:.0f} ms")
    _pause()

    if response.validation_errors:
        print("Validation errors:", "; ".join(response.validation_errors))
        sys.exit(1)

    if not response.recommendations:
        print("\nNo recommendations:", response.message)
        sys.exit(0)

    if response.summary:
        _section("5. AI summary")
        print(response.summary)
        _pause()

    _section("6. Top 3 recommendations")
    for rec in response.recommendations[:3]:
        r = rec.restaurant
        cuisines = ", ".join(r.cuisines) or "N/A"
        cost = f"Rs.{r.cost:.0f} for two" if r.cost else "N/A"
        area = r.locality or r.location
        print(f"\n#{rec.rank} {r.name} ({area})")
        print(f"   Cuisine : {cuisines}")
        print(f"   Rating  : {r.rating}/5")
        print(f"   Cost    : {cost}")
        print(f"   Why     : {rec.explanation}")

    _section("Demo complete")
    print("Launch UI: streamlit run src/ui/app.py")
    print("Tests:     python -m pytest -v -m \"not integration\"")


if __name__ == "__main__":
    main()
