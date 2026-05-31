"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src.data.models import BudgetTier, Restaurant
from src.data.store import RestaurantStore


@pytest.fixture
def sample_restaurants() -> list[Restaurant]:
    return [
        Restaurant(
            id="r_delhi_1",
            name="Spice Kitchen",
            location="Delhi",
            locality="Connaught Place",
            cuisines=["North Indian", "Chinese"],
            cost=400.0,
            budget_tier=BudgetTier.LOW,
            rating=4.2,
        ),
        Restaurant(
            id="r_delhi_2",
            name="Pasta Palace",
            location="Delhi",
            cuisines=["Italian"],
            cost=1200.0,
            budget_tier=BudgetTier.HIGH,
            rating=4.8,
        ),
        Restaurant(
            id="r_bangalore_1",
            name="Dosa Corner",
            location="Bangalore",
            cuisines=["South Indian"],
            cost=300.0,
            budget_tier=BudgetTier.LOW,
            rating=4.0,
        ),
        Restaurant(
            id="r_bangalore_2",
            name="Biryani House",
            location="Bangalore",
            cuisines=["Mughlai", "North Indian"],
            cost=800.0,
            budget_tier=BudgetTier.MEDIUM,
            rating=4.5,
        ),
        Restaurant(
            id="r_mumbai_1",
            name="Seafood Shack",
            location="Mumbai",
            cuisines=["Seafood"],
            cost=1500.0,
            budget_tier=BudgetTier.HIGH,
            rating=3.9,
        ),
    ]


@pytest.fixture
def sample_store(sample_restaurants: list[Restaurant]) -> RestaurantStore:
    return RestaurantStore(sample_restaurants)
