from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.security import decode_token


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    token = authorization.split(" ", 1)[1]
    sub = decode_token(token)
    if not sub:
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    user = db.get(User, int(sub))
    if not user:
        raise AppError(401, "session_expired", "Your session expired. Please sign in again.")
    return user
