import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models import PasswordResetToken, User, UserSettings
from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_dev_reset_tokens: dict[str, str] = {}


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise AppError(409, "duplicate_email", "An account with this email already exists.")
    user = User(
        name=body.name.strip(),
        email=body.email.lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id)), onboarding_complete=False)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        onboarding_complete=user.onboarding_complete,
    )


@router.post("/logout")
def logout(_user: User = Depends(get_current_user)) -> dict:
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user:
        return {"ok": True, "message": "If that email exists, a reset link was issued."}
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
    )
    db.commit()
    payload = {"ok": True, "message": "If that email exists, a reset link was issued."}
    if settings.environment == "development":
        payload["dev_reset_token"] = raw
        payload["dev_reset_url"] = f"{settings.public_app_url}/reset-password?token={raw}"
        _dev_reset_tokens[body.email.lower()] = raw
    return payload


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if not row or row.used:
        raise AppError(400, "invalid_reset_token", "This reset link is invalid or expired.")
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise AppError(400, "invalid_reset_token", "This reset link is invalid or expired.")
    user = db.get(User, row.user_id)
    if not user:
        raise AppError(400, "invalid_reset_token", "This reset link is invalid or expired.")
    user.password_hash = hash_password(body.password)
    row.used = True
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
