"""Tests for saved destinations and itinerary planning."""


def test_saved_destinations_flow(client):
    # Register a new user
    user_resp = client.post(
        "/auth/register",
        json={
            "email": "saved_user@example.com",
            "password": "password123",
            "full_name": "Saved Tester",
        },
    )
    token = user_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Save destination 1
    save_resp = client.post(
        "/users/me/saved-destinations",
        json={"destination_id": 1, "notes": "Must visit India Gate in the evening!"},
        headers=headers,
    )
    assert save_resp.status_code == 201

    # 2. Saving the same destination again should fail (duplicate prevention)
    dup_save = client.post(
        "/users/me/saved-destinations",
        json={"destination_id": 1},
        headers=headers,
    )
    assert dup_save.status_code == 400

    # 3. List saved destinations
    list_resp = client.get("/users/me/saved-destinations", headers=headers)
    assert list_resp.status_code == 200
    saved_list = list_resp.json()["saved_destinations"]
    assert len(saved_list) == 1
    assert saved_list[0]["destination_id"] == 1
    assert saved_list[0]["destination"]["Name"]

    # 4. Delete saved destination
    del_resp = client.delete("/users/me/saved-destinations/1", headers=headers)
    assert del_resp.status_code == 200

    # 5. Verify list is now empty
    list_after = client.get("/users/me/saved-destinations", headers=headers)
    assert len(list_after.json()["saved_destinations"]) == 0


def test_itinerary_crud_flow(client):
    # Register user
    user_resp = client.post(
        "/auth/register",
        json={
            "email": "itin_user@example.com",
            "password": "password123",
            "full_name": "Itinerary Tester",
        },
    )
    token = user_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a 2-day itinerary
    itin_payload = {
        "title": "Delhi Heritage Weekend",
        "description": "Exploring historical monuments in Delhi",
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "total_budget": 1000.0,
        "days": [
            {
                "day_number": 1,
                "notes": "South Delhi historical walk",
                "activities": [
                    {
                        "destination_id": 1,
                        "order_index": 1,
                        "time_slot": "Morning",
                        "planned_hours": 2.0,
                        "notes": "Arrive early",
                    },
                    {
                        "destination_id": 2,
                        "order_index": 2,
                        "time_slot": "Afternoon",
                        "planned_hours": 2.5,
                    },
                ],
            },
            {
                "day_number": 2,
                "notes": "Old Delhi culture",
                "activities": [
                    {
                        "destination_id": 8,
                        "order_index": 1,
                        "time_slot": "Morning",
                        "planned_hours": 3.0,
                    }
                ],
            },
        ],
    }

    create_resp = client.post("/itineraries", json=itin_payload, headers=headers)
    assert create_resp.status_code == 201
    itin_data = create_resp.json()
    itin_id = itin_data["id"]
    assert itin_data["title"] == "Delhi Heritage Weekend"
    assert len(itin_data["days"]) == 2
    assert itin_data["estimated_entrance_fee"] >= 0

    # 2. Get itinerary by ID
    get_resp = client.get(f"/itineraries/{itin_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == itin_id

    # 3. List itineraries
    list_resp = client.get("/itineraries", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] >= 1

    # 4. Update itinerary title
    update_resp = client.put(
        f"/itineraries/{itin_id}",
        json={"title": "Updated Delhi Heritage Tour"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Delhi Heritage Tour"

    # 5. Delete itinerary
    del_resp = client.delete(f"/itineraries/{itin_id}", headers=headers)
    assert del_resp.status_code == 200

    # 6. Verify deleted
    get_after = client.get(f"/itineraries/{itin_id}", headers=headers)
    assert get_after.status_code == 404
