"""Travel itinerary management endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    User,
    Destination,
    Itinerary,
    ItineraryDay,
    ItineraryActivity,
    Accommodation,
    ItineraryStay,
    FoodOption,
    ItineraryFood,
)
from backend.schemas import ItineraryCreate, ItineraryUpdate
from backend.auth import get_current_user


router = APIRouter(tags=["Itineraries"])


def _serialize_itinerary(itinerary: Itinerary, db: Optional[Session] = None) -> Dict[str, Any]:
    days_data = []
    total_fees = 0.0

    for day in itinerary.days:
        activities_data = []
        for act in day.activities:
            dest = act.destination
            fee = dest.entrance_fee_inr if dest else 0
            total_fees += fee
            activities_data.append(
                {
                    "id": act.id,
                    "itinerary_day_id": act.itinerary_day_id,
                    "destination_id": act.destination_id,
                    "order_index": act.order_index,
                    "time_slot": act.time_slot,
                    "planned_hours": act.planned_hours,
                    "notes": act.notes,
                    "destination": {
                        "id": dest.id,
                        "Name": dest.name,
                        "State": dest.state,
                        "City": dest.city,
                        "Type": dest.type,
                        "Entrance Fee in INR": fee,
                        "time needed to visit in hrs": dest.time_needed_hours,
                        "Google review rating": dest.rating,
                        "Best Time to visit": dest.best_time,
                    }
                    if dest
                    else None,
                }
            )

        days_data.append(
            {
                "id": day.id,
                "itinerary_id": day.itinerary_id,
                "day_number": day.day_number,
                "notes": day.notes,
                "activities": activities_data,
            }
        )

    stay_data = None
    accommodation_min = None
    accommodation_max = None
    stay_plan = itinerary.accommodation_plan
    if stay_plan and stay_plan.accommodation:
        stay = stay_plan.accommodation
        if stay_plan.nightly_min_inr is not None:
            accommodation_min = float(stay_plan.nightly_min_inr * stay_plan.nights)
        if stay_plan.nightly_max_inr is not None:
            accommodation_max = float(stay_plan.nightly_max_inr * stay_plan.nights)
        stay_data = {
            "accommodation_id": stay.id,
            "name": stay.name,
            "property_type": stay.property_type,
            "city": stay.stay_area.city,
            "area": stay.stay_area.name,
            "nights": stay_plan.nights,
            "nightly_min_inr": stay_plan.nightly_min_inr,
            "nightly_max_inr": stay_plan.nightly_max_inr,
            "estimated_min_inr": accommodation_min,
            "estimated_max_inr": accommodation_max,
        }

    # Food planning calculation
    days_count = max(1, len(itinerary.days))
    travelers_count = max(1, getattr(itinerary, "travelers_count", 1) or 1)
    food_data = None
    estimated_food_cost = 0.0

    food_plan = getattr(itinerary, "food_plan", None)
    if food_plan and food_plan.plan_mode != "none":
        plan_mode = food_plan.plan_mode
        food_travelers = food_plan.travelers_count or travelers_count
        daily_rate = food_plan.daily_budget_per_person or 0.0
        selected_options_list = []

        if plan_mode in ("daily_budget", "custom_daily"):
            estimated_food_cost = float(round(daily_rate * food_travelers * days_count, 2))
            calc_text = f"₹{int(daily_rate):,}/person/day × {food_travelers} traveler(s) × {days_count} day(s)"
        elif plan_mode == "selected_options" and food_plan.selected_option_ids:
            try:
                opt_ids = [int(x.strip()) for x in food_plan.selected_option_ids.split(",") if x.strip()]
            except ValueError:
                opt_ids = []
            selected_items = []
            if opt_ids and db:
                selected_items = db.query(FoodOption).filter(FoodOption.id.in_(opt_ids)).all()
                selected_options_list = [
                    {
                        "id": f.id,
                        "name": f.name,
                        "city": f.city,
                        "cuisine": f.cuisine,
                        "price_tier": f.price_tier,
                        "estimated_cost_inr": f.estimated_cost_inr,
                    }
                    for f in selected_items
                ]
            item_sum = sum(f.estimated_cost_inr for f in selected_items)
            estimated_food_cost = float(round(item_sum * food_travelers, 2))
            calc_text = f"Selected options total ₹{int(item_sum):,}/person × {food_travelers} traveler(s)"
        else:
            estimated_food_cost = 0.0
            calc_text = "Food planning skipped"

        food_data = {
            "plan_mode": plan_mode,
            "travelers_count": food_travelers,
            "daily_budget_per_person": daily_rate,
            "estimated_cost_inr": estimated_food_cost,
            "calculation_explanation": calc_text,
            "selected_options": selected_options_list,
            "notes": food_plan.notes,
        }

    # Combined totals
    base_cost = total_fees + estimated_food_cost

    if stay_data is not None:
        estimated_total_min = (base_cost + accommodation_min) if accommodation_min is not None else base_cost
        estimated_total_max = (
            (base_cost + accommodation_max)
            if accommodation_max is not None
            else ((base_cost + accommodation_min) if accommodation_min is not None else base_cost)
        )
    else:
        estimated_total_min = base_cost
        estimated_total_max = base_cost

    budget_warning = False
    if itinerary.total_budget and itinerary.total_budget > 0:
        if estimated_total_min is not None and estimated_total_min > itinerary.total_budget:
            budget_warning = True
        elif estimated_total_max is not None and estimated_total_max > itinerary.total_budget:
            budget_warning = True

    cost_breakdown = {
        "entrance_fees": total_fees,
        "accommodation_min": accommodation_min,
        "accommodation_max": accommodation_max,
        "food": estimated_food_cost,
        "total_min": estimated_total_min,
        "total_max": estimated_total_max,
        "total_budget": itinerary.total_budget,
        "travelers_count": travelers_count,
        "days_count": days_count,
    }

    return {
        "id": itinerary.id,
        "user_id": itinerary.user_id,
        "title": itinerary.title,
        "description": itinerary.description,
        "start_date": itinerary.start_date,
        "end_date": itinerary.end_date,
        "total_budget": itinerary.total_budget,
        "travelers_count": travelers_count,
        "days_count": days_count,
        "estimated_entrance_fee": total_fees,
        "estimated_accommodation_min": accommodation_min,
        "estimated_accommodation_max": accommodation_max,
        "estimated_food_cost": estimated_food_cost,
        "estimated_total_min": estimated_total_min,
        "estimated_total_max": estimated_total_max,
        "accommodation": stay_data,
        "food": food_data,
        "cost_breakdown": cost_breakdown,
        "budget_exceeded": budget_warning,
        "created_at": itinerary.created_at,
        "updated_at": itinerary.updated_at,
        "days": days_data,
    }


def _set_itinerary_accommodation(db: Session, itinerary: Itinerary, stay_plan):
    if stay_plan is None:
        if itinerary.accommodation_plan is not None:
            db.delete(itinerary.accommodation_plan)
        return

    accommodation = (
        db.query(Accommodation)
        .filter(Accommodation.id == stay_plan.accommodation_id)
        .first()
    )
    if accommodation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation listing not found.",
        )

    plan = itinerary.accommodation_plan
    if plan is None:
        plan = ItineraryStay(itinerary_id=itinerary.id)
    plan.accommodation_id = accommodation.id
    plan.nights = stay_plan.nights
    # Store a tariff snapshot so later catalog edits do not silently alter a saved trip.
    plan.nightly_min_inr = accommodation.price_min_inr
    plan.nightly_max_inr = accommodation.price_max_inr
    db.add(plan)


def _set_itinerary_food(db: Session, itinerary: Itinerary, food_in):
    if food_in is None or food_in.plan_mode == "none":
        if itinerary.food_plan is not None:
            db.delete(itinerary.food_plan)
        return

    food_plan = itinerary.food_plan
    if food_plan is None:
        food_plan = ItineraryFood(itinerary_id=itinerary.id)

    food_plan.plan_mode = food_in.plan_mode
    food_plan.daily_budget_per_person = food_in.daily_budget_per_person
    food_plan.travelers_count = food_in.travelers_count or itinerary.travelers_count or 1
    food_plan.notes = food_in.notes

    if food_in.selected_option_ids:
        food_plan.selected_option_ids = ",".join(str(x) for x in food_in.selected_option_ids)
    else:
        food_plan.selected_option_ids = None

    db.add(food_plan)


@router.post(
    "/itineraries",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trip itinerary with activities, accommodation, and food planning",
)
def create_itinerary(
    itin_in: ItineraryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a structured itinerary organized into days, destination activities, stay, and food."""
    travelers = itin_in.travelers_count or 1
    new_itin = Itinerary(
        user_id=current_user.id,
        title=itin_in.title,
        description=itin_in.description,
        start_date=itin_in.start_date,
        end_date=itin_in.end_date,
        total_budget=itin_in.total_budget,
        travelers_count=travelers,
        estimated_entrance_fee=0.0,
    )
    db.add(new_itin)
    db.flush()

    if itin_in.accommodation is not None:
        _set_itinerary_accommodation(db, new_itin, itin_in.accommodation)

    if itin_in.food is not None:
        _set_itinerary_food(db, new_itin, itin_in.food)

    total_fees = 0.0

    for day_in in itin_in.days:
        day_obj = ItineraryDay(
            itinerary_id=new_itin.id,
            day_number=day_in.day_number,
            notes=day_in.notes,
        )
        db.add(day_obj)
        db.flush()

        for act_in in day_in.activities:
            dest = (
                db.query(Destination)
                .filter(Destination.id == act_in.destination_id)
                .first()
            )
            if dest:
                total_fees += dest.entrance_fee_inr

            act_obj = ItineraryActivity(
                itinerary_day_id=day_obj.id,
                destination_id=act_in.destination_id,
                order_index=act_in.order_index,
                time_slot=act_in.time_slot,
                planned_hours=act_in.planned_hours,
                notes=act_in.notes,
            )
            db.add(act_obj)

    new_itin.estimated_entrance_fee = total_fees
    db.commit()
    db.refresh(new_itin)

    return _serialize_itinerary(new_itin, db=db)


@router.get(
    "/itineraries",
    summary="List all itineraries created by the authenticated user",
)
def list_itineraries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all itineraries belonging to current user."""
    itins = (
        db.query(Itinerary)
        .filter(Itinerary.user_id == current_user.id)
        .order_by(Itinerary.created_at.desc())
        .all()
    )
    return {
        "count": len(itins),
        "itineraries": [_serialize_itinerary(it, db=db) for it in itins],
    }


@router.get(
    "/itineraries/{itinerary_id}",
    summary="Get full details for a specific itinerary",
)
def get_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve an itinerary by ID (restricted to owner)."""
    itin = (
        db.query(Itinerary)
        .filter(
            Itinerary.id == itinerary_id,
            Itinerary.user_id == current_user.id,
        )
        .first()
    )
    if not itin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found or access denied.",
        )
    return _serialize_itinerary(itin, db=db)


@router.put(
    "/itineraries/{itinerary_id}",
    summary="Update an existing itinerary",
)
def update_itinerary(
    itinerary_id: int,
    itin_in: ItineraryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update itinerary title, budget, travelers, stay, food, dates, and activities."""
    itin = (
        db.query(Itinerary)
        .filter(
            Itinerary.id == itinerary_id,
            Itinerary.user_id == current_user.id,
        )
        .first()
    )
    if not itin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found or access denied.",
        )

    if itin_in.title is not None:
        itin.title = itin_in.title
    if itin_in.description is not None:
        itin.description = itin_in.description
    if itin_in.start_date is not None:
        itin.start_date = itin_in.start_date
    if itin_in.end_date is not None:
        itin.end_date = itin_in.end_date
    if itin_in.total_budget is not None:
        itin.total_budget = itin_in.total_budget
    if itin_in.travelers_count is not None:
        itin.travelers_count = itin_in.travelers_count

    if "accommodation" in itin_in.model_fields_set:
        _set_itinerary_accommodation(db, itin, itin_in.accommodation)

    if "food" in itin_in.model_fields_set:
        _set_itinerary_food(db, itin, itin_in.food)

    if itin_in.days is not None:
        for old_day in list(itin.days):
            db.delete(old_day)
        db.flush()

        total_fees = 0.0
        for day_in in itin_in.days:
            day_obj = ItineraryDay(
                itinerary_id=itin.id,
                day_number=day_in.day_number,
                notes=day_in.notes,
            )
            db.add(day_obj)
            db.flush()

            for act_in in day_in.activities:
                dest = (
                    db.query(Destination)
                    .filter(Destination.id == act_in.destination_id)
                    .first()
                )
                if dest:
                    total_fees += dest.entrance_fee_inr

                act_obj = ItineraryActivity(
                    itinerary_day_id=day_obj.id,
                    destination_id=act_in.destination_id,
                    order_index=act_in.order_index,
                    time_slot=act_in.time_slot,
                    planned_hours=act_in.planned_hours,
                    notes=act_in.notes,
                )
                db.add(act_obj)

        itin.estimated_entrance_fee = total_fees

    db.commit()
    db.refresh(itin)
    return _serialize_itinerary(itin, db=db)


@router.delete(
    "/itineraries/{itinerary_id}",
    summary="Delete an itinerary",
)
def delete_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an itinerary."""
    itin = (
        db.query(Itinerary)
        .filter(
            Itinerary.id == itinerary_id,
            Itinerary.user_id == current_user.id,
        )
        .first()
    )
    if not itin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found or access denied.",
        )

    db.delete(itin)
    db.commit()
    return {"message": "Itinerary deleted successfully."}
