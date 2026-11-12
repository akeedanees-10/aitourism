"""Tests for accommodations, food options, and comprehensive itinerary budgeting."""


def test_stay_search_and_budget_friendly_filter(client):
    # 1. List all accommodations
    resp = client.get("/accommodations")
    assert resp.status_code == 200
    all_stays = resp.json()["accommodations"]
    assert len(all_stays) > 0

    # 2. Filter budget-friendly stays
    resp_budget = client.get("/accommodations?budget_friendly=true")
    assert resp_budget.status_code == 200
    budget_stays = resp_budget.json()["accommodations"]
    assert len(budget_stays) > 0
    for stay in budget_stays:
        assert stay["is_budget_friendly"] is True or (stay["price_min_inr"] is not None and stay["price_min_inr"] <= 1500)

    # 3. Filter by price tier: Budget, Standard, Premium
    resp_tier = client.get("/accommodations?price_tier=Budget")
    assert resp_tier.status_code == 200
    assert len(resp_tier.json()["accommodations"]) > 0

    # 4. Search by city
    resp_city = client.get("/accommodations?city=Delhi")
    assert resp_city.status_code == 200
    assert all("delhi" in s["city"].lower() for s in resp_city.json()["accommodations"])


def test_food_options_and_presets(client):
    # 1. Get daily food presets
    resp_presets = client.get("/food-options/daily-presets")
    assert resp_presets.status_code == 200
    presets = resp_presets.json()
    assert len(presets) == 3
    preset_ids = [p["id"] for p in presets]
    assert "budget" in preset_ids
    assert "standard" in preset_ids
    assert "premium" in preset_ids
    budget_preset = next(p for p in presets if p["id"] == "budget")
    assert budget_preset["daily_per_person_inr"] == 350

    # 2. Search food options
    resp_food = client.get("/food-options")
    assert resp_food.status_code == 200
    foods = resp_food.json()["food_options"]
    assert len(foods) > 0

    # 3. Filter budget-friendly food
    resp_budget_food = client.get("/food-options?budget_friendly=true")
    assert resp_budget_food.status_code == 200
    assert all(f["is_budget_friendly"] is True for f in resp_budget_food.json()["food_options"])

    # 4. Filter food by city
    resp_delhi_food = client.get("/food-options?city=Delhi")
    assert resp_delhi_food.status_code == 200
    assert all("delhi" in f["city"].lower() for f in resp_delhi_food.json()["food_options"])


def test_itinerary_with_stay_and_food_budgeting(client):
    # Register a test user
    reg = client.post(
        "/auth/register",
        json={
            "email": "planner_user@example.com",
            "password": "password123",
            "full_name": "Planner Pro",
        },
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Find a budget stay in Delhi
    stays_resp = client.get("/accommodations?city=Delhi&budget_friendly=true")
    stay_id = stays_resp.json()["accommodations"][0]["id"]
    nightly_min = stays_resp.json()["accommodations"][0]["price_min_inr"] or 700

    # Create a 2-day trip for 2 travelers with entrance fee, 1 night stay, and budget food
    # Destinations: 1 and 2 (e.g. India Gate, Humayun's Tomb)
    itin_payload = {
        "title": "Delhi 2-Day Complete Tour",
        "description": "Historical trip with budget stay and food",
        "total_budget": 5000.0,
        "travelers_count": 2,
        "accommodation": {
            "accommodation_id": stay_id,
            "nights": 1,
        },
        "food": {
            "plan_mode": "daily_budget",
            "daily_budget_per_person": 350.0,
            "travelers_count": 2,
        },
        "days": [
            {
                "day_number": 1,
                "activities": [
                    {"destination_id": 1, "order_index": 1, "time_slot": "Morning"},
                ],
            },
            {
                "day_number": 2,
                "activities": [
                    {"destination_id": 2, "order_index": 1, "time_slot": "Morning"},
                ],
            },
        ],
    }

    create_resp = client.post("/itineraries", json=itin_payload, headers=headers)
    assert create_resp.status_code == 201
    data = create_resp.json()

    itin_id = data["id"]
    assert data["travelers_count"] == 2
    assert data["days_count"] == 2
    assert data["accommodation"]["accommodation_id"] == stay_id
    assert data["accommodation"]["nights"] == 1

    # Check food cost: 350 * 2 travelers * 2 days = 1400 INR
    assert data["food"] is not None
    assert data["food"]["estimated_cost_inr"] == 1400.0
    assert data["estimated_food_cost"] == 1400.0

    # Check cost breakdown
    breakdown = data["cost_breakdown"]
    assert breakdown is not None
    assert breakdown["entrance_fees"] == data["estimated_entrance_fee"]
    assert breakdown["food"] == 1400.0
    assert breakdown["accommodation_min"] == nightly_min * 1
    assert breakdown["total_min"] == data["estimated_entrance_fee"] + (nightly_min * 1) + 1400.0
    assert data["budget_exceeded"] is False

    # 2. Test budget warning: lower total_budget to less than minimum cost
    update_budget = client.put(
        f"/itineraries/{itin_id}",
        json={"total_budget": 500.0},
        headers=headers,
    )
    assert update_budget.status_code == 200
    updated_data = update_budget.json()
    assert updated_data["budget_exceeded"] is True

    # 3. Test changing food plan: skip food planning
    update_food = client.put(
        f"/itineraries/{itin_id}",
        json={"food": {"plan_mode": "none"}},
        headers=headers,
    )
    assert update_food.status_code == 200
    no_food_data = update_food.json()
    assert no_food_data["food"] is None
    assert no_food_data["estimated_food_cost"] == 0.0

    # 4. Test removing accommodation
    update_stay = client.put(
        f"/itineraries/{itin_id}",
        json={"accommodation": None},
        headers=headers,
    )
    assert update_stay.status_code == 200
    no_stay_data = update_stay.json()
    assert no_stay_data["accommodation"] is None
    assert no_stay_data["estimated_accommodation_min"] is None
    assert no_stay_data["estimated_total_min"] == no_stay_data["estimated_entrance_fee"]
