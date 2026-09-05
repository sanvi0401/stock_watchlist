from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models import User
from app.security import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    hash_password,
    new_totp_secret,
    totp_uri,
    verify_totp,
    validate_password_length,
)
from app.schemas import ForgotPasswordRequest, ForgotPasswordResponse, TotpSetupResponse, TotpStatusResponse, TotpVerifyRequest

router = APIRouter(prefix="/auth", tags=["authenticator"])

@router.get("/authenticator/status", response_model=TotpStatusResponse)
def authenticator_status(user: User = Depends(get_current_user)) -> TotpStatusResponse:
    return TotpStatusResponse(enabled=bool(user.totp_enabled and user.totp_secret))

@router.post("/authenticator/setup", response_model=TotpSetupResponse)
def authenticator_setup(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TotpSetupResponse:
    if user.totp_enabled and user.totp_secret:
        return TotpSetupResponse(configured=True)
    secret = new_totp_secret()
    user.totp_secret = encrypt_totp_secret(secret)
    user.totp_enabled = False
    db.commit()
    return TotpSetupResponse(configured=False, secret=secret, otpauth_uri=totp_uri(secret, user.email))

@router.post("/authenticator/verify", response_model=TotpStatusResponse)
def authenticator_verify(body: TotpVerifyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TotpStatusResponse:
    if not user.totp_secret:
        raise AppError(400, "authenticator_not_setup", "Start authenticator setup first.")
    secret = decrypt_totp_secret(user.totp_secret)
    if not verify_totp(secret, body.code):
        raise AppError(400, "invalid_authenticator_code", "The authenticator code is invalid or expired.")
    user.totp_enabled = True
    db.commit()
    return TotpStatusResponse(enabled=True)

@router.post("/recover-password", response_model=ForgotPasswordResponse)
def recover_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    email = str(body.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.totp_enabled or not user.totp_secret:
        raise AppError(400, "recovery_unavailable", "Authenticator recovery is not enabled for this account.")
    if not verify_totp(decrypt_totp_secret(user.totp_secret), body.authenticator_code):
        raise AppError(400, "invalid_authenticator_code", "The authenticator code is invalid or expired.")
    validate_password_length(body.new_password)
    user.password_hash = hash_password(body.new_password)
    user.token_version = int(user.token_version or 0) + 1
    db.commit()
    return ForgotPasswordResponse(ok=True, message="Password updated. Sign in with your new password.")
