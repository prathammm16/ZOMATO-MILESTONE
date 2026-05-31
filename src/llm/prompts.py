"""
Prompt templates for the recommendation engine.

Output contract (JSON only):
{
  "recommendations": [
    {"rank": 1, "restaurant_id": "<id>", "explanation": "<why it fits>"}
  ],
  "summary": "<optional one paragraph>"
}
"""

from __future__ import annotations

import json

from config import settings
from src.data.models import Restaurant, UserPreferences

SYSTEM_PROMPT = """You are an expert restaurant recommender for India.

Rules:
- ONLY recommend restaurants from the CANDIDATES list below.
- NEVER invent restaurant names or IDs not in the list.
- Rank the top {top_k} options for the user's preferences.
- Each explanation must reference specific user preferences (location, budget, cuisine, rating).
- Respond with valid JSON only — no markdown fences or extra text.

Output schema:
{{
  "recommendations": [
    {{"rank": 1, "restaurant_id": "<id from list>", "explanation": "<1-2 sentences>"}}
  ],
  "summary": "<optional short overview>"
}}"""


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _format_candidate(restaurant: Restaurant, index: int) -> dict:
    max_chars = settings.MAX_FIELD_CHARS
    area = restaurant.locality or restaurant.location
    return {
        "index": index,
        "id": restaurant.id,
        "name": _truncate(restaurant.name, max_chars),
        "area": _truncate(area, max_chars),
        "city": restaurant.location,
        "cuisines": restaurant.cuisines[:5],
        "rating": restaurant.rating,
        "cost": restaurant.cost,
        "budget_tier": restaurant.budget_tier.value,
    }


def build_recommendation_prompt(
    preferences: UserPreferences,
    candidates: list[Restaurant],
    *,
    top_k: int | None = None,
) -> tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for the LLM.

    Returns system and user message bodies.
    """
    k = top_k if top_k is not None else settings.TOP_RECOMMENDATIONS
    prefs_payload = {
        "location": preferences.location,
        "budget": preferences.budget.value,
        "cuisine": preferences.cuisine,
        "min_rating": preferences.min_rating,
        "additional_preferences": preferences.additional_preferences,
    }
    candidate_rows = [_format_candidate(r, i + 1) for i, r in enumerate(candidates)]
    user_payload = {
        "user_preferences": prefs_payload,
        "instructions": (
            f"Rank the top {k} restaurants. Use only restaurant_id values from candidates."
        ),
        "candidates": candidate_rows,
    }
    system = SYSTEM_PROMPT.format(top_k=k)
    user = json.dumps(user_payload, indent=2)
    return system, user


def build_json_retry_prompt(previous_response: str) -> tuple[str, str]:
    """Short retry when the model did not return parseable JSON."""
    system = "You fix malformed outputs. Return valid JSON only matching the required schema."
    user = (
        "The previous response was not valid JSON. "
        "Return ONLY a JSON object with keys recommendations (array) "
        "and optional summary.\n\n"
        f"Previous response:\n{previous_response[:2000]}"
    )
    return system, user
