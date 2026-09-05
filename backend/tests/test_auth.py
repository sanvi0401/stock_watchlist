from tests.conftest import auth_headers, client


def test_register_and_login():
    email = "newuser@test.com"
    r = client.post("/auth/register", json={"name": "Ada", "email": email, "password": "password12"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert "identity_token" not in body
    bad = client.post("/auth/login", json={"email": email, "password": "wrongpass1"})
    assert bad.status_code == 401
    dup = client.post("/auth/register", json={"name": "Ada", "email": email, "password": "password12"})
    assert dup.status_code == 409
    ok = client.post("/auth/login", json={"email": email, "password": "password12"})
    assert ok.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {ok.json()['access_token']}"})
    assert me.status_code == 200
    assert "password" not in me.json()
    assert "identity_token" not in me.json()


def test_forgot_and_reset_dev_echo():
    email = "resetme@test.com"
    client.post("/auth/register", json={"name": "R", "email": email, "password": "password12"})
    forgot = client.post("/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200
    assert forgot.json().get("reset_url") is None
    token = forgot.json().get("dev_reset_token")
    assert token
    bad = client.post("/auth/reset-password", json={"token": "nope", "password": "newpass123"})
    assert bad.status_code == 400
    ok = client.post("/auth/reset-password", json={"token": token, "password": "newpass123"})
    assert ok.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": "newpass123"})
    assert login.status_code == 200


def test_reset_token_single_use_and_session_revoked():
    email = "revoke@test.com"
    created = client.post("/auth/register", json={"name": "R", "email": email, "password": "password12"})
    old_token = created.json()["access_token"]
    forgot = client.post("/auth/forgot-password", json={"email": email})
    raw = forgot.json()["dev_reset_token"]
    client.post("/auth/reset-password", json={"token": raw, "password": "newerpass1"})
    again = client.post("/auth/reset-password", json={"token": raw, "password": "thirdpass1"})
    assert again.status_code == 400
    stale = client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert stale.status_code == 401


def test_reset_token_expiry():
    from datetime import UTC, datetime, timedelta

    from app.models import PasswordResetToken, User
    from app.security import hash_reset_token
    from tests.conftest import TestingSession

    email = "expire@test.com"
    client.post("/auth/register", json={"name": "E", "email": email, "password": "password12"})
    db = TestingSession()
    user = db.query(User).filter_by(email=email).one()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token("expired-token-value"),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    db.commit()
    db.close()
    r = client.post("/auth/reset-password", json={"token": "expired-token-value", "password": "password99"})
    assert r.status_code == 400


def test_unknown_email_forgot_is_generic():
    r = client.post("/auth/forgot-password", json={"email": "nobody@test.com"})
    assert r.status_code == 200
    assert r.json().get("dev_reset_token") is None
    assert r.json().get("reset_url") is None
