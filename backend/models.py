"""SQLAlchemy ORM models for Users, Destinations, Saved Trips, and Itineraries."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import relationship
from backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)  # 'user' or 'admin'
    created_at = Column(DateTime, default=utc_now, nullable=False)

    saved_destinations = relationship(
        "SavedDestination", back_populates="user", cascade="all, delete-orphan"
    )
    itineraries = relationship(
        "Itinerary", back_populates="user", cascade="all, delete-orphan"
    )


class Destination(Base):
    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    type = Column(String(100), nullable=False, index=True)
    establishment_year = Column(String(50), default="Not specified")
    time_needed_hours = Column(Float, default=2.0)
    rating = Column(Float, default=4.0)
    entrance_fee_inr = Column(Integer, default=0)
    airport_within_50km = Column(String(10), default="No")
    weekly_off = Column(String(50), default="Not specified")
    significance = Column(String(100), default="Historical")
    dslr_allowed = Column(String(10), default="Yes")
    reviews_lakhs = Column(Float, default=0.1)
    best_time = Column(String(50), default="All")
    zone = Column(String(50), default="Northern")

    saved_by = relationship("SavedDestination", back_populates="destination")
    activities = relationship("ItineraryActivity", back_populates="destination")


class StayArea(Base):
    """Curated neighborhoods and localities suggested as bases for a trip."""

    __tablename__ = "stay_areas"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    nearby_attractions = Column(Text, nullable=True)
    budget_category = Column(String(50), default="Mixed", nullable=False)
    source_url = Column(String(500), nullable=True)

    accommodations = relationship("Accommodation", back_populates="stay_area")


class Accommodation(Base):
    """A sourced accommodation listing with an indicative nightly tariff."""

    __tablename__ = "accommodations"

    id = Column(Integer, primary_key=True, index=True)
    stay_area_id = Column(Integer, ForeignKey("stay_areas.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    property_type = Column(String(80), nullable=False, default="Hotel")
    address = Column(String(500), nullable=True)
    price_min_inr = Column(Integer, nullable=True)
    price_max_inr = Column(Integer, nullable=True)
    amenities = Column(Text, nullable=True)
    website_url = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=False)
    price_note = Column(String(500), nullable=True)

    stay_area = relationship("StayArea", back_populates="accommodations")
    itinerary_stays = relationship("ItineraryStay", back_populates="accommodation")


class FoodOption(Base):
    """Sourced food options and dining spots with indicative costs."""

    __tablename__ = "food_options"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    area = Column(String(150), nullable=True)
    cuisine = Column(String(100), nullable=True)
    meal_type = Column(String(100), nullable=True)
    price_tier = Column(String(50), default="Budget", nullable=False)  # 'Budget', 'Standard', 'Premium'
    estimated_cost_inr = Column(Integer, nullable=False, default=200)  # Indicative per-person cost
    description = Column(Text, nullable=True)
    source_url = Column(String(500), nullable=True)
    is_budget_friendly = Column(Integer, default=1, nullable=False)  # 1 for True, 0 for False


class SavedDestination(Base):
    __tablename__ = "saved_destinations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    destination_id = Column(
        Integer, ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "destination_id", name="uq_user_destination"),
    )

    user = relationship("User", back_populates="saved_destinations")
    destination = relationship("Destination", back_populates="saved_by")


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    total_budget = Column(Float, default=0.0)
    estimated_entrance_fee = Column(Float, default=0.0)
    travelers_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", back_populates="itineraries")
    days = relationship(
        "ItineraryDay",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryDay.day_number",
    )
    accommodation_plan = relationship(
        "ItineraryStay",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        uselist=False,
    )
    food_plan = relationship(
        "ItineraryFood",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ItineraryDay(Base):
    __tablename__ = "itinerary_days"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(
        Integer, ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False
    )
    day_number = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)

    itinerary = relationship("Itinerary", back_populates="days")
    activities = relationship(
        "ItineraryActivity",
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="ItineraryActivity.order_index",
    )


class ItineraryActivity(Base):
    __tablename__ = "itinerary_activities"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_day_id = Column(
        Integer, ForeignKey("itinerary_days.id", ondelete="CASCADE"), nullable=False
    )
    destination_id = Column(
        Integer, ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False
    )
    order_index = Column(Integer, default=0)
    time_slot = Column(String(50), default="Morning")  # 'Morning', 'Afternoon', 'Evening'
    planned_hours = Column(Float, default=2.0)
    notes = Column(Text, nullable=True)

    day = relationship("ItineraryDay", back_populates="activities")
    destination = relationship("Destination", back_populates="activities")


class ItineraryStay(Base):
    """One selected stay and its saved price estimate for an itinerary."""

    __tablename__ = "itinerary_stays"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(
        Integer, ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    accommodation_id = Column(
        Integer, ForeignKey("accommodations.id"), nullable=False, index=True
    )
    nights = Column(Integer, nullable=False, default=1)
    nightly_min_inr = Column(Integer, nullable=True)
    nightly_max_inr = Column(Integer, nullable=True)

    itinerary = relationship("Itinerary", back_populates="accommodation_plan")
    accommodation = relationship("Accommodation", back_populates="itinerary_stays")


class ItineraryFood(Base):
    """Optional food-planning choice and cost estimate for an itinerary."""

    __tablename__ = "itinerary_foods"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(
        Integer,
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    plan_mode = Column(String(50), default="none", nullable=False)  # 'none', 'daily_budget', 'custom_daily', 'selected_options'
    daily_budget_per_person = Column(Float, nullable=True)
    travelers_count = Column(Integer, default=1, nullable=False)
    selected_option_ids = Column(Text, nullable=True)  # Comma-separated food_option IDs
    notes = Column(Text, nullable=True)

    itinerary = relationship("Itinerary", back_populates="food_plan")
