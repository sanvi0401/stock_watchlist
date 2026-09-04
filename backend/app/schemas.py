from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Severity = Literal["STABLE", "NOTABLE", "MEANINGFUL", "HIGH"]
DataStatus = Literal["LIVE", "DELAYED", "STALE", "UNAVAILABLE"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    onboarding_complete: bool = False
    identity_token: str | None = None


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    identity_backup: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    identity_backup: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    timezone: str
    currency: str
    onboarding_complete: bool
    sensitivity: str
    lookback_mode: str
    identity_token: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = "General"
    symbols: list[str] = []


class WatchlistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = None


class AddStockRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=80)
    watchlist_id: int | None = None


class QuoteOut(BaseModel):
    symbol: str
    company_name: str
    current_price: float
    previous_close: float
    previous_price: float | None = None
    price_change_percent: float
    since_last_check_percent: float | None = None
    volume: float
    average_volume: float
    volatility: float
    market_cap: float
    week_52_high: float
    week_52_low: float
    timestamp: datetime
    source: str
    data_status: DataStatus
    market_state: str
    first_seen: bool = False
    significance_score: float = 0
    severity: Severity = "STABLE"
    explanation: str = ""
    change_type: str = "none"
    evidence: list[str] = []


class WatchlistStockOut(BaseModel):
    symbol: str
    added_at: datetime
    quote: QuoteOut | None = None


class WatchlistOut(BaseModel):
    id: int
    name: str
    category: str
    created_at: datetime
    stock_count: int
    stocks: list[WatchlistStockOut] = []
    attention_count: int = 0
    meaningful_count: int = 0
    stable_count: int = 0
    identity_token: str | None = None


class DashboardOut(BaseModel):
    greeting: str
    last_checked_at: datetime | None
    stocks_tracked: int
    watchlist_count: int
    meaningful_changes: int
    needs_attention: int
    stable_count: int
    market_state: str
    data_status: DataStatus
    needs_attention_items: list[QuoteOut]
    meaningful_items: list[QuoteOut]
    stable_items: list[QuoteOut]
    unavailable_items: list[QuoteOut] = []
    first_time: bool = False


class HistoryItem(BaseModel):
    id: int
    timestamp: datetime
    symbol: str
    change_type: str
    significance_score: float
    severity: Severity
    explanation: str
    snapshot_id: int | None = None


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    next_cursor: int | None = None


class SettingsOut(BaseModel):
    name: str
    email: EmailStr
    timezone: str
    currency: str
    sensitivity: str
    lookback_mode: str
    email_alerts: bool
    push_alerts: bool
    high_significance_only: bool
    dark_pool_signals: bool
    created_at: datetime | None = None


class SettingsPatch(BaseModel):
    name: str | None = None
    timezone: str | None = None
    currency: str | None = None
    sensitivity: str | None = None
    lookback_mode: str | None = None
    email_alerts: bool | None = None
    push_alerts: bool | None = None
    high_significance_only: bool | None = None
    dark_pool_signals: bool | None = None
    onboarding_complete: bool | None = None


class NotificationOut(BaseModel):
    id: int
    title: str
    body: str
    kind: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResult(BaseModel):
    symbol: str
    company_name: str
    current_price: float | None
    price_change_percent: float | None
    data_status: DataStatus
    market_state: str
