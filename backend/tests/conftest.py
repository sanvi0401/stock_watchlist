import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("MARKET_DATA_PROVIDER", "mock")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:1/15")  # unreachable on purpose: exercise the memory cache

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _fk(dbapi_conn, _connection_record):  # noqa: ANN001
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


@pytest.fixture
def db():
    session = TestingSession()
    yield session
    session.close()


def auth_headers(email: str | None = None) -> dict[str, str]:
    """Fresh user per call unless an email is given."""
    email = email or f"user-{uuid4().hex[:10]}@test.com"
    r = client.post("/auth/register", json={"name": "Test User", "email": email, "password": "password12"})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": email, "password": "password12"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _reset_provider_cooldown():
    """Cooldown and rate-limit state live in the process cache; never leak them between tests."""
    from app import cache

    cache.cache_delete("provider:cooldown_until")
    yield
    cache.cache_delete("provider:cooldown_until")
