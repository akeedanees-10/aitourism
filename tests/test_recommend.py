"""Unit tests for the personalized tourism recommendation engine."""

import pytest
from backend.recommend import get_recommender, recommend_destinations


def test_recommender_initialization():
    rec = get_recommender()
    df = rec.dataframe
    assert not df.empty
    assert len(df) >= 300
    assert "Name" in df.columns
    assert "Google review rating" in df.columns
    assert "Entrance Fee in INR" in df.columns
    assert "id" in df.columns


def test_recommend_returns_results_and_valid_scores():
    results = recommend_destinations(
        state="Delhi",
        budget=500,
        available_hours=8,
        top_n=5,
    )
    assert not results.empty
    assert len(results) <= 5

    for _, row in results.iterrows():
        # Score bounds check
        score = row["Recommendation Score"]
        assert 0.0 <= score <= 100.0
        # Check required fields
        assert "Name" in row
        assert "Type" in row
        assert "Explanation" in row
        assert len(row["Explanation"]) > 0


def test_budget_constraint_enforced():
    budget_limit = 50.0
    results = recommend_destinations(
        budget=budget_limit,
        available_hours=12,
        top_n=20,
    )
    assert not results.empty
    for _, row in results.iterrows():
        assert row["Entrance Fee in INR"] <= budget_limit


def test_duration_constraint_enforced():
    max_hours = 2.0
    results = recommend_destinations(
        budget=1000,
        available_hours=max_hours,
        top_n=20,
    )
    assert not results.empty
    for _, row in results.iterrows():
        assert row["time needed to visit in hrs"] <= max_hours


def test_state_filtering():
    target_state = "Kerala"
    results = recommend_destinations(
        state=target_state,
        budget=5000,
        available_hours=10,
        top_n=10,
    )
    assert not results.empty
    for _, row in results.iterrows():
        assert target_state.lower() in row["State"].lower()


def test_attraction_type_filtering():
    results = recommend_destinations(
        type="Beach",
        budget=5000,
        available_hours=10,
        top_n=10,
    )
    assert not results.empty
    for _, row in results.iterrows():
        assert "beach" in row["Type"].lower()


def test_content_similarity_boosts_relevant_interests():
    # Query with specific temple interest
    results = recommend_destinations(
        state="Delhi",
        interests=["temple"],
        budget=500,
        available_hours=8,
        top_n=10,
    )
    assert not results.empty
    top_result = results.iloc[0]
    # Temple should rank near top and have positive content match
    assert top_result["Content Similarity Score"] > 0


def test_ranking_determinism():
    run1 = recommend_destinations(
        state="Rajasthan",
        interests=["fort", "palace"],
        budget=500,
        available_hours=6,
        top_n=5,
    )
    run2 = recommend_destinations(
        state="Rajasthan",
        interests=["fort", "palace"],
        budget=500,
        available_hours=6,
        top_n=5,
    )
    assert list(run1["id"]) == list(run2["id"])
    assert list(run1["Recommendation Score"]) == list(run2["Recommendation Score"])


def test_nonexistent_state_returns_empty_dataframe():
    results = recommend_destinations(
        state="AtlantisFantasyWorldXYZ",
        budget=500,
        available_hours=8,
    )
    assert results.empty
