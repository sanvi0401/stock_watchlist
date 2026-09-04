from tests.conftest import auth_headers, client


def test_register_and_login():
    email = "newuser@test.com"
    r = client.post("/auth/register", json={"name": "Ada", "email": email, "password": "password12"})
    assert r.status_code == 200
    assert r.json()["access_token"]
    bad = client.post("/auth/login", json={"email": email, "password": "wrongpass1"})
    assert bad.status_code == 401
    dup = client.post("/auth/register", json={"name": "Ada", "email": email, "password": "password12"})
    assert dup.status_code == 409
    ok = client.post("/auth/login", json={"email": email, "password": "password12"})
    assert ok.status_code == 200


def test_forgot_and_reset():
    email = "resetme@test.com"
    client.post("/auth/register", json={"name": "R", "email": email, "password": "password12"})
    forgot = client.post("/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200
    token = forgot.json().get("dev_reset_token")
    assert token
    bad = client.post("/auth/reset-password", json={"token": "nope", "password": "newpass123"})
    assert bad.status_code == 400
    ok = client.post("/auth/reset-password", json={"token": token, "password": "newpass123"})
    assert ok.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": "newpass123"})
    assert login.status_code == 200
