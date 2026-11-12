"""Protected administration endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Destination, SavedDestination, Itinerary
from backend.auth import require_admin
from backend.recommend import get_recommender


router = APIRouter(tags=["Administration"])


@router.get(
    "/admin/stats",
    summary="Get application usage statistics and dataset metrics (Admin only)",
)
def get_admin_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return administrative metrics: user count, itinerary volume, dataset coverage."""
    total_users = db.query(User).count()
    total_itineraries = db.query(Itinerary).count()
    total_saved = db.query(SavedDestination).count()
    total_destinations = db.query(Destination).count()

    df = get_recommender().dataframe
    states_count = int(df["State"].nunique())
    types_count = int(df["Type"].nunique())

    return {
        "admin_user": admin.email,
        "users_count": total_users,
        "itineraries_count": total_itineraries,
        "saved_destinations_count": total_saved,
        "destinations_in_catalog": total_destinations,
        "unique_states_covered": states_count,
        "unique_attraction_types": types_count,
        "average_dataset_rating": round(float(df["Google review rating"].mean()), 2),
    }
