from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    sensitivity: Mapped[str] = mapped_column(String(16), default="balanced")
    lookback_mode: Mapped[str] = mapped_column(String(32), default="since_last_check")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    watchlists: Mapped[list["Watchlist"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="General")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="watchlists")
    stocks: Mapped[list["WatchlistStock"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )


class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", name="uq_watchlist_symbol"),
        Index("ix_watchlist_stocks_symbol", "symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    watchlist: Mapped[Watchlist] = relationship(back_populates="stocks")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (Index("ix_snapshots_symbol_ts", "symbol", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(160), default="")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    previous_close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=0)
    average_volume: Mapped[float] = mapped_column(Float, default=0)
    volatility: Mapped[float] = mapped_column(Float, default=0.02)
    market_cap: Mapped[float] = mapped_column(Float, default=0)
    week_52_high: Mapped[float] = mapped_column(Float, default=0)
    week_52_low: Mapped[float] = mapped_column(Float, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="mock")
    data_status: Mapped[str] = mapped_column(String(16), default="LIVE")
    market_state: Mapped[str] = mapped_column(String(16), default="OPEN")


class UserStockState(Base):
    __tablename__ = "user_stock_state"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_user_symbol_state"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_price: Mapped[float] = mapped_column(Float, nullable=False)
    reference_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("market_snapshots.id", ondelete="SET NULL"), nullable=True
    )


class DetectedChange(Base):
    __tablename__ = "detected_changes"
    __table_args__ = (Index("ix_changes_user_detected", "user_id", "detected_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)
    significance_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("market_snapshots.id", ondelete="SET NULL"), nullable=True
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(32), default="change")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    email_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    push_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    high_significance_only: Mapped[bool] = mapped_column(Boolean, default=False)
    dark_pool_signals: Mapped[bool] = mapped_column(Boolean, default=True)
