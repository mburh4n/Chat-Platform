from tests.conftest import PASSWORD, auth_header, register_and_login

EMAIL = "bob@example.com"


def test_read_me_hides_secrets(client, outbox):
    token = register_and_login(client, outbox, EMAIL, name="Bob")
    response = client.get("/api/users/me", headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == EMAIL
    assert body["name"] == "Bob"
    assert "hashed_password" not in body
    assert "token_version" not in body


def test_update_profile(client, outbox):
    token = register_and_login(client, outbox, EMAIL)
    response = client.patch("/api/users/me", json={"name": "  Bob   Builder "}, headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["name"] == "Bob Builder"

    # Email can't be changed through the profile
    response = client.patch("/api/users/me", json={"name": "Bob", "email": "x@example.com"}, headers=auth_header(token))
    assert response.status_code == 422


def test_update_profile_rejects_short_name(client, outbox):
    token = register_and_login(client, outbox, EMAIL)
    response = client.patch("/api/users/me", json={"name": "B"}, headers=auth_header(token))
    assert response.status_code == 422


def test_change_password(client, outbox):
    token = register_and_login(client, outbox, EMAIL)

    response = client.post(
        "/api/users/me/change-password",
        json={"current_password": "WrongPass1", "new_password": "NewPass4567"},
        headers=auth_header(token),
    )
    assert response.status_code == 400

    response = client.post(
        "/api/users/me/change-password",
        json={"current_password": PASSWORD, "new_password": "NewPass4567"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    new_token = response.json()["access_token"]

    # The old token is revoked, the new one works
    assert client.get("/api/users/me", headers=auth_header(token)).status_code == 401
    assert client.get("/api/users/me", headers=auth_header(new_token)).status_code == 200
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": "NewPass4567"}).status_code == 200


def test_change_password_must_differ(client, outbox):
    token = register_and_login(client, outbox, EMAIL)
    response = client.post(
        "/api/users/me/change-password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=auth_header(token),
    )
    assert response.status_code == 400
