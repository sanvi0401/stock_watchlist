"""Password-reset delivery through Gmail SMTP."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger("marketwatch.mail")


def send_reset_email(to_email: str, reset_url: str) -> bool:
    s = get_settings()
    if not s.smtp_host or not s.smtp_user or not s.smtp_password or not s.smtp_from:
        log.error("Password reset email is not configured")
        return False

    message = EmailMessage()
    message["From"] = s.smtp_from
    message["To"] = to_email
    message["Subject"] = "Reset your Market Watch password"
    message.set_content(
        "A password reset was requested for this address.\n\n"
        f"Reset link (expires in 2 hours, single use):\n{reset_url}\n\n"
        "If you did not request this, ignore this email."
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(s.smtp_user, s.smtp_password)
            server.send_message(message)
        return True
    except Exception:
        log.exception("Password reset email delivery failed")
        return False
