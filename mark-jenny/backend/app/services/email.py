"""Outbound email.

Previously every function printed a [DEV] line and returned True, so callers
reported "email sent" while nothing was delivered. This sends for real over
SMTP when configured, and otherwise raises/report a real failure instead of
pretending to succeed.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

settings = get_settings()
log = logging.getLogger("email")


class EmailNotConfigured(RuntimeError):
    pass


def _smtp_configured() -> bool:
    return bool(getattr(settings, "SMTP_HOST", None))


def _from_address() -> str:
    return getattr(settings, "SMTP_FROM", None) or getattr(settings, "SMTP_USER", "") or "no-reply@mark-imti.local"


def _send(to: str, subject: str, body: str) -> bool:
    if not _smtp_configured():
        raise EmailNotConfigured(
            "SMTP is not configured. Set SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD "
            "(and SMTP_FROM) to send real email. Nothing was delivered."
        )
    host = settings.SMTP_HOST
    port = int(getattr(settings, "SMTP_PORT", 587) or 587)
    use_ssl = bool(getattr(settings, "SMTP_USE_SSL", False))

    msg = EmailMessage()
    msg["From"] = _from_address()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            try:
                server.starttls()
            except smtplib.SMTPNotSupportedError:
                pass
        with server:
            user = getattr(settings, "SMTP_USER", None)
            password = getattr(settings, "SMTP_PASSWORD", None)
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        log.error("SMTP send to %s failed: %s", to, exc)
        raise RuntimeError(f"SMTP delivery to {to} failed: {exc}") from exc


def _frontend_base() -> str:
    return (getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000").rstrip("/")


async def send_verification_email(email: str, user_id: int) -> bool:
    link = f"{_frontend_base()}/verify-email?token=dev-token-{user_id}"
    return _send(email, "Verify your Mark-Imti account",
                 f"Welcome to Mark-Imti.\n\nConfirm your address:\n{link}\n")


async def send_password_reset_email(email: str, user_id: int) -> bool:
    link = f"{_frontend_base()}/reset-password?token=dev-reset-token-{user_id}"
    return _send(email, "Reset your Mark-Imti password",
                 f"Use this link to choose a new password:\n{link}\n\n"
                 "If you did not request this, you can ignore the email.\n")


async def send_notification_email(email: str, subject: str, body: str) -> bool:
    return _send(email, subject, body)
