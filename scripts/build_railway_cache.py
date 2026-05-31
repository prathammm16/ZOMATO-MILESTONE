"""
Build data/railway_bootstrap.parquet for Railway (avoids HF download on deploy).

Run once locally (requires network):
    python scripts/build_railway_cache.py

Commit the generated file so Railway loads from disk instead of Hugging Face.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from src.data.ingestion import iter_raw_dataset, normalize_rows, save_cache


def main() -> None:
    max_rows = 8_000
    out = settings.RAILWAY_BOOTSTRAP_CACHE
    print(f"Building {out} (max_rows={max_rows}, strip_metadata=True)...")
    rows = iter_raw_dataset(max_rows=max_rows)
    restaurants, stats = normalize_rows(rows, include_raw_metadata=False)
    if not restaurants:
        raise SystemExit("No restaurants produced — check network and dataset.")
    out.parent.mkdir(parents=True, exist_ok=True)
    save_cache(restaurants, out)
    print(
        f"Done: {len(restaurants)} restaurants, "
        f"{stats.unique_locations} locations -> {out}"
    )


if __name__ == "__main__":
    main()
