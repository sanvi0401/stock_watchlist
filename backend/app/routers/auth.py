from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.mailer import send_reset_email
from app.models import PasswordResetToken, User, UserSettings
from app.rate_limit import enforce_auth_rate_limit
from app.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.security import (
    create_access_token,
    hash_password,
    hash_reset_token,
    new_reset_token,
    validate_password_length,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
GENERIC_FORGOT = (
    "If that email is registered, a reset link is issued. "
    "When SMTP is configured it is emailed; otherwise check with the operator."
)


@router.post("/register", response_model=TokenResponse)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
) -> TokenResponse:
    try:
        validate_password_length(body.password)
    except AppError:
        raise
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise AppError(409, "duplicate_email", "An account with this email already exists.")
    user = User(
        name=body.name.strip(),
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        token_version=0,
    )
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    db.commit()
    db.refresh(user)
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email, user.token_version),
        onboarding_complete=False,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
) -> TokenResponse:
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(body.password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email, user.token_version),
        onboarding_complete=user.onboarding_complete,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
def logout(_user: User = Depends(get_current_user)) -> dict:
    return {"ok": True}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
) -> ForgotPasswordResponse:
    settings = get_settings()
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    raw: str | None = None
    if user:
        raw = new_reset_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_reset_token(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=2),
            )
        )
        db.commit()
        origin = (request.headers.get("origin") or "").rstrip("/")
        allowed = {o.rstrip("/") for o in settings.cors_origin_list}
        if origin not in allowed:
            origin = settings.public_url
        reset_url = f"{origin}/reset-password?token={raw}"
        send_reset_email(user.email, reset_url)
    if settings.allow_dev_reset_echo and raw:
        return ForgotPasswordResponse(
            ok=True,
            message="Development only: token returned because SMTP is not required locally.",
            dev_reset_token=raw,
        )
    return ForgotPasswordResponse(ok=True, message=GENERIC_FORGOT)


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
) -> dict:
    try:
        validate_password_length(body.password)
    except AppError:
        raise
    token_hash = hash_reset_token(body.token)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    now = datetime.now(UTC)
    if not row or row.used:
        raise AppError(400, "invalid_reset_token", "This reset link is invalid or expired.")
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now:
        raise AppError(400, "invalid_reset_token", "This reset link is invalid or expired.")
    user = db.get(User, row.user_id)
    if not user:
        raise AppError(400, "invalid_reset_token", "This reset link is invalid or expired.")
    user.password_hash = hash_password(body.password)
    user.token_version = int(user.token_version or 0) + 1
    row.used = True
    db.commit()
    return {"ok": True, "message": "Password updated. Sign in with your new password."}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
