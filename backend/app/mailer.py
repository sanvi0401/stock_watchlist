"""Password-reset delivery through Resend's HTTPS API."""

from __future__ import annotations

import logging
import json
from urllib.request import Request, urlopen

from app.config import get_settings

log = logging.getLogger("marketwatch.mail")


def send_reset_email(to_email: str, reset_url: str) -> bool:
    s = get_settings()
    if not s.resend_api_key or not s.email_from:
        return False
    payload = json.dumps(
        {
            "from": s.email_from,
            "to": [to_email],
            "subject": "Reset your Market Watch password",
            "text": (
                "A password reset was requested for this address.\n\n"
                f"Reset link (expires in 2 hours, single use):\n{reset_url}\n\n"
                "If you did not request this, ignore this email."
            ),
        }
    ).encode()
    request = Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {s.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception:
        log.exception("Password reset email delivery failed")
        return False
