"""Stay-area and accommodation discovery endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Accommodation, Destination, StayArea


router = APIRouter(tags=["Stay Planner"])


def _area_payload(area: StayArea):
    return {
        "id": area.id,
        "city": area.city,
        "state": area.state,
        "name": area.name,
        "description": area.description,
        "nearby_attractions": [
            item.strip() for item in (area.nearby_attractions or "").split("|") if item.strip()
        ],
        "budget_category": area.budget_category,
        "source_url": area.source_url,
        "accommodation_count": len(area.accommodations),
    }


def _accommodation_payload(stay: Accommodation):
    area = stay.stay_area
    min_p = stay.price_min_inr
    if min_p is not None:
        if min_p <= 1500:
            tier = "Budget"
        elif min_p <= 4000:
            tier = "Standard"
        else:
            tier = "Premium"
    else:
        tier = "Budget" if area and "budget" in area.budget_category.lower() else "Standard"

    is_budget = (min_p is not None and min_p <= 1500) or (area and "budget" in area.budget_category.lower())

    return {
        "id": stay.id,
        "name": stay.name,
        "property_type": stay.property_type,
        "address": stay.address,
        "city": area.city,
        "state": area.state,
        "area": area.name,
        "area_id": area.id,
        "price_min_inr": stay.price_min_inr,
        "price_max_inr": stay.price_max_inr,
        "price_tier": tier,
        "is_budget_friendly": bool(is_budget),
        "amenities": [
            item.strip() for item in (stay.amenities or "").split("|") if item.strip()
        ],
        "website_url": stay.website_url,
        "source_url": stay.source_url,
        "price_note": stay.price_note,
    }


@router.get("/stay-areas", summary="List suggested areas to stay in")
def list_stay_areas(
    city: Optional[str] = Query(default=None, description="Filter by city"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    db: Session = Depends(get_db),
):
    query = db.query(StayArea).options(joinedload(StayArea.accommodations))
    if city and city.strip():
        query = query.filter(StayArea.city.ilike(f"%{city.strip()}%"))
    if state and state.strip():
        query = query.filter(StayArea.state.ilike(f"%{state.strip()}%"))
    areas = query.order_by(StayArea.city.asc(), StayArea.name.asc()).all()
    return {"count": len(areas), "areas": [_area_payload(area) for area in areas]}


@router.get("/accommodations", summary="Search hotels and other places to stay")
def list_accommodations(
    city: Optional[str] = Query(default=None, description="Filter by city"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    destination_id: Optional[int] = Query(default=None, ge=1, description="Filter by single destination ID"),
    destination_ids: Optional[str] = Query(default=None, description="Comma-separated destination IDs to match cities"),
    area_id: Optional[int] = Query(default=None, ge=1, description="Filter by stay area ID"),
    property_type: Optional[str] = Query(default=None, description="Filter by property type"),
    price_tier: Optional[str] = Query(default=None, description="Filter by price tier: Budget, Standard, Premium"),
    budget_friendly: Optional[bool] = Query(default=None, description="Filter for budget-friendly properties"),
    max_price: Optional[int] = Query(default=None, ge=0, description="Maximum nightly tariff in INR"),
    db: Session = Depends(get_db),
):
    query = db.query(Accommodation).join(StayArea).options(joinedload(Accommodation.stay_area))

    cities_to_match = set()
    if city and city.strip():
        cities_to_match.add(city.strip().casefold())

    if destination_id is not None:
        destination = db.query(Destination).filter(Destination.id == destination_id).first()
        if destination is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination with ID {destination_id} not found.",
            )
        cities_to_match.add(destination.city.strip().casefold())

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
        query = query.filter(or_(*[StayArea.city.ilike(f"%{c}%") for c in cities_to_match]))

    if state and state.strip():
        query = query.filter(StayArea.state.ilike(f"%{state.strip()}%"))
    if area_id is not None:
        query = query.filter(Accommodation.stay_area_id == area_id)
    if property_type and property_type.strip():
        query = query.filter(Accommodation.property_type.ilike(f"%{property_type.strip()}%"))

    if budget_friendly is True:
        query = query.filter(
            or_(
                Accommodation.price_min_inr <= 1500,
                StayArea.budget_category.ilike("%budget%"),
            )
        )

    if price_tier and price_tier.strip():
        tier_lower = price_tier.strip().lower()
        if tier_lower == "budget":
            query = query.filter(
                or_(
                    Accommodation.price_min_inr <= 1500,
                    StayArea.budget_category.ilike("%budget%"),
                )
            )
        elif tier_lower == "standard":
            query = query.filter(
                Accommodation.price_min_inr > 1500,
                Accommodation.price_min_inr <= 4000,
            )
        elif tier_lower == "premium":
            query = query.filter(Accommodation.price_min_inr > 4000)

    if max_price is not None:
        query = query.filter(
            Accommodation.price_min_inr.is_not(None),
            Accommodation.price_min_inr <= max_price,
        )

    stays = query.order_by(
        StayArea.city.asc(),
        Accommodation.price_min_inr.is_(None),
        Accommodation.price_min_inr.asc(),
        Accommodation.name.asc(),
    ).all()
    return {"count": len(stays), "accommodations": [_accommodation_payload(stay) for stay in stays]}
