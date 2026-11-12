"""Main FastAPI application entry point.

Initializes the database schema, pre-seeds destinations from verified CSV,
configures CORS, mounts modular API routes, and serves health checks.
"""

from contextlib import asynccontextmanager
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.config import settings
from backend.database import engine, Base, SessionLocal
from backend.models import Accommodation, Destination, FoodOption, StayArea
from backend.recommend import get_recommender
from backend.api import (
    auth_routes,
    destination_routes,
    saved_routes,
    itinerary_routes,
    assistant_routes,
    admin_routes,
    stay_routes,
    food_routes,
)


def run_db_migrations():
    """Run lightweight schema updates for existing SQLite installations."""
    try:
        with engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(itineraries)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "travelers_count" not in cols:
                conn.execute(text("ALTER TABLE itineraries ADD COLUMN travelers_count INTEGER DEFAULT 1 NOT NULL"))
                conn.commit()
                print("[Startup] Migrated itineraries table: added travelers_count column.")
    except Exception as exc:
        print(f"[Startup] Migration check notice: {exc}")


def seed_destinations_if_empty(session_factory=SessionLocal):
    """Populate or synchronize database Destination table from cleaned_tourism.csv."""
    db = session_factory()
    try:
        csv_path = Path(__file__).resolve().parent.parent / "data" / "cleaned_tourism.csv"
        if not csv_path.exists():
            return
        df = pd.read_csv(csv_path)

        count = db.query(Destination).count()
        if count == 0:
            records = []
            for _, row in df.iterrows():
                d = Destination(
                    id=int(row["id"]) if "id" in row and pd.notna(row["id"]) else None,
                    name=str(row.get("Name", "")).strip(),
                    state=str(row.get("State", "")).strip(),
                    city=str(row.get("City", "")).strip(),
                    type=str(row.get("Type", "")).strip(),
                    establishment_year=str(row.get("Establishment Year", "Not specified")).strip(),
                    time_needed_hours=float(row.get("time needed to visit in hrs", 2.0)),
                    rating=float(row.get("Google review rating", 4.0)),
                    entrance_fee_inr=int(row.get("Entrance Fee in INR", 0)),
                    airport_within_50km=str(row.get("Airport with 50km Radius", "No")).strip(),
                    weekly_off=str(row.get("Weekly Off", "Not specified")).strip(),
                    significance=str(row.get("Significance", "Historical")).strip(),
                    dslr_allowed=str(row.get("DSLR Allowed", "Yes")).strip(),
                    reviews_lakhs=float(row.get("Number of google review in lakhs", 0.1)),
                    best_time=str(row.get("Best Time to visit", "All")).strip(),
                    zone=str(row.get("Zone", "Northern")).strip(),
                )
                records.append(d)
            db.bulk_save_objects(records)
            db.commit()
            print(f"[Startup] Pre-seeded {len(records)} destinations into database.")
        else:
            # Safely synchronize missing destinations and update updated attributes
            existing_destinations = {
                (d.name.strip().casefold(), d.city.strip().casefold(), d.state.strip().casefold()): d
                for d in db.query(Destination).all()
            }
            existing_ids = {d.id for d in existing_destinations.values()}
            added = 0
            updated = 0
            for _, row in df.iterrows():
                name = str(row.get("Name", "")).strip()
                city = str(row.get("City", "")).strip()
                state = str(row.get("State", "")).strip()
                key = (name.casefold(), city.casefold(), state.casefold())
                new_fee = int(row.get("Entrance Fee in INR", 0))

                if key not in existing_destinations:
                    rec_id = int(row["id"]) if "id" in row and pd.notna(row["id"]) else None
                    if rec_id in existing_ids:
                        rec_id = None
                    d = Destination(
                        id=rec_id,
                        name=name,
                        state=state,
                        city=city,
                        type=str(row.get("Type", "")).strip(),
                        establishment_year=str(row.get("Establishment Year", "Not specified")).strip(),
                        time_needed_hours=float(row.get("time needed to visit in hrs", 2.0)),
                        rating=float(row.get("Google review rating", 4.0)),
                        entrance_fee_inr=new_fee,
                        airport_within_50km=str(row.get("Airport with 50km Radius", "No")).strip(),
                        weekly_off=str(row.get("Weekly Off", "Not specified")).strip(),
                        significance=str(row.get("Significance", "Historical")).strip(),
                        dslr_allowed=str(row.get("DSLR Allowed", "Yes")).strip(),
                        reviews_lakhs=float(row.get("Number of google review in lakhs", 0.1)),
                        best_time=str(row.get("Best Time to visit", "All")).strip(),
                        zone=str(row.get("Zone", "Northern")).strip(),
                    )
                    db.add(d)
                    existing_destinations[key] = d
                    if rec_id:
                        existing_ids.add(rec_id)
                    added += 1
                else:
                    existing_dest = existing_destinations[key]
                    if existing_dest.entrance_fee_inr != new_fee:
                        existing_dest.entrance_fee_inr = new_fee
                        updated += 1
            if added > 0 or updated > 0:
                db.commit()
                print(f"[Startup] Synchronized destinations ({added} added, {updated} updated).")
    except Exception as exc:
        db.rollback()
        print(f"[Startup] Error seeding destinations: {exc}")
    finally:
        db.close()


def seed_stays_if_empty(session_factory=SessionLocal):
    """Load and synchronize the sourced stay-area and accommodation starter catalogs."""
    db = session_factory()
    data_dir = Path(__file__).resolve().parent.parent / "data"
    try:
        areas_path = data_dir / "stay_areas.csv"
        if areas_path.exists():
            areas_df = pd.read_csv(areas_path).fillna("")
            existing_areas = {
                (a.city.strip().casefold(), a.name.strip().casefold())
                for a in db.query(StayArea).all()
            }
            new_areas = 0
            for row in areas_df.to_dict(orient="records"):
                city = str(row["city"]).strip()
                name = str(row["name"]).strip()
                if (city.casefold(), name.casefold()) not in existing_areas:
                    db.add(
                        StayArea(
                            city=city,
                            state=str(row["state"]).strip(),
                            name=name,
                            description=str(row["description"]).strip(),
                            nearby_attractions=str(row.get("nearby_attractions", "")).strip(),
                            budget_category=str(row.get("budget_category", "Mixed")).strip() or "Mixed",
                            source_url=str(row.get("source_url", "")).strip() or None,
                        )
                    )
                    new_areas += 1
            if new_areas > 0:
                db.commit()
                print(f"[Startup] Added {new_areas} new stay areas.")

        stays_path = data_dir / "accommodations.csv"
        if stays_path.exists():
            stays_df = pd.read_csv(stays_path).fillna("")
            area_lookup = {
                (area.city.casefold(), area.state.casefold(), area.name.casefold()): area.id
                for area in db.query(StayArea).all()
            }
            existing_stays = {
                (s.stay_area_id, s.name.strip().casefold())
                for s in db.query(Accommodation).all()
            }

            def optional_int(value):
                try:
                    s = str(value).strip()
                    return int(float(s)) if s and s.lower() != "nan" else None
                except (ValueError, TypeError):
                    return None

            new_stays = 0
            for row in stays_df.to_dict(orient="records"):
                area_id = area_lookup.get(
                    (
                        str(row["city"]).strip().casefold(),
                        str(row["state"]).strip().casefold(),
                        str(row["area_name"]).strip().casefold(),
                    )
                )
                if area_id is None:
                    continue

                stay_name = str(row["name"]).strip()
                if (area_id, stay_name.casefold()) not in existing_stays:
                    db.add(
                        Accommodation(
                            stay_area_id=area_id,
                            name=stay_name,
                            property_type=str(row.get("property_type", "Hotel")).strip() or "Hotel",
                            address=str(row.get("address", "")).strip() or None,
                            price_min_inr=optional_int(row.get("price_min_inr", "")),
                            price_max_inr=optional_int(row.get("price_max_inr", "")),
                            amenities=str(row.get("amenities", "")).strip() or None,
                            website_url=str(row.get("website_url", "")).strip() or None,
                            source_url=str(row["source_url"]).strip(),
                            price_note=str(row.get("price_note", "")).strip() or None,
                        )
                    )
                    new_stays += 1
            if new_stays > 0:
                db.commit()
                print(f"[Startup] Added {new_stays} new accommodation listings.")
    except Exception as exc:
        db.rollback()
        print(f"[Startup] Error seeding stay catalog: {exc}")
    finally:
        db.close()


def seed_food_if_empty(session_factory=SessionLocal):
    """Load curated food and dining options into the database."""
    db = session_factory()
    data_dir = Path(__file__).resolve().parent.parent / "data"
    food_path = data_dir / "food_options.csv"
    try:
        if food_path.exists():
            food_df = pd.read_csv(food_path).fillna("")
            existing_food = {
                (f.city.strip().casefold(), f.name.strip().casefold())
                for f in db.query(FoodOption).all()
            }
            new_food = 0
            for row in food_df.to_dict(orient="records"):
                city = str(row["city"]).strip()
                name = str(row["name"]).strip()
                if (city.casefold(), name.casefold()) not in existing_food:
                    try:
                        cost = int(float(str(row.get("estimated_cost_inr", 200)).strip()))
                    except (ValueError, TypeError):
                        cost = 200

                    try:
                        is_budget = int(float(str(row.get("is_budget_friendly", 1)).strip()))
                    except (ValueError, TypeError):
                        is_budget = 1

                    db.add(
                        FoodOption(
                            city=city,
                            state=str(row.get("state", "")).strip(),
                            name=name,
                            area=str(row.get("area", "")).strip() or None,
                            cuisine=str(row.get("cuisine", "")).strip() or None,
                            meal_type=str(row.get("meal_type", "")).strip() or None,
                            price_tier=str(row.get("price_tier", "Budget")).strip() or "Budget",
                            estimated_cost_inr=cost,
                            description=str(row.get("description", "")).strip() or None,
                            source_url=str(row.get("source_url", "")).strip() or None,
                            is_budget_friendly=is_budget,
                        )
                    )
                    new_food += 1
            if new_food > 0:
                db.commit()
                print(f"[Startup] Seeded {new_food} curated food options.")
    except Exception as exc:
        db.rollback()
        print(f"[Startup] Error seeding food catalog: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: runs on server startup and shutdown."""
    # 1. Create database tables
    Base.metadata.create_all(bind=engine)
    # 2. Run lightweight schema migrations for existing DBs
    run_db_migrations()
    # 3. Seed destinations
    seed_destinations_if_empty()
    # 4. Seed stay-area and accommodation catalog
    seed_stays_if_empty()
    # 5. Seed food options catalog
    seed_food_if_empty()
    # 6. Warm up the in-memory TF-IDF recommendation cache
    get_recommender()
    print("[Startup] AI Tourism Recommendation System initialized successfully.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="An AI-powered platform for personalized travel planning across India.",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project root and static paths
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"

# Mount static files if frontend directory exists
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

# Mount modular routers
app.include_router(auth_routes.router)
app.include_router(destination_routes.router)
app.include_router(saved_routes.router)
app.include_router(itinerary_routes.router)
app.include_router(assistant_routes.router)
app.include_router(admin_routes.router)
app.include_router(stay_routes.router)
app.include_router(food_routes.router)


@app.get("/", tags=["System"])
def home(request: Request):
    """Root endpoint: serves the web application UI for browsers, or API info for JSON clients."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        if INDEX_HTML.exists():
            return FileResponse(INDEX_HTML, media_type="text/html")
    return {
        "project": settings.PROJECT_NAME,
        "status": "Backend is running successfully",
        "version": settings.VERSION,
    }


@app.get("/app", tags=["System"], response_class=FileResponse)
def web_app():
    """Direct route to access the web application interface."""
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML, media_type="text/html")
    return JSONResponse(status_code=404, content={"detail": "Frontend UI file not found"})


@app.get("/index.html", tags=["System"], include_in_schema=False)
def index_html_page():
    """Direct route for index.html."""
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML, media_type="text/html")
    return JSONResponse(status_code=404, content={"detail": "Frontend UI file not found"})


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
