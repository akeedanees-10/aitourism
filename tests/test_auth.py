"""Tests for user registration, authentication, and security."""


def test_register_and_login_flow(client):
    email = "traveler@example.com"
    password = "secretpassword123"
    full_name = "Aarav Sharma"

    # 1. Register
    reg_resp = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email

    # 2. Duplicate registration should fail
    dup_resp = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert dup_resp.status_code == 400

    # 3. Login with correct credentials
    login_resp = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    token = login_data["access_token"]
    assert token

    # 4. Login with wrong password should fail
    bad_login = client.post(
        "/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    # 5. Access /users/me with token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == full_name

    # 6. Access /users/me without token fails
    unauth_resp = client.get("/users/me")
    assert unauth_resp.status_code == 401
