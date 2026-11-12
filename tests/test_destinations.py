"""Tests for root, health, and destination catalog endpoints."""


def test_home_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["version"] == "2.0.0"


def test_home_serves_html_for_browser(client):
    response = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "VoyAIge" in response.text


def test_web_app_endpoint(client):
    response = client.get("/app")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "VoyAIge" in response.text


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_destinations_pagination(client):
    response = client.get("/destinations?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["destinations"]) == 10
    assert data["total"] >= 300


def test_get_single_destination(client):
    # Destination 1
    response = client.get("/destinations/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "Name" in data
    assert "State" in data


def test_get_nonexistent_destination_returns_404(client):
    response = client.get("/destinations/999999")
    assert response.status_code == 404


def test_list_states(client):
    response = client.get("/states")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 25
    assert "Delhi" in data["states"]
    assert "Lakshadweep" in data["states"]


def test_lakshadweep_destination_and_state_filter(client):
    # Test state filtering for Lakshadweep
    response = client.get("/destinations?state=Lakshadweep")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    dest = next((d for d in data["destinations"] if d["Name"] == "Agatti Island"), None)
    assert dest is not None
    assert dest["State"] == "Lakshadweep"
    assert dest["City"] == "Agatti"
    assert dest["Type"] == "Island"
    assert dest["Google review rating"] == 4.7
    assert dest["Entrance Fee in INR"] == 200
    assert dest["Airport with 50km Radius"] == "Yes"

    # Test single destination lookup
    dest_id = dest["id"]
    single_res = client.get(f"/destinations/{dest_id}")
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["Name"] == "Agatti Island"
    assert single_data["State"] == "Lakshadweep"

    # Test recommendation for Lakshadweep
    rec_res = client.get("/recommend?state=Lakshadweep")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["count"] >= 1
    assert any(r["Name"] == "Agatti Island" for r in rec_data["recommendations"])


def test_list_destination_types(client):
    response = client.get("/destination-types")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 10


def test_recommend_endpoint_compatibility(client):
    response = client.get("/recommend?state=Delhi&budget=500&available_hours=8")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] > 0
    assert len(data["recommendations"]) > 0
    assert "Personalization Score" in data["recommendations"][0]
    assert "Explanation" in data["recommendations"][0]
