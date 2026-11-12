"""Food and dining discovery endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Destination, FoodOption
from backend.schemas import FoodOptionListResponse, FoodOptionResponse, FoodPresetResponse


router = APIRouter(tags=["Food Planner"])


DAILY_FOOD_PRESETS = [
    {
        "id": "budget",
        "name": "Budget-Friendly (Street Eats, Dhabas & Thalis)",
        "daily_per_person_inr": 350,
        "description": "Pocket-friendly local breakfasts, hearty street snacks, dhabas, and traditional thalis.",
        "tier": "Budget",
    },
    {
        "id": "standard",
        "name": "Standard (Casual Dining & Regional Restaurants)",
        "daily_per_person_inr": 750,
        "description": "Clean, popular sit-down family restaurants, multi-cuisine dining, and regional specialties.",
        "tier": "Standard",
    },
    {
        "id": "premium",
        "name": "Premium (Fine Dining & Heritage Eateries)",
        "daily_per_person_inr": 1600,
        "description": "Luxury hotel restaurants, heritage culinary landmarks, and multi-course royal menus.",
        "tier": "Premium",
    },
]


def _food_payload(food: FoodOption) -> dict:
    return {
        "id": food.id,
        "city": food.city,
        "state": food.state,
        "name": food.name,
        "area": food.area,
        "cuisine": food.cuisine,
        "meal_type": food.meal_type,
        "price_tier": food.price_tier,
        "estimated_cost_inr": food.estimated_cost_inr,
        "description": food.description,
        "source_url": food.source_url,
        "is_budget_friendly": bool(food.is_budget_friendly),
    }


@router.get("/food-options/daily-presets", response_model=List[FoodPresetResponse], summary="Get recommended daily food budget presets")
def get_daily_food_presets():
    """Return indicative per-person daily food budget tiers (Budget, Standard, Premium)."""
    return DAILY_FOOD_PRESETS


@router.get("/food-options", response_model=FoodOptionListResponse, summary="Search and filter food options")
def list_food_options(
    city: Optional[str] = Query(default=None, description="Filter by city name"),
    state: Optional[str] = Query(default=None, description="Filter by state name"),
    destination_id: Optional[int] = Query(default=None, ge=1, description="Filter by single destination ID"),
    destination_ids: Optional[str] = Query(default=None, description="Comma-separated destination IDs to match relevant cities"),
    price_tier: Optional[str] = Query(default=None, description="Filter by tier: Budget, Standard, Premium"),
    budget_friendly: Optional[bool] = Query(default=None, description="Filter for budget-friendly options only"),
    cuisine: Optional[str] = Query(default=None, description="Filter by cuisine or dish type"),
    max_cost: Optional[int] = Query(default=None, ge=0, description="Maximum estimated cost per person in INR"),
    db: Session = Depends(get_db),
):
    """Retrieve food options and dining spots with indicative costs and source links."""
    query = db.query(FoodOption)

    cities_to_match = set()
    if city and city.strip():
        cities_to_match.add(city.strip().casefold())

    if destination_id is not None:
        dest = db.query(Destination).filter(Destination.id == destination_id).first()
        if dest and dest.city:
            cities_to_match.add(dest.city.strip().casefold())

    if destination_ids and destination_ids.strip():
        try:
            ids = [int(x.strip()) for x in destination_ids.split(",") if x.strip()]
            if ids:
                dests = db.query(Destination).filter(Destination.id.in_(ids)).all()
                for d in dests:
                    if d.city:
                        cities_to_match.add(d.city.strip().casefold())
        except ValueError:
            pass

    if cities_to_match:
        from sqlalchemy import or_
        query = query.filter(or_(*[FoodOption.city.ilike(f"%{c}%") for c in cities_to_match]))

    if state and state.strip():
        query = query.filter(FoodOption.state.ilike(f"%{state.strip()}%"))

    if price_tier and price_tier.strip():
        query = query.filter(FoodOption.price_tier.ilike(f"%{price_tier.strip()}%"))

    if budget_friendly is True:
        query = query.filter(FoodOption.is_budget_friendly == 1)

    if cuisine and cuisine.strip():
        query = query.filter(FoodOption.cuisine.ilike(f"%{cuisine.strip()}%"))

    if max_cost is not None:
        query = query.filter(FoodOption.estimated_cost_inr <= max_cost)

    food_items = query.order_by(
        FoodOption.is_budget_friendly.desc(),
        FoodOption.estimated_cost_inr.asc(),
        FoodOption.name.asc(),
    ).all()

    return {
        "count": len(food_items),
        "food_options": [_food_payload(item) for item in food_items],
    }
