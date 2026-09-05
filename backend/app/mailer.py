"""Optional SMTP delivery. Absence is not an error — forgot-password still succeeds generically."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger("marketwatch.mail")


def send_reset_email(to_email: str, reset_url: str) -> bool:
    s = get_settings()
    if not s.smtp_host or not s.smtp_from:
        log.info("SMTP not configured; skip sending reset email")
        return False
    msg = EmailMessage()
    msg["Subject"] = "Reset your Market Watch password"
    msg["From"] = s.smtp_from
    msg["To"] = to_email
    msg.set_content(
        "A password reset was requested for this address.\n\n"
        f"Reset link (expires in 2 hours, single use):\n{reset_url}\n\n"
        "If you did not request this, ignore this email."
    )
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            if s.smtp_user and s.smtp_password:
                smtp.starttls()
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:
        log.exception("SMTP send failed")
        return False
