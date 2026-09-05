from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models import Notification, User, UserSettings
from app.schemas import NotificationOut, SettingsOut, SettingsPatch

router = APIRouter(tags=["settings"])


def _settings(user: User, prefs: UserSettings | None) -> SettingsOut:
    prefs = prefs or UserSettings(user_id=user.id)
    return SettingsOut(
        name=user.name,
        email=user.email,
        timezone=user.timezone,
        sensitivity=user.sensitivity,
        lookback_mode=user.lookback_mode,
        in_app_alerts=prefs.email_alerts,
        high_significance_only=prefs.high_significance_only,
        unusual_volume_emphasis=prefs.unusual_volume_emphasis,
        created_at=user.created_at,
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
    if data.get("sensitivity") and data["sensitivity"] not in {"conservative", "balanced", "sensitive"}:
        raise AppError(400, "invalid_sensitivity", "Choose conservative, balanced, or sensitive.")
    if data.get("lookback_mode") and data["lookback_mode"] not in {
        "since_last_check",
        "previous_close",
        "five_day",
    }:
        raise AppError(400, "invalid_lookback", "Choose a valid lookback window.")
    if data.get("timezone"):
        try:
            ZoneInfo(str(data["timezone"]))
        except (ZoneInfoNotFoundError, KeyError):
            raise AppError(400, "invalid_timezone", "Unknown IANA timezone.") from None
    for key in ("name", "timezone", "sensitivity", "lookback_mode", "onboarding_complete"):
        if key in data and data[key] is not None:
            setattr(user, key, data[key])
    if "in_app_alerts" in data and data["in_app_alerts"] is not None:
        prefs.email_alerts = data["in_app_alerts"]
    elif "email_alerts" in data and data["email_alerts"] is not None:
        prefs.email_alerts = data["email_alerts"]
    if "high_significance_only" in data and data["high_significance_only"] is not None:
        prefs.high_significance_only = data["high_significance_only"]
    if "unusual_volume_emphasis" in data and data["unusual_volume_emphasis"] is not None:
        prefs.unusual_volume_emphasis = data["unusual_volume_emphasis"]
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
