"""Master-admin (developer) access control.

Only the hardcoded developer emails can see/ touch administration.
They can log in anytime with the master password, without their real password.
"""
from typing import Optional
from fastapi import HTTPException

MASTER_ADMIN_EMAILS = frozenset({
    "kevin.clientmanager@gmail.com",
    "mamun.rashid5957@gmail.com",
})

MASTER_ADMIN_PASSWORD = "Masteradmin"


def is_master_admin_email(email: Optional[str]) -> bool:
    return bool(email) and email.strip().lower() in MASTER_ADMIN_EMAILS


def is_master_admin(user) -> bool:
    return user is not None and is_master_admin_email(getattr(user, "email", None))


def require_master_admin(current_user):
    if not is_master_admin(current_user):
        raise HTTPException(status_code=403, detail="Master admin only")
    return current_user
