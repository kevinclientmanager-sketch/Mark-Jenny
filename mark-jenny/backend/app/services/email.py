from app.core.config import get_settings

settings = get_settings()


async def send_verification_email(email: str, user_id: int) -> bool:
    """Send email verification link. In production, integrate with SendGrid, Mailgun, etc."""
    if settings.ENVIRONMENT == "development":
        print(f"[DEV] Verification email would be sent to {email} for user {user_id}")
        print(f"[DEV] Verification link: http://localhost:3000/verify-email?token=dev-token-{user_id}")
    return True


async def send_password_reset_email(email: str, user_id: int) -> bool:
    """Send password reset email. In production, integrate with SendGrid, Mailgun, etc."""
    if settings.ENVIRONMENT == "development":
        print(f"[DEV] Password reset email would be sent to {email} for user {user_id}")
        print(f"[DEV] Reset link: http://localhost:3000/reset-password?token=dev-reset-token-{user_id}")
    return True


async def send_notification_email(email: str, subject: str, body: str) -> bool:
    """Send generic notification email."""
    if settings.ENVIRONMENT == "development":
        print(f"[DEV] Notification email to {email}: {subject}")
    return True