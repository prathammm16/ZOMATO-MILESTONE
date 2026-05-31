"""
Zomato AI Restaurant Recommendations — Streamlit UI (Phase 5).

Run from project root:
    streamlit run src/ui/app.py
"""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from src.api.orchestrator import get_recommendations
from src.data.loader import load_restaurant_store
from src.data.models import BudgetTier, Recommendation, RecommendationResponse, UserPreferences
from src.data.store import RestaurantStore
from src.filtering.locations import get_location_options

BUDGET_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}

MIN_NUM_RECOMMENDATIONS = 1
MAX_NUM_RECOMMENDATIONS = 10
CUISINE_ANY_LABEL = "(Any cuisine)"


@st.cache_resource(show_spinner="Loading restaurant dataset…")
def get_store() -> RestaurantStore:
    """Load restaurant store once per server process."""
    return load_restaurant_store()


def _inject_theme_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #07090d;
            --surface: #14151f;
            --surface-2: #1a1117;
            --surface-3: #24171d;
            --border: rgba(255, 190, 185, 0.13);
            --border-strong: rgba(255, 157, 148, 0.28);
            --text: #f7e7e4;
            --muted: #b99f9a;
            --accent: #ff4a5f;
            --accent-2: #ffa39f;
            --gold: #ffbf73;
            --green: #4fd081;
        }

        html, body, [class*="css"] {
            font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            color: var(--text);
            background:
                radial-gradient(circle at 12% 0%, rgba(255, 74, 95, 0.12), transparent 31rem),
                radial-gradient(circle at 90% 7%, rgba(255, 163, 159, 0.08), transparent 26rem),
                linear-gradient(180deg, #09070a 0%, var(--bg) 36%, #050609 100%);
        }

        [data-testid="stHeader"] {
            display: none;
        }

        #MainMenu, footer, [data-testid="stToolbar"] {
            visibility: hidden;
        }

        .block-container {
            max-width: 1200px;
            padding: 0.85rem 2.1rem 3rem;
        }

        h1, h2, h3, p {
            letter-spacing: -0.02em;
        }

        label, .stMarkdown, .stCaption {
            color: var(--text) !important;
        }

        .topbar {
            align-items: center;
            background: linear-gradient(135deg, rgba(31, 14, 18, 0.96), rgba(15, 16, 24, 0.92));
            border: 1px solid rgba(255, 163, 159, 0.1);
            border-radius: 1rem;
            box-shadow: 0 18px 55px rgba(0, 0, 0, 0.36);
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin: 0 0 1.2rem;
            min-height: 3.85rem;
            padding: 0.8rem 1.1rem;
        }

        .brand {
            align-items: center;
            color: #ffd2d6;
            display: flex;
            font-size: 1.25rem;
            font-weight: 800;
            gap: 0.6rem;
            letter-spacing: -0.06em;
        }

        .brand-mark {
            align-items: center;
            background: #e93445;
            border-radius: 0.85rem;
            box-shadow: 0 10px 24px rgba(233, 52, 69, 0.32);
            color: #ffffff;
            display: inline-flex;
            font-size: 1.05rem;
            font-style: italic;
            font-weight: 900;
            height: 2.25rem;
            justify-content: center;
            letter-spacing: -0.07em;
            line-height: 1;
            padding: 0 0.85rem;
            text-transform: lowercase;
        }

        .brand-copy {
            color: #ffe1e4;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        .navlinks {
            align-items: center;
            color: #d5b8b4;
            display: flex;
            font-size: 0.78rem;
            font-weight: 700;
            gap: 1.35rem;
            letter-spacing: 0.08em;
        }

        .navlinks span:first-child {
            color: #ffced0;
        }

        .nav-badge {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 999px;
            color: #9df2b6;
            font-size: 0.68rem;
            font-weight: 850;
            letter-spacing: 0.1em;
            padding: 0.5rem 0.7rem;
            text-transform: uppercase;
        }

        .hero-row {
            align-items: flex-start;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin: 0.2rem 0 1.3rem;
        }

        .eyebrow {
            color: #ff9e9a;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .hero-title {
            color: #fff3f1;
            font-size: clamp(2rem, 4vw, 3.15rem);
            font-weight: 850;
            letter-spacing: -0.075em;
            line-height: 0.95;
            margin: 0;
        }

        .hero-subtitle {
            color: var(--muted);
            font-size: 0.98rem;
            margin-top: 0.55rem;
        }

        .status-pill {
            align-items: center;
            background: rgba(26, 27, 38, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 999px;
            color: #9df2b6;
            display: inline-flex;
            font-size: 0.72rem;
            font-weight: 800;
            gap: 0.5rem;
            letter-spacing: 0.08em;
            padding: 0.75rem 1rem;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .status-pill.fallback {
            color: #ffd48c;
        }

        .status-dot {
            background: var(--green);
            border-radius: 99px;
            box-shadow: 0 0 15px rgba(79, 208, 129, 0.75);
            height: 0.45rem;
            width: 0.45rem;
        }

        .status-pill.fallback .status-dot {
            background: var(--gold);
            box-shadow: 0 0 15px rgba(255, 191, 115, 0.75);
        }

        .panel-card {
            background: linear-gradient(180deg, rgba(24, 24, 35, 0.98), rgba(18, 18, 27, 0.98));
            border: 1px solid var(--border);
            border-radius: 1rem;
            box-shadow: 0 24px 65px rgba(0, 0, 0, 0.42);
            padding: 1.2rem;
        }

        .panel-title {
            align-items: center;
            color: #fff0ee;
            display: flex;
            font-size: 1.15rem;
            font-weight: 800;
            gap: 0.55rem;
            margin-bottom: 1rem;
        }

        .panel-caption {
            color: var(--muted);
            font-size: 0.78rem;
            line-height: 1.55;
            margin-top: 1rem;
        }

        div[data-testid="stForm"] {
            background: linear-gradient(180deg, rgba(24, 24, 35, 0.98), rgba(18, 18, 27, 0.98));
            border: 1px solid var(--border);
            border-radius: 1rem;
            box-shadow: 0 24px 65px rgba(0, 0, 0, 0.42);
            padding: 1.1rem 1.15rem 1.2rem;
        }

        div[data-testid="stForm"] label p {
            color: #f1d7d3 !important;
            font-size: 0.72rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput input,
        .stTextArea textarea {
            background: #2a1518 !important;
            border: 1px solid rgba(255, 109, 121, 0.12) !important;
            border-radius: 0.55rem !important;
            color: var(--text) !important;
        }

        div[role="radiogroup"] {
            background: #2a1518;
            border-radius: 0.65rem;
            gap: 0.25rem;
            padding: 0.18rem;
        }

        div[role="radiogroup"] label {
            border-radius: 0.5rem;
            padding: 0.42rem 0.48rem;
        }

        div[role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(135deg, #ff4a5f, #ffa39f);
            color: #21090d !important;
        }

        .stSlider [data-baseweb="slider"] div {
            color: var(--accent-2);
        }

        [data-testid="stFormSubmitButton"] button,
        div.stButton > button {
            background: linear-gradient(135deg, #ff3850 0%, #ff4e67 55%, #ff8b87 100%) !important;
            border: 0 !important;
            border-radius: 0.75rem !important;
            box-shadow: 0 14px 28px rgba(255, 56, 80, 0.28);
            color: #fff3f1 !important;
            font-weight: 800 !important;
            min-height: 3.2rem;
        }

        .stats-grid {
            display: grid;
            gap: 1rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin: 1rem 0 1.55rem;
        }

        .stat-card {
            background: linear-gradient(180deg, rgba(26, 26, 38, 0.97), rgba(20, 20, 31, 0.98));
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-left: 3px solid rgba(255, 163, 159, 0.8);
            border-radius: 0.8rem;
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.3);
            padding: 1rem 1.1rem;
        }

        .stat-card:nth-child(3) {
            border-left-color: #38cfa0;
        }

        .stat-label {
            color: #c9a9a4;
            font-size: 0.67rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .stat-value {
            color: #fff1ef;
            font-size: 1.7rem;
            font-weight: 850;
            letter-spacing: -0.06em;
            margin-top: 0.25rem;
        }

        .stat-value span {
            color: #d9c0bb;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-left: 0.25rem;
        }

        .summary-card,
        .state-card {
            background: linear-gradient(135deg, rgba(255, 74, 95, 0.13), rgba(255, 163, 159, 0.06));
            border: 1px solid var(--border-strong);
            border-radius: 0.9rem;
            color: #ffe8e5;
            margin-bottom: 1.25rem;
            padding: 1rem 1.15rem;
        }

        .summary-card strong,
        .state-card strong {
            color: #ffb8b5;
            display: block;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .recommendation-grid {
            display: grid;
            gap: 1.25rem;
            grid-template-columns: repeat(auto-fit, minmax(235px, 1fr));
            margin-top: 0.35rem;
        }

        .recommendation-card {
            background:
                linear-gradient(180deg, rgba(25, 25, 36, 0.98), rgba(18, 18, 27, 0.98)),
                radial-gradient(circle at 100% 0%, rgba(255, 74, 95, 0.12), transparent 18rem);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 1rem;
            box-shadow: 0 22px 58px rgba(0, 0, 0, 0.4);
            display: flex;
            flex-direction: column;
            min-height: 330px;
            overflow: hidden;
            padding: 1.05rem;
            position: relative;
        }

        .recommendation-card::before {
            background: linear-gradient(180deg, #ff8f8b, transparent);
            border-radius: 99px;
            content: "";
            height: 40%;
            left: 0;
            opacity: 0.45;
            position: absolute;
            top: 1rem;
            width: 2px;
        }

        .card-top {
            align-items: flex-start;
            display: flex;
            gap: 1rem;
            justify-content: space-between;
            margin-bottom: 0.75rem;
        }

        .rank-badge {
            background: transparent;
            border-radius: 0;
            color: #9b8583;
            display: inline-block;
            font-size: 0.62rem;
            font-weight: 900;
            letter-spacing: 0.16em;
            margin-bottom: 0.4rem;
            padding: 0;
            text-transform: uppercase;
        }

        .restaurant-name {
            color: #fff4f2;
            font-size: 1.12rem;
            font-weight: 850;
            letter-spacing: -0.045em;
            margin: 0;
            max-width: 13rem;
        }

        .rating-badge {
            background: rgba(66, 196, 220, 0.12);
            border: 1px solid rgba(66, 196, 220, 0.18);
            border-radius: 0.45rem;
            color: #7de6ff;
            font-size: 0.65rem;
            font-weight: 800;
            padding: 0.35rem 0.5rem;
            white-space: nowrap;
        }

        .meta-line {
            align-items: center;
            color: #cdb7b2;
            display: grid;
            font-size: 0.76rem;
            gap: 0.55rem 0.65rem;
            grid-template-columns: 1fr 1fr;
            margin: 0.3rem 0 0.9rem;
        }

        .meta-line span {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.38rem;
            margin-bottom: 0.85rem;
        }

        .chip {
            background: rgba(255, 255, 255, 0.045);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 0.32rem;
            color: #bfa9a5;
            font-size: 0.66rem;
            font-weight: 700;
            padding: 0.26rem 0.45rem;
        }

        .ai-box {
            background: rgba(255, 255, 255, 0.055);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 0.75rem;
            margin-top: auto;
            min-height: 5.5rem;
            overflow: hidden;
            padding: 0.75rem;
        }

        .ai-title {
            color: #c8b4af;
            font-size: 0.62rem;
            font-weight: 850;
            letter-spacing: 0.13em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .ai-copy {
            color: #f1dfdc;
            display: -webkit-box;
            font-size: 0.76rem;
            font-style: italic;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            line-height: 1.45;
            overflow: hidden;
        }

        .pipeline {
            align-items: center;
            color: #cfb5b0;
            display: flex;
            flex-wrap: wrap;
            font-size: 0.76rem;
            font-weight: 700;
            gap: 0.45rem;
            margin-top: 0.8rem;
        }

        .pipeline span {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 999px;
            padding: 0.35rem 0.6rem;
        }

        @media (max-width: 900px) {
            .topbar,
            .hero-row {
                align-items: flex-start;
                flex-direction: column;
            }

            .stats-grid {
                grid-template-columns: 1fr;
            }

            .navlinks {
                display: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _location_choices(store: RestaurantStore) -> list[str]:
    opts = get_location_options(store)
    cities = opts["cities"]
    localities = opts["localities"]
    choices: list[str] = []
    if cities:
        choices.extend(cities)
    if localities:
        locality_only = [loc for loc in localities if loc not in choices]
        choices.extend(locality_only)
    return choices or ["Bangalore"]


def _default_location_index(choices: list[str]) -> int:
    for preferred in ("Bangalore", "Bengaluru"):
        for i, loc in enumerate(choices):
            if loc.casefold() == preferred.casefold():
                return i
    return 0


def _default_num_recommendations() -> int:
    return max(MIN_NUM_RECOMMENDATIONS, min(MAX_NUM_RECOMMENDATIONS, settings.TOP_RECOMMENDATIONS))


def _cuisine_choices(store: RestaurantStore) -> list[str]:
    return [CUISINE_ANY_LABEL, *store.get_distinct_cuisines()]


def _format_cost(cost: float | None) -> str:
    if cost is None:
        return "Cost not listed"
    return f"₹{cost:.0f} for two"


def _render_nav() -> None:
    st.markdown(
        """
        <div class="topbar">
            <div class="brand">
                <span class="brand-mark">zomato</span>
                <span class="brand-copy">AI Recommender</span>
            </div>
            <div class="navlinks">
                <span>Discover</span>
                <span>For You</span>
                <span>AI Picks</span>
                <span class="nav-badge">Live Demo</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_hero(response: RecommendationResponse | None = None) -> None:
    fallback = bool(response and response.metadata.fallback_used)
    status_text = "Fallback Ranking" if fallback else "AI Ranking Active"
    fallback_class = " fallback" if fallback else ""
    st.markdown(
        f"""
        <div class="hero-row">
            <div>
                <div class="eyebrow">Real Data + Groq AI</div>
                <h1 class="hero-title">Personalized Picks</h1>
                <div class="hero-subtitle">Restaurant recommendations tailored to your palate.</div>
            </div>
            <div class="status-pill{fallback_class}">
                <span class="status-dot"></span>{escape(status_text)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_preference_form(store: RestaurantStore) -> UserPreferences | None:
    location_choices = _location_choices(store)

    with st.form("preference_form"):
        st.markdown('<div class="panel-title">☷ Refine Search</div>', unsafe_allow_html=True)
        location = st.selectbox(
            "Location",
            options=location_choices,
            index=_default_location_index(location_choices),
        )
        num_recommendations = int(
            st.number_input(
                "Number of Recommendations",
                min_value=MIN_NUM_RECOMMENDATIONS,
                max_value=MAX_NUM_RECOMMENDATIONS,
                value=_default_num_recommendations(),
                step=1,
            )
        )
        budget_label = st.radio(
            "Budget",
            options=list(BUDGET_LABELS.keys()),
            format_func=lambda k: BUDGET_LABELS[k],
            horizontal=True,
            index=1,
        )
        cuisine_choice = st.selectbox(
            "Cuisine",
            options=_cuisine_choices(store),
            index=0,
        )
        min_rating = st.slider("Minimum Rating", min_value=0.0, max_value=5.0, value=4.0, step=0.5)
        additional_preferences = st.text_area(
            "Dining Mood",
            placeholder="Date night, family-friendly, quick service...",
            height=88,
        )
        submitted = st.form_submit_button(
            "✨ Update Recommendations",
            type="primary",
            use_container_width=True,
        )

    st.markdown(
        f"""
        <div class="panel-caption">
            Dataset ready with <strong>{store.count():,}</strong> restaurants.
            Model: <strong>{escape(settings.GROQ_MODEL)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not submitted:
        return None

    cuisine = None if cuisine_choice == CUISINE_ANY_LABEL else cuisine_choice
    return UserPreferences(
        location=location,
        budget=BudgetTier(budget_label),
        cuisine=cuisine,
        min_rating=min_rating,
        additional_preferences=additional_preferences,
        num_recommendations=num_recommendations,
    )


def _render_stats(store_count: int, response: RecommendationResponse | None = None) -> None:
    if response is None:
        discovered = store_count
        screened = settings.MAX_CANDIDATES_TO_LLM
        selected = settings.TOP_RECOMMENDATIONS
    else:
        discovered = response.metadata.total_matches or len(response.recommendations)
        screened = response.metadata.candidate_count
        selected = len(response.recommendations)

    st.markdown(
        f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Discovered</div>
                <div class="stat-value">{discovered:,}<span>Restaurants</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Screened</div>
                <div class="stat-value">{screened:,}<span>Candidates</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Selected</div>
                <div class="stat-value">{selected:,}<span>Top Matches</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_validation_errors(response: RecommendationResponse) -> None:
    messages = response.validation_errors or [response.message or "Please adjust your search filters."]
    for error in messages:
        _render_state_card("Preference check", error)


def _render_state_card(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="state-card">
            <strong>{escape(title)}</strong>
            <div>{escape(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_state(response: RecommendationResponse) -> None:
    _render_state_card(
        "No matches found",
        response.message
        or "Try a broader cuisine, lower the minimum rating, or switch to a different budget tier.",
    )


def _render_fallback_banner(response: RecommendationResponse) -> None:
    if response.metadata.fallback_used:
        _render_state_card(
            "Fallback recommendations",
            "AI ranking is temporarily unavailable. Showing the strongest filter-based matches.",
        )


def _render_summary(response: RecommendationResponse) -> None:
    if response.summary:
        st.markdown(
            f"""
            <div class="summary-card">
                <strong>AI Summary</strong>
                <div>{escape(response.summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _match_score(rec: Recommendation) -> int:
    return max(72, 100 - ((rec.rank - 1) * 6))


def _recommendation_card_html(rec: Recommendation) -> str:
    restaurant = rec.restaurant
    area = restaurant.locality or restaurant.location
    cost_label = _format_cost(restaurant.cost)
    cuisines = restaurant.cuisines or ["Cuisine not listed"]
    visible_cuisines = cuisines[:5]
    cuisine_chips = "".join(f'<span class="chip">{escape(cuisine)}</span>' for cuisine in visible_cuisines)
    if len(cuisines) > len(visible_cuisines):
        cuisine_chips += f'<span class="chip">+{len(cuisines) - len(visible_cuisines)} more</span>'

    return (
        '<article class="recommendation-card">'
        '<div class="card-top">'
        "<div>"
        f'<span class="rank-badge">Rank #{rec.rank}</span>'
        f'<h3 class="restaurant-name">{escape(restaurant.name)}</h3>'
        "</div>"
        f'<div class="rating-badge">{_match_score(rec)}% Match</div>'
        "</div>"
        '<div class="meta-line">'
        f"<span>★ {restaurant.rating:.1f}</span>"
        f"<span>🍴 {escape(restaurant.budget_tier.value.title())}</span>"
        f"<span>⌖ {escape(area)}</span>"
        f"<span>{escape(cost_label)}</span>"
        "</div>"
        f'<div class="chip-row">{cuisine_chips}</div>'
        '<div class="ai-box">'
        '<div class="ai-title">Why AI Picked It</div>'
        f'<div class="ai-copy">"{escape(rec.explanation)}"</div>'
        "</div>"
        "</article>"
    )


def _render_recommendation_card(rec: Recommendation) -> None:
    st.markdown(_recommendation_card_html(rec), unsafe_allow_html=True)


def _render_pipeline() -> None:
    st.markdown(
        """
        <div class="pipeline">
            <span>Preferences</span>
            →
            <span>Dataset Filter</span>
            →
            <span>Groq Ranking</span>
            →
            <span>Grounded Results</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_initial_state(store_count: int) -> None:
    _render_stats(store_count)
    st.markdown(
        """
        <div class="state-card">
            <strong>Ready to discover</strong>
            <div>
                Tune your location, budget, cuisine, and rating preferences, then generate
                AI-ranked restaurant picks grounded in the Zomato dataset.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_pipeline()


def _render_results(response: RecommendationResponse, store_count: int) -> None:
    _render_stats(store_count, response)
    _render_fallback_banner(response)
    _render_summary(response)

    if not response.recommendations:
        return

    cards = "".join(_recommendation_card_html(rec) for rec in response.recommendations)
    st.markdown(f'<div class="recommendation-grid">{cards}</div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Zomato | AI Recommendations",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_theme_css()
    _render_nav()

    try:
        store = get_store()
    except Exception as exc:
        _render_state_card("Could not load restaurant data", str(exc))
        st.stop()

    left, right = st.columns([0.28, 0.72], gap="large")
    with left:
        preferences = _render_preference_form(store)

    with right:
        if not settings.GROQ_API_KEY:
            _render_hero()
            _render_state_card(
                "Groq API key missing",
                "Set GROQ_API_KEY in Streamlit Cloud Secrets (or in .env / "
                ".streamlit/secrets.toml locally), then restart the app.",
            )
            _render_pipeline()
            return

        if preferences is None:
            _render_hero()
            _render_initial_state(store.count())
            return

        with st.spinner("Finding and ranking restaurants with Groq AI…"):
            try:
                response = get_recommendations(preferences, store)
            except Exception as exc:
                _render_hero()
                _render_state_card("Something went wrong", str(exc))
                return

        _render_hero(response)

        if response.validation_errors:
            _render_stats(store.count(), response)
            _render_validation_errors(response)
            return

        if not response.recommendations:
            _render_stats(store.count(), response)
            _render_empty_state(response)
            return

        _render_results(response, store.count())


if __name__ == "__main__":
    main()
