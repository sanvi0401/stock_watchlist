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


def _add_missing_columns(table_name: str, required: dict[str, str]) -> None:
    """Add missing columns safely for existing databases, including concurrent Vercel workers."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [(name, sql_type) for name, sql_type in required.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for name, sql_type in missing:
            # IF NOT EXISTS makes the one-time upgrade safe when two serverless
            # invocations race to initialize the same Neon database.
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {name} {sql_type}"))


def ensure_detected_change_columns() -> None:
    """Add history columns to existing databases without dropping or rewriting data."""
    _add_missing_columns(
        "detected_changes",
        {
            "baseline_price": "FLOAT",
            "current_price": "FLOAT",
            "currency": "VARCHAR(8)",
            "since_last_check_percent": "FLOAT",
        },
    )


def ensure_authenticator_columns() -> None:
    """Add TOTP columns to existing user tables without dropping data."""
    _add_missing_columns(
        "users",
        {
            "totp_secret": "VARCHAR(512)",
            "totp_enabled": "BOOLEAN DEFAULT FALSE",
        },
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
