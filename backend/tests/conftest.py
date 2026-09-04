import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("MARKET_DATA_PROVIDER", "mock")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import MarketSnapshot, User, UserStockState
from app.security import hash_password

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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


def auth_headers():
    r = client.post(
        "/auth/register",
        json={"name": "Sanvi Patel", "email": "sanvi@test.com", "password": "password12"},
    )
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": "sanvi@test.com", "password": "password12"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
