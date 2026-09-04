import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.market.freshness import as_utc
from app.models import PasswordResetToken, User
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

_DUPLICATE = AppError(409, "duplicate_email", "An account with this email already exists.")
_BAD_LOGIN = AppError(401, "invalid_credentials", "Email or password is incorrect.")
_BAD_RESET = AppError(400, "invalid_reset_token", "This reset link is invalid or expired.")


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise _DUPLICATE
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two sign-ups for the same address raced; the unique index is the source of truth.
        db.rollback()
        raise _DUPLICATE from None
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id)), onboarding_complete=False)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise _BAD_LOGIN
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        onboarding_complete=user.onboarding_complete,
    )


@router.post("/logout")
def logout(_user: User = Depends(get_current_user)) -> dict:
    # Stateless JWT: the client discards the token. A server-side denylist is
    # the obvious next step and is listed under limitations in the README.
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    # Same response shape whether or not the address exists (no account enumeration).
    response: dict = {"ok": True, "message": "If that email is on file, a reset link has been issued."}
    if not user:
        return response
    raw = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
    )
    db.commit()
    if settings.show_reset_link:
        response["message"] = "This deployment has no email service. Use the link below; it expires in 2 hours."
        response["reset_url"] = f"{settings.public_url}/reset-password?token={raw}"
    return response


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if not row or row.used or (as_utc(row.expires_at) or datetime.min.replace(tzinfo=UTC)) < datetime.now(UTC):
        raise _BAD_RESET
    user = db.get(User, row.user_id)
    if not user:
        raise _BAD_RESET
    user.password_hash = hash_password(body.password)
    row.used = True
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
