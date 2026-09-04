from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models import Notification, User
from app.schemas import NotificationOut, SettingsOut, SettingsPatch

router = APIRouter(tags=["settings"])


def _out(user: User) -> SettingsOut:
    return SettingsOut(
        name=user.name,
        email=user.email,
        timezone=user.timezone,
        sensitivity=user.sensitivity,
        lookback_mode=user.lookback_mode,
        high_significance_only=user.high_significance_only,
        onboarding_complete=user.onboarding_complete,
        created_at=user.created_at,
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings(user: User = Depends(get_current_user)):
    return _out(user)


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(body: SettingsPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if "timezone" in data:
        try:
            ZoneInfo(data["timezone"])
        except (ZoneInfoNotFoundError, ValueError):
            raise AppError(400, "invalid_timezone", "Choose a valid IANA timezone such as Asia/Kolkata.") from None
    if "name" in data:
        data["name"] = data["name"].strip()
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return _out(user)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.id.desc())
            .limit(50)
        ).all()
    )


@router.post("/notifications/read")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for row in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read.is_(False))):
        row.read = True
    db.commit()
    return {"ok": True}
