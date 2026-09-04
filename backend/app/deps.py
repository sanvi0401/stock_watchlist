from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.identity import restore_if_needed, unpack_identity
from app.models import User
from app.security import decode_token_payload


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_identity_backup: str | None = Header(default=None, alias="X-Identity-Backup"),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    token = authorization.split(" ", 1)[1]
    payload = decode_token_payload(token)
    if not payload:
        restored = restore_if_needed(db, x_identity_backup)
        if restored:
            return restored
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    sub = str(payload.get("sub") or "")
    email_claim = str(payload.get("email") or "").lower()
    user = None
    if email_claim:
        user = db.scalar(select(User).where(User.email == email_claim))
    if user is None and sub.isdigit():
        user = db.get(User, int(sub))
        if user is not None and email_claim and user.email.lower() != email_claim:
            user = None
    if user is None and sub and not sub.isdigit():
        user = db.scalar(select(User).where(User.email == sub.lower()))
    if user is None:
        restored = restore_if_needed(db, x_identity_backup)
        if restored:
            return restored
        backup = unpack_identity(x_identity_backup)
        if backup and backup.get("email"):
            user = db.scalar(select(User).where(User.email == str(backup["email"]).lower()))
        if user is None:
            raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    return user
