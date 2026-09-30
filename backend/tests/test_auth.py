from app.core import config
from tests.conftest import PASSWORD, auth_header, register_and_login

EMAIL = "alice@example.com"


def signup(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/auth/signup", json={"name": "Alice", "email": email, "password": password})


def test_signup_verify_login(client, outbox):
    assert signup(client).status_code == 201

    # Login before verification: correct password, but 403
    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 403

    code = outbox.last_code(EMAIL)
    response = client.post("/api/auth/verify-email", json={"email": EMAIL, "otp": code})
    assert response.status_code == 200

    # The same code can't be used twice
    response = client.post("/api/auth/verify-email", json={"email": EMAIL, "otp": code})
    assert response.status_code == 400

    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password_and_unknown_email_look_the_same(client, outbox):
    register_and_login(client, outbox, EMAIL)
    wrong = client.post("/api/auth/login", json={"email": EMAIL, "password": "Wrong12345"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Wrong12345"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_protected_endpoint_requires_valid_token(client):
    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/users/me", headers=auth_header("not-a-jwt")).status_code == 401


def test_logout_invalidates_token(client, outbox):
    token = register_and_login(client, outbox, EMAIL)
    assert client.get("/api/users/me", headers=auth_header(token)).status_code == 200

    assert client.post("/api/auth/logout", headers=auth_header(token)).status_code == 200
    assert client.get("/api/users/me", headers=auth_header(token)).status_code == 401


def test_forgot_password_response_is_identical_for_unknown_email(client, outbox):
    register_and_login(client, outbox, EMAIL)
    known = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    # Only the real account received an email
    assert [m["to_email"] for m in outbox.messages].count("nobody@example.com") == 0


def test_forgot_password_cooldown_is_silent(client, outbox):
    register_and_login(client, outbox, EMAIL)
    first = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    second = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert first.json() == second.json()
    reset_emails = [m for m in outbox.messages if "reset" in m["subject"]]
    assert len(reset_emails) == 1


def test_reset_password_flow(client, outbox):
    old_token = register_and_login(client, outbox, EMAIL)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    code = outbox.last_code(EMAIL)

    new_password = "BrandNew789"
    response = client.post(
        "/api/auth/reset-password",
        json={"email": EMAIL, "otp": code, "new_password": new_password},
    )
    assert response.status_code == 200

    # Old sessions are logged out, old password no longer works, new one does
    assert client.get("/api/users/me", headers=auth_header(old_token)).status_code == 401
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": new_password}).status_code == 200

    # The code is single-use
    response = client.post(
        "/api/auth/reset-password",
        json={"email": EMAIL, "otp": code, "new_password": "Another123"},
    )
    assert response.status_code == 400


def test_reset_password_verifies_unverified_account(client, outbox):
    signup(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    code = outbox.last_code(EMAIL)
    response = client.post(
        "/api/auth/reset-password",
        json={"email": EMAIL, "otp": code, "new_password": "BrandNew789"},
    )
    assert response.status_code == 200
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": "BrandNew789"}).status_code == 200


def test_reset_password_wrong_code_counts_attempts(client, outbox, monkeypatch):
    monkeypatch.setattr(config.settings, "otp_max_attempts", 2)
    register_and_login(client, outbox, EMAIL)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    real_code = outbox.last_code(EMAIL)
    wrong_code = "000000" if real_code != "000000" else "111111"

    body = {"email": EMAIL, "otp": wrong_code, "new_password": "BrandNew789"}
    assert client.post("/api/auth/reset-password", json=body).status_code == 400
    assert client.post("/api/auth/reset-password", json=body).status_code == 429
    # Even the right code is dead now
    body["otp"] = real_code
    assert client.post("/api/auth/reset-password", json=body).status_code == 400


def test_reset_password_unknown_email(client):
    response = client.post(
        "/api/auth/reset-password",
        json={"email": "nobody@example.com", "otp": "123456", "new_password": "BrandNew789"},
    )
    assert response.status_code == 400
