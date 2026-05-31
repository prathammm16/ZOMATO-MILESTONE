"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _env_or_secret(key: str, default: str | None = None) -> str | None:
    """Read from OS env (Streamlit Cloud) or st.secrets (local Streamlit parity)."""
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


HF_DATASET_ID: str = _env_or_secret(
    "HF_DATASET_ID", "ManikaSaini/zomato-restaurant-recommendation"
) or "ManikaSaini/zomato-restaurant-recommendation"
HF_TOKEN: str | None = _env_or_secret("HF_TOKEN") or _env_or_secret("HUGGING_FACE_HUB_TOKEN")


def _parse_optional_int(key: str) -> int | None:
    raw = _env_or_secret(key)
    if not raw:
        return None
    return int(raw)


def _default_hf_max_rows() -> int | None:
    configured = _parse_optional_int("HF_MAX_ROWS")
    if configured is not None:
        return configured
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        # Full HF ingest (~51k rows) often OOMs on small Railway instances.
        return 20_000
    return None


HF_MAX_ROWS: int | None = _default_hf_max_rows()
DATA_CACHE_PATH: Path = PROJECT_ROOT / (
    _env_or_secret("DATA_CACHE_PATH", "data/cache.parquet") or "data/cache.parquet"
)
FORCE_REFRESH: bool = (_env_or_secret("FORCE_REFRESH") or "false").lower() in (
    "1",
    "true",
    "yes",
)

# Groq (canonical for Phases 3–4)
GROQ_API_KEY: str | None = _env_or_secret("GROQ_API_KEY") or _env_or_secret("LLM_API_KEY")
GROQ_MODEL: str = (
    _env_or_secret("GROQ_MODEL")
    or _env_or_secret("LLM_MODEL")
    or "llama-3.3-70b-versatile"
)
GROQ_TIMEOUT_SECONDS: int = int(
    _env_or_secret("GROQ_TIMEOUT_SECONDS")
    or _env_or_secret("LLM_TIMEOUT_SECONDS")
    or "30"
)
GROQ_TEMPERATURE: float = float(
    _env_or_secret("GROQ_TEMPERATURE")
    or _env_or_secret("LLM_TEMPERATURE")
    or "0.3"
)

# Legacy aliases (deprecated)
LLM_API_KEY = GROQ_API_KEY
LLM_MODEL = GROQ_MODEL
LLM_TIMEOUT_SECONDS = GROQ_TIMEOUT_SECONDS
LLM_TEMPERATURE = GROQ_TEMPERATURE

MAX_CANDIDATES_TO_LLM: int = int(_env_or_secret("MAX_CANDIDATES_TO_LLM") or "20")
TOP_RECOMMENDATIONS: int = int(_env_or_secret("TOP_RECOMMENDATIONS") or "5")
MAX_FIELD_CHARS: int = int(_env_or_secret("MAX_FIELD_CHARS") or "120")


def _parse_cors_origins(raw: str | None) -> list[str]:
    if not raw or raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# Comma-separated list, e.g. https://my-app.vercel.app — defaults to * (all origins)
CORS_ORIGINS: list[str] = _parse_cors_origins(_env_or_secret("CORS_ORIGINS"))
