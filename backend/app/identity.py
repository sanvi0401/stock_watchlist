from __future__ import annotations

import json
import os
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.config import settings
from app.models import User, UserSettings, Watchlist, WatchlistStock
from app.security import hash_password, verify_password


def _fernet() -> Fernet:
    digest = sha256(settings.secret_key.encode("utf-8")).digest()
    key = __import__("base64").urlsafe_b64encode(digest)
    return Fernet(key)


def pack_identity(db: Session, user: User) -> str:
    lists = db.scalars(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.user_id == user.id)
    ).all()
    payload = {
        "v": 1,
        "email": user.email,
        "name": user.name,
        "password_hash": user.password_hash,
        "onboarding_complete": user.onboarding_complete,
        "timezone": user.timezone,
        "currency": user.currency,
        "sensitivity": user.sensitivity,
        "lookback_mode": user.lookback_mode,
        "lists": [
            {
                "name": wl.name,
                "category": wl.category,
                "symbols": [s.symbol for s in wl.stocks],
            }
            for wl in lists
        ],
    }
    return _fernet().encrypt(json.dumps(payload).encode("utf-8")).decode("utf-8")


def unpack_identity(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        raw = _fernet().decrypt(token.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict) or not data.get("email"):
            return None
        return data
    except (InvalidToken, json.JSONDecodeError, ValueError):
        return None


def restore_user(db: Session, data: dict) -> User:
    email = str(data["email"]).lower()
    user = db.scalar(
        select(User)
        .options(selectinload(User.watchlists).selectinload(Watchlist.stocks))
        .where(User.email == email)
    )
    if user:
        if data.get("password_hash"):
            user.password_hash = data["password_hash"]
        if data.get("name"):
            user.name = data["name"]
        user.onboarding_complete = bool(data.get("onboarding_complete", user.onboarding_complete))
        if data.get("timezone"):
            user.timezone = str(data["timezone"])
        if data.get("currency"):
            user.currency = str(data["currency"])
        if data.get("sensitivity"):
            user.sensitivity = str(data["sensitivity"])
        if data.get("lookback_mode"):
            user.lookback_mode = str(data["lookback_mode"])
    else:
        user = User(
            name=str(data.get("name") or email.split("@")[0]),
            email=email,
            password_hash=str(data.get("password_hash") or hash_password(os.urandom(12).hex())),
            onboarding_complete=bool(data.get("onboarding_complete")),
            timezone=str(data.get("timezone") or "America/New_York"),
            currency=str(data.get("currency") or "USD"),
            sensitivity=str(data.get("sensitivity") or "balanced"),
            lookback_mode=str(data.get("lookback_mode") or "since_last_check"),
        )
        db.add(user)
        db.flush()
        leftover = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        if leftover is None:
            db.add(UserSettings(user_id=user.id))
    existing_lists = {wl.name: wl for wl in user.watchlists}
    for item in data.get("lists") or []:
        name = str(item.get("name") or "Watchlist")
        wl = existing_lists.get(name)
        if not wl:
            wl = Watchlist(user_id=user.id, name=name, category=str(item.get("category") or "General"))
            db.add(wl)
            db.flush()
            existing_lists[name] = wl
        have = {s.symbol for s in wl.stocks}
        for symbol in item.get("symbols") or []:
            sym = str(symbol).upper()
            if sym and sym not in have:
                db.add(WatchlistStock(watchlist_id=wl.id, symbol=sym))
                have.add(sym)
    db.commit()
    db.refresh(user)
    return user


def restore_if_needed(db: Session, backup: str | None) -> User | None:
    data = unpack_identity(backup)
    if not data:
        return None
    return restore_user(db, data)


def identity_matches_password(data: dict, password: str) -> bool:
    hashed = data.get("password_hash")
    if not hashed:
        return False
    return verify_password(password, hashed)
