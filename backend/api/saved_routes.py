"""User saved destinations endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Destination, SavedDestination
from backend.schemas import SavedDestinationCreate, SavedDestinationResponse
from backend.auth import get_current_user


router = APIRouter(tags=["Saved Destinations"])


@router.get(
    "/users/me/saved-destinations",
    summary="List all destinations saved by the authenticated user",
)
def list_saved_destinations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all destinations saved by current user."""
    saved_items = (
        db.query(SavedDestination)
        .filter(SavedDestination.user_id == current_user.id)
        .order_by(SavedDestination.created_at.desc())
        .all()
    )

    results = []
    for item in saved_items:
        dest = item.destination
        results.append(
            {
                "id": item.id,
                "user_id": item.user_id,
                "destination_id": item.destination_id,
                "notes": item.notes,
                "created_at": item.created_at,
                "destination": {
                    "id": dest.id,
                    "Name": dest.name,
                    "State": dest.state,
                    "City": dest.city,
                    "Type": dest.type,
                    "Google review rating": dest.rating,
                    "Entrance Fee in INR": dest.entrance_fee_inr,
                    "time needed to visit in hrs": dest.time_needed_hours,
                    "Best Time to visit": dest.best_time,
                }
                if dest
                else None,
            }
        )

    return {"count": len(results), "saved_destinations": results}


@router.post(
    "/users/me/saved-destinations",
    status_code=status.HTTP_201_CREATED,
    summary="Save a destination to user's favorites",
)
def save_destination(
    save_in: SavedDestinationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a destination to current user's profile."""
    # Check destination exists
    dest = (
        db.query(Destination)
        .filter(Destination.id == save_in.destination_id)
        .first()
    )
    if not dest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with ID {save_in.destination_id} not found.",
        )

    # Check for duplicate
    existing = (
        db.query(SavedDestination)
        .filter(
            SavedDestination.user_id == current_user.id,
            SavedDestination.destination_id == save_in.destination_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination is already in your saved list.",
        )

    saved_obj = SavedDestination(
        user_id=current_user.id,
        destination_id=save_in.destination_id,
        notes=save_in.notes,
    )
    db.add(saved_obj)
    db.commit()
    db.refresh(saved_obj)

    return {
        "message": "Destination saved successfully.",
        "saved_destination": {
            "id": saved_obj.id,
            "user_id": saved_obj.user_id,
            "destination_id": saved_obj.destination_id,
            "notes": saved_obj.notes,
            "created_at": saved_obj.created_at,
        },
    }


@router.delete(
    "/users/me/saved-destinations/{destination_id}",
    summary="Remove a destination from user's saved list",
)
def delete_saved_destination(
    destination_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a saved destination."""
    item = (
        db.query(SavedDestination)
        .filter(
            SavedDestination.user_id == current_user.id,
            SavedDestination.destination_id == destination_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved destination not found in your list.",
        )

    db.delete(item)
    db.commit()
    return {"message": "Destination removed from your saved list."}
