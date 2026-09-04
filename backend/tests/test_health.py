from datetime import datetime, timezone

from app.db import Base, engine
from app.main import app
from tests.conftest import auth_headers, client


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_me_requires_auth():
    h = auth_headers()
    me = client.get("/auth/me", headers=h)
    assert me.status_code == 200
    assert "email" in me.json()
