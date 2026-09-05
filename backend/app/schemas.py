from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.security import MAX_PASSWORD_BYTES

Severity = Literal["STABLE", "NOTABLE", "MEANINGFUL", "HIGH"]
DataStatus = Literal["LIVE", "DELAYED", "STALE", "UNAVAILABLE"]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    onboarding_complete: bool = False
    expires_in: int | None = None

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    authenticator_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)

class ForgotPasswordResponse(BaseModel):
    ok: bool = True
    message: str

class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)

class TotpSetupResponse(BaseModel):
    configured: bool
    secret: str | None = None
    otpauth_uri: str | None = None

class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

class TotpStatusResponse(BaseModel):
    enabled: bool

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

class HistoryPointOut(BaseModel):
    timestamp: datetime
    close: float
    volume: float = 0

class WatchlistStockOut(BaseModel):
    symbol: str
    added_at: datetime
    quote: QuoteOut | None = None

class WatchlistOut(BaseModel):
    id: int
    name: str
    category: str
    created_at: datetime
    updated_at: datetime | None = None
    stock_count: int
    stocks: list[WatchlistStockOut] = []
    attention_count: int = 0
    meaningful_count: int = 0
    stable_count: int = 0

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
    baseline_advances_on: str = "acknowledge"

class HistoryItem(BaseModel):
    id: int
    timestamp: datetime
    symbol: str
    change_type: str
    significance_score: float
    severity: Severity
    baseline_price: float
    current_price: float
    currency: str
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
    in_app_alerts: bool
    high_significance_only: bool
    unusual_volume_emphasis: bool
    created_at: datetime | None = None
    alerts_note: str = "Preferences only. This app does not send email or push; changes appear in-app on Overview."
    prices_note: str = "Prices are shown in USD as reported by the delayed quote feed. FX conversion is not implemented."

class SettingsPatch(BaseModel):
    name: str | None = None
    timezone: str | None = None
    sensitivity: str | None = None
    lookback_mode: str | None = None
    in_app_alerts: bool | None = None
    email_alerts: bool | None = None
    push_alerts: bool | None = None
    high_significance_only: bool | None = None
    unusual_volume_emphasis: bool | None = None
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

class AcknowledgeOut(BaseModel):
    ok: bool = True
    acknowledged_at: datetime
    symbols: list[str]
    message: str
