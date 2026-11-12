"""Pydantic request and response validation schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# -------------------------------------------------------------
# User & Authentication Schemas
# -------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password (at least 6 characters)")
    full_name: str = Field(..., min_length=2, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# -------------------------------------------------------------
# Destination Schemas
# -------------------------------------------------------------
class DestinationResponse(BaseModel):
    id: int
    name: str
    state: str
    city: str
    type: str
    establishment_year: Optional[str] = "Not specified"
    time_needed_hours: float = Field(alias="time needed to visit in hrs", default=2.0)
    rating: float = Field(alias="Google review rating", default=4.0)
    entrance_fee_inr: int = Field(alias="Entrance Fee in INR", default=0)
    airport_within_50km: Optional[str] = Field(alias="Airport with 50km Radius", default="No")
    weekly_off: Optional[str] = Field(alias="Weekly Off", default="Not specified")
    significance: Optional[str] = Field(alias="Significance", default="Historical")
    dslr_allowed: Optional[str] = Field(alias="DSLR Allowed", default="Yes")
    reviews_lakhs: Optional[float] = Field(alias="Number of google review in lakhs", default=0.1)
    best_time: Optional[str] = Field(alias="Best Time to visit", default="All")
    zone: Optional[str] = Field(alias="Zone", default="Northern")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DestinationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    destinations: List[Dict[str, Any]]


# -------------------------------------------------------------
# Recommendation Schemas
# -------------------------------------------------------------
class RecommendationResponse(BaseModel):
    count: int
    recommendations: List[Dict[str, Any]]
    error: Optional[str] = None


# -------------------------------------------------------------
# Saved Destination Schemas
# -------------------------------------------------------------
class SavedDestinationCreate(BaseModel):
    destination_id: int
    notes: Optional[str] = None


class SavedDestinationResponse(BaseModel):
    id: int
    user_id: int
    destination_id: int
    notes: Optional[str] = None
    created_at: datetime
    destination: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Itinerary Schemas
# -------------------------------------------------------------
class ItineraryActivityCreate(BaseModel):
    destination_id: int
    order_index: int = 0
    time_slot: str = "Morning"  # 'Morning', 'Afternoon', 'Evening'
    planned_hours: float = 2.0
    notes: Optional[str] = None


class ItineraryActivityResponse(BaseModel):
    id: int
    itinerary_day_id: int
    destination_id: int
    order_index: int
    time_slot: str
    planned_hours: float
    notes: Optional[str] = None
    destination: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ItineraryDayCreate(BaseModel):
    day_number: int
    notes: Optional[str] = None
    activities: List[ItineraryActivityCreate] = []


class ItineraryDayResponse(BaseModel):
    id: int
    itinerary_id: int
    day_number: int
    notes: Optional[str] = None
    activities: List[ItineraryActivityResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ItineraryStayPlan(BaseModel):
    accommodation_id: int
    nights: int = Field(default=1, ge=1, le=60)


class ItineraryFoodPlan(BaseModel):
    plan_mode: str = "daily_budget"  # 'daily_budget', 'custom_daily', 'selected_options', 'none'
    daily_budget_per_person: Optional[float] = None
    travelers_count: Optional[int] = Field(default=1, ge=1, le=50)
    selected_option_ids: Optional[List[int]] = None
    notes: Optional[str] = None


class ItineraryCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: float = 0.0
    travelers_count: Optional[int] = Field(default=1, ge=1, le=50)
    days: List[ItineraryDayCreate] = []
    accommodation: Optional[ItineraryStayPlan] = None
    food: Optional[ItineraryFoodPlan] = None


class ItineraryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: Optional[float] = None
    travelers_count: Optional[int] = Field(default=None, ge=1, le=50)
    days: Optional[List[ItineraryDayCreate]] = None
    accommodation: Optional[ItineraryStayPlan] = None
    food: Optional[ItineraryFoodPlan] = None


class ItineraryResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: float
    travelers_count: int = 1
    days_count: Optional[int] = None
    estimated_entrance_fee: float
    estimated_accommodation_min: Optional[float] = None
    estimated_accommodation_max: Optional[float] = None
    estimated_food_cost: Optional[float] = 0.0
    estimated_total_min: Optional[float] = None
    estimated_total_max: Optional[float] = None
    accommodation: Optional[Dict[str, Any]] = None
    food: Optional[Dict[str, Any]] = None
    cost_breakdown: Optional[Dict[str, Any]] = None
    budget_exceeded: Optional[bool] = False
    created_at: datetime
    updated_at: datetime
    days: List[ItineraryDayResponse] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Food Option Schemas
# -------------------------------------------------------------
class FoodOptionResponse(BaseModel):
    id: int
    city: str
    state: str
    name: str
    area: Optional[str] = None
    cuisine: Optional[str] = None
    meal_type: Optional[str] = None
    price_tier: str
    estimated_cost_inr: int
    description: Optional[str] = None
    source_url: Optional[str] = None
    is_budget_friendly: bool

    model_config = ConfigDict(from_attributes=True)


class FoodOptionListResponse(BaseModel):
    count: int
    food_options: List[FoodOptionResponse]


class FoodPresetResponse(BaseModel):
    id: str
    name: str
    daily_per_person_inr: int
    description: str
    tier: str


# -------------------------------------------------------------
# Weather & AI Assistant Schemas
# -------------------------------------------------------------
class WeatherResponse(BaseModel):
    city: str
    state: Optional[str] = None
    temp_c: Optional[float] = None
    condition: str
    humidity: Optional[int] = None
    wind_kph: Optional[float] = None
    best_visiting_period: str
    is_live: bool = False
    note: str


class AssistantMessage(BaseModel):
    query: str = Field(..., min_length=2)


class AssistantResponse(BaseModel):
    query: str
    answer: str
    suggested_destinations: List[Dict[str, Any]] = []
    source: str = "dataset-knowledge"
