"""Destination catalog, lookup, and recommendation endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Destination
from backend.schemas import DestinationListResponse, RecommendationResponse
from backend.recommend import get_recommender, recommend_destinations


router = APIRouter(tags=["Destinations & Recommendations"])


@router.get(
    "/destinations",
    response_model=DestinationListResponse,
    summary="List destinations with search, filter, and pagination",
)
def list_destinations(
    state: Optional[str] = Query(default=None, description="Filter by state name"),
    city: Optional[str] = Query(default=None, description="Filter by city name"),
    type: Optional[str] = Query(default=None, description="Filter by attraction type"),
    search: Optional[str] = Query(default=None, description="Search destination name"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve paginated destinations from the database."""
    query = db.query(Destination)

    if state and state.strip():
        query = query.filter(Destination.state.ilike(f"%{state.strip()}%"))
    if city and city.strip():
        query = query.filter(Destination.city.ilike(f"%{city.strip()}%"))
    if type and type.strip():
        query = query.filter(Destination.type.ilike(f"%{type.strip()}%"))
    if search and search.strip():
        query = query.filter(Destination.name.ilike(f"%{search.strip()}%"))

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Destination.name.asc()).offset(offset).limit(page_size).all()

    destinations = [
        {
            "id": d.id,
            "Name": d.name,
            "State": d.state,
            "City": d.city,
            "Type": d.type,
            "Establishment Year": d.establishment_year,
            "time needed to visit in hrs": d.time_needed_hours,
            "Google review rating": d.rating,
            "Entrance Fee in INR": d.entrance_fee_inr,
            "Airport with 50km Radius": d.airport_within_50km,
            "Weekly Off": d.weekly_off,
            "Significance": d.significance,
            "DSLR Allowed": d.dslr_allowed,
            "Number of google review in lakhs": d.reviews_lakhs,
            "Best Time to visit": d.best_time,
            "Zone": d.zone,
        }
        for d in items
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "destinations": destinations,
    }


@router.get(
    "/destinations/{destination_id}",
    summary="Get single destination details by ID",
)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed information for a specific destination."""
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with ID {destination_id} not found.",
        )

    return {
        "id": destination.id,
        "Name": destination.name,
        "State": destination.state,
        "City": destination.city,
        "Type": destination.type,
        "Establishment Year": destination.establishment_year,
        "time needed to visit in hrs": destination.time_needed_hours,
        "Google review rating": destination.rating,
        "Entrance Fee in INR": destination.entrance_fee_inr,
        "Airport with 50km Radius": destination.airport_within_50km,
        "Weekly Off": destination.weekly_off,
        "Significance": destination.significance,
        "DSLR Allowed": destination.dslr_allowed,
        "Number of google review in lakhs": destination.reviews_lakhs,
        "Best Time to visit": destination.best_time,
        "Zone": destination.zone,
    }


@router.get(
    "/states",
    summary="List all unique available states",
)
def list_states():
    """Return all unique states from the verified tourism dataset."""
    df = get_recommender().dataframe
    states = sorted(df["State"].dropna().unique().tolist())
    return {"count": len(states), "states": states}


@router.get(
    "/destination-types",
    summary="List all unique attraction types",
)
def list_destination_types():
    """Return all unique attraction types from the dataset."""
    df = get_recommender().dataframe
    types = sorted(df["Type"].dropna().unique().tolist())
    return {"count": len(types), "types": types}


@router.get(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Personalized tourism recommendations via TF-IDF content similarity",
)
def recommend(
    state: Optional[str] = Query(default=None, description="Preferred state filter"),
    city: Optional[str] = Query(default=None, description="Preferred city filter"),
    type: Optional[str] = Query(default=None, description="Attraction type filter"),
    interests: Optional[str] = Query(
        default=None, description="Comma-separated interest keywords (e.g. historical, temple)"
    ),
    best_time: Optional[str] = Query(default=None, description="Visiting period (Morning/Afternoon/Evening)"),
    budget: float = Query(default=1000.0, ge=0, description="Max entrance fee in INR"),
    available_hours: float = Query(default=8.0, gt=0, description="Available visiting hours"),
    min_rating: Optional[float] = Query(default=None, ge=1.0, le=5.0, description="Minimum rating"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of recommendations"),
):
    """Compute personalized recommendations based on TF-IDF content similarity and user constraints."""
    try:
        interest_list = [
            item.strip()
            for item in (interests or "").split(",")
            if item.strip()
        ]

        results = recommend_destinations(
            state=state,
            city=city,
            type=type,
            interests=interest_list,
            budget=budget,
            available_hours=available_hours,
            preferred_time=best_time,
            min_rating=min_rating,
            top_n=limit,
        )

        if results.empty:
            return {"count": 0, "recommendations": []}

        # Keep both 'Recommendation Score' and 'Personalization Score' for frontend compatibility
        recommendations = results.fillna("").to_dict(orient="records")
        return {
            "count": len(recommendations),
            "recommendations": recommendations,
        }

    except Exception as exc:
        return {
            "count": 0,
            "recommendations": [],
            "error": str(exc),
        }
