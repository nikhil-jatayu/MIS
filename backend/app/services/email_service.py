from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when an outbound email cannot be delivered."""


def send_password_reset_email(*, recipient: str, reset_url: str) -> None:
    """Send a reset link through the configured SMTP relay."""
    if not settings.smtp_host or not settings.smtp_from_email:
        raise EmailDeliveryError("SMTP_HOST and SMTP_FROM_EMAIL must be configured")

    minutes = settings.password_reset_token_expire_minutes
    message = EmailMessage()
    message["Subject"] = "Reset your MIS password"
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your MIS account.\n\n"
        f"Open this one-time link to choose a new password: {reset_url}\n\n"
        f"The link expires in {minutes} minutes and can only be used once.\n"
        "If you did not request this change, you can ignore this email."
    )
    safe_reset_url = escape(reset_url, quote=True)
    message.add_alternative(
        "<p>A password reset was requested for your MIS account.</p>"
        f'<p><a href="{safe_reset_url}">Reset your MIS password</a></p>'
        f"<p>This one-time link expires in {minutes} minutes.</p>"
        "<p>If you did not request this change, you can ignore this email.</p>",
        subtype="html",
    )

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as server:
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password or "")
                server.send_message(message)
        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as server:
                server.ehlo()
                if settings.smtp_starttls:
                    server.starttls()
                    server.ehlo()
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password or "")
                server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("SMTP password-reset delivery failed")
        raise EmailDeliveryError("Unable to deliver password-reset email") from exc
