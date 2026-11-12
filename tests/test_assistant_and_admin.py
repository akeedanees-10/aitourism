"""Tests for weather fallback, AI travel assistant, and admin statistics."""


def test_weather_endpoint_fallback(client):
    response = client.get("/weather?city=Delhi&state=Delhi")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Delhi"
    assert "best_visiting_period" in data
    assert "note" in data


def test_assistant_chat_destination_query(client):
    response = client.post(
        "/assistant/chat",
        json={"query": "Tell me about Lotus Temple"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Lotus Temple" in data["answer"]
    assert len(data["suggested_destinations"]) > 0


def test_assistant_chat_recommendation_query(client):
    response = client.post(
        "/assistant/chat",
        json={"query": "Recommend forts in Rajasthan"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "suggested_destinations" in data
    assert len(data["suggested_destinations"]) > 0


def test_admin_stats_authorization(client):
    # 1. Unauthenticated request should fail
    unauth_resp = client.get("/admin/stats")
    assert unauth_resp.status_code == 401

    # 2. Register first user (automatically assigned admin)
    reg_resp = client.post(
        "/auth/register",
        json={
            "email": "head_admin@example.com",
            "password": "adminpassword123",
            "full_name": "Chief Administrator",
        },
    )
    admin_token = reg_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Access admin stats
    stats_resp = client.get("/admin/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "users_count" in stats
    assert "destinations_in_catalog" in stats
    assert stats["destinations_in_catalog"] >= 300
    assert "unique_states_covered" in stats
