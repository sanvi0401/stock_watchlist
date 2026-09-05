from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings, validate_settings


class Base(DeclarativeBase):
    pass


validate_settings(settings)

_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_kwargs)
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_conn, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ensure_detected_change_columns() -> None:
    """Add history columns to existing databases without dropping or rewriting data."""
    required = {
        "baseline_price": "FLOAT",
        "current_price": "FLOAT",
        "currency": "VARCHAR(8)",
        "since_last_check_percent": "FLOAT",
    }
    inspector = inspect(engine)
    if "detected_changes" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("detected_changes")}
    missing = [(name, sql_type) for name, sql_type in required.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for name, sql_type in missing:
            connection.execute(text(f"ALTER TABLE detected_changes ADD COLUMN {name} {sql_type}"))


def ensure_authenticator_columns() -> None:
    """Add TOTP columns to existing user tables without dropping data."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("users")}
    required = {
        "totp_secret": "VARCHAR(512)",
        "totp_enabled": "BOOLEAN DEFAULT FALSE",
    }
    missing = [(name, sql_type) for name, sql_type in required.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for name, sql_type in missing:
            connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type}"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
