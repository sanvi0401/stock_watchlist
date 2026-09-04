from tests.conftest import client


def test_register_login_and_duplicate():
    email = "newuser@test.com"
    r = client.post("/auth/register", json={"name": "Ada", "email": email, "password": "password12"})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert "identity_token" not in r.json()
    bad = client.post("/auth/login", json={"email": email, "password": "wrongpass1"})
    assert bad.status_code == 401
    dup = client.post("/auth/register", json={"name": "Ada", "email": "NewUser@test.com", "password": "password12"})
    assert dup.status_code == 409
    ok = client.post("/auth/login", json={"email": email, "password": "password12"})
    assert ok.status_code == 200


def test_short_password_rejected():
    r = client.post("/auth/register", json={"name": "A", "email": "short@test.com", "password": "short"})
    assert r.status_code == 422


def test_forgot_and_reset():
    email = "resetme@test.com"
    client.post("/auth/register", json={"name": "R", "email": email, "password": "password12"})
    forgot = client.post("/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200
    url = forgot.json().get("reset_url")
    assert url and "token=" in url
    token = url.split("token=")[1]
    bad = client.post("/auth/reset-password", json={"token": "nope", "password": "newpass123"})
    assert bad.status_code == 400
    ok = client.post("/auth/reset-password", json={"token": token, "password": "newpass123"})
    assert ok.status_code == 200
    reused = client.post("/auth/reset-password", json={"token": token, "password": "another123"})
    assert reused.status_code == 400
    login = client.post("/auth/login", json={"email": email, "password": "newpass123"})
    assert login.status_code == 200


def test_forgot_unknown_email_does_not_leak():
    r = client.post("/auth/forgot-password", json={"email": "nobody@test.com"})
    assert r.status_code == 200
    assert "reset_url" not in r.json()


def test_bad_token_rejected():
    r = client.get("/dashboard", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401
    assert r.json()["code"] == "session_expired"
