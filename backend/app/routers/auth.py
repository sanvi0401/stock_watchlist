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
from app.identity import identity_matches_password, pack_identity, restore_user, unpack_identity
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
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email),
        onboarding_complete=False,
        identity_token=pack_identity(db, user),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    backup = unpack_identity(body.identity_backup)
    if user is None and backup and backup.get("email") == email and identity_matches_password(backup, body.password):
        user = restore_user(db, backup)
    if not user or not verify_password(body.password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email),
        onboarding_complete=user.onboarding_complete,
        identity_token=pack_identity(db, user),
    )


@router.post("/logout")
def logout(_user: User = Depends(get_current_user)) -> dict:
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        backup = unpack_identity(body.identity_backup)
        if backup and backup.get("email") == email:
            user = restore_user(db, backup)
    if not user:
        return {
            "ok": True,
            "message": "If that email is on file, use the reset link we show after a match. This demo does not send email.",
        }
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
    reset_url = f"{settings.public_url}/reset-password?token={raw}"
    _dev_reset_tokens[email] = raw
    return {
        "ok": True,
        "message": "This deployment cannot send email. Use the reset link below — it expires in 2 hours.",
        "reset_url": reset_url,
        "dev_reset_token": raw,
        "dev_reset_url": reset_url,
    }


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
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    out = UserOut.model_validate(user)
    return out.model_copy(update={"identity_token": pack_identity(db, user)})
