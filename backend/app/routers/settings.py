from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Notification, User, UserSettings
from app.schemas import NotificationOut, SettingsOut, SettingsPatch

router = APIRouter(tags=["settings"])


def _settings(user: User, prefs: UserSettings | None) -> SettingsOut:
    prefs = prefs or UserSettings(user_id=user.id)
    return SettingsOut(
        name=user.name,
        email=user.email,
        timezone=user.timezone,
        currency=user.currency,
        sensitivity=user.sensitivity,
        lookback_mode=user.lookback_mode,
        email_alerts=prefs.email_alerts,
        push_alerts=prefs.push_alerts,
        high_significance_only=prefs.high_significance_only,
        dark_pool_signals=prefs.dark_pool_signals,
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    return _settings(user, prefs)


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(
    body: SettingsPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    prefs = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if not prefs:
        prefs = UserSettings(user_id=user.id)
        db.add(prefs)
    data = body.model_dump(exclude_unset=True)
    for key in ("name", "timezone", "currency", "sensitivity", "lookback_mode", "onboarding_complete"):
        if key in data and data[key] is not None:
            setattr(user, key, data[key])
    for key in ("email_alerts", "push_alerts", "high_significance_only", "dark_pool_signals"):
        if key in data and data[key] is not None:
            setattr(prefs, key, data[key])
    db.commit()
    db.refresh(user)
    return _settings(user, prefs)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ).all()
    return list(rows)


@router.post("/notifications/{nid}/read")
def mark_read(nid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Notification, nid)
    if row and row.user_id == user.id:
        row.read = True
        db.commit()
    return {"ok": True}
