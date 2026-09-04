from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Severity = Literal["STABLE", "NOTABLE", "MEANINGFUL", "HIGH"]
DataStatus = Literal["LIVE", "DELAYED", "STALE", "UNAVAILABLE"]
Sensitivity = Literal["conservative", "balanced", "sensitive"]
Lookback = Literal["since_last_check", "previous_close", "five_day"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    onboarding_complete: bool = False


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    timezone: str
    onboarding_complete: bool
    sensitivity: str
    lookback_mode: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="General", max_length=64)
    symbols: list[str] = Field(default_factory=list, max_length=100)


class WatchlistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=64)


class AddStockRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=80)


class QuoteOut(BaseModel):
    symbol: str
    company_name: str
    current_price: float
    previous_close: float
    previous_price: float | None = None
    baseline_at: datetime | None = None
    price_change_percent: float
    since_last_check_percent: float | None = None
    volume: float
    average_volume: float
    volatility: float
    market_cap: float
    week_52_high: float
    week_52_low: float
    sparkline: list[float] = []
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
    unavailable_count: int = 0


class DashboardOut(BaseModel):
    greeting: str
    baseline_at: datetime | None
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
    new_visit: bool = False


class CheckpointOut(BaseModel):
    ok: bool = True
    symbols: int
    baseline_at: datetime


class HistoryItem(BaseModel):
    id: int
    timestamp: datetime
    symbol: str
    change_type: str
    significance_score: float
    severity: Severity
    baseline_price: float
    current_price: float
    since_last_check_percent: float
    explanation: str
    evidence: list[str] = []
    snapshot_id: int | None = None


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    next_cursor: int | None = None


class SettingsOut(BaseModel):
    name: str
    email: EmailStr
    timezone: str
    sensitivity: str
    lookback_mode: str
    high_significance_only: bool
    onboarding_complete: bool
    created_at: datetime | None = None


class SettingsPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = None
    sensitivity: Sensitivity | None = None
    lookback_mode: Lookback | None = None
    high_significance_only: bool | None = None
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


class HealthOut(BaseModel):
    ok: bool = True
    environment: str
    provider: str
    cache: str
    persistence: str
    market_state: str
    server_time: datetime
