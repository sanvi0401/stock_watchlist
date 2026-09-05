from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.security import decode_token_payload


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    token = authorization.split(" ", 1)[1]
    payload = decode_token_payload(token)
    if not payload:
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    sub = str(payload.get("sub") or "")
    email_claim = str(payload.get("email") or "").lower()
    ver = int(payload.get("ver") or 0)
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
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    if int(user.token_version or 0) != ver:
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    return user
