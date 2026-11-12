"""Test fixtures and client setup."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.recommend import get_recommender
from backend.main import (
    app,
    seed_destinations_if_empty,
    seed_stays_if_empty,
    seed_food_if_empty,
)


TEST_DATABASE_URL = "sqlite:///./test_tourism.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test tables and seed destinations once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    # Seed and synchronize destinations, stays, and food into test db
    get_recommender(force_reload=True)
    seed_destinations_if_empty(session_factory=TestingSessionLocal)
    seed_stays_if_empty(session_factory=TestingSessionLocal)
    seed_food_if_empty(session_factory=TestingSessionLocal)

    app.dependency_overrides[get_db] = override_get_db
    yield
    # Cleanup test db
    Base.metadata.drop_all(bind=test_engine)
    import os
    if os.path.exists("./test_tourism.db"):
        try:
            os.remove("./test_tourism.db")
        except Exception:
            pass


@pytest.fixture
def client():
    """TestClient instance."""
    with TestClient(app) as c:
        yield c
