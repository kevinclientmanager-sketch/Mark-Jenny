from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user, get_password_hash
from app.models.user import User, UserRole
from app.models.audit import AuditLog, AuditAction
from app.utils.audit import log_audit

router = APIRouter()

def require_admin(current_user: User):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only - server-side RBAC enforced")
    return current_user

def require_creator_or_admin(current_user: User):
    if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
        raise HTTPException(status_code=403, detail="Creator/Admin only")
    return current_user

# In-memory stores for demo (in prod would be DB tables)
FEATURE_FLAGS: Dict[str, bool] = {"enable_skills": True, "enable_browser": True, "enable_code_exec": True}
BLACKLIST: List[str] = []
SKILL_ACCESS: Dict[str, List[str]] = {}  # skill_id -> roles
SUBSCRIPTIONS: Dict[int, Dict] = {}
CREDITS: Dict[int, int] = {}

class RoleUpdate(BaseModel):
    role: UserRole

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER

class SubscriptionUpdate(BaseModel):
    plan: str
    credits: Optional[int] = None
    expires_at: Optional[datetime] = None

class FeatureFlagUpdate(BaseModel):
    flag: str
    enabled: bool

@router.get("/users")
async def admin_list_users(
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    require_admin(current_user)
    q = db.query(User)
    if search:
        q = q.filter(or_(User.email.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%")))
    if role:
        q = q.filter(User.role == role)
    total = q.count()
    users = q.order_by(desc(User.created_at)).offset((page-1)*page_size).limit(page_size).all()
    return {"users": [{"id":u.id, "email":u.email, "full_name":u.full_name, "role":u.role.value, "is_active":u.is_active, "created_at":u.created_at} for u in users], "total":total, "page":page, "page_size":page_size}

@router.post("/users")
async def admin_create_user(data: UserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    u = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name or data.email.split("@")[0],
        role=data.role,
        is_active=True,
        is_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    await log_audit(db, user_id=current_user.id, action="USER_CREATE", resource_type="user", resource_id=str(u.id), success=True)
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role.value, "is_active": u.is_active}

@router.get("/users/{user_id}")
async def admin_get_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    u = db.query(User).filter(User.id == user_id).first()
    if not u: raise HTTPException(status_code=404, detail="User not found")
    return {"id":u.id, "email":u.email, "full_name":u.full_name, "role":u.role.value, "is_active":u.is_active, "is_verified":u.is_verified, "created_at":u.created_at, "last_login_at":u.last_login_at, "subscription": SUBSCRIPTIONS.get(u.id), "credits": CREDITS.get(u.id, 0)}

@router.patch("/users/{user_id}/role")
async def admin_set_role(user_id: int, data: RoleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    u = db.query(User).filter(User.id == user_id).first()
    if not u: raise HTTPException(status_code=404, detail="User not found")
    u.role = data.role
    db.commit()
    await log_audit(db, user_id=current_user.id, action="ROLE_CHANGE", resource_type="user", resource_id=str(user_id), success=True)
    return {"message": f"Role set to {data.role.value}"}

@router.post("/users/{user_id}/blacklist")
async def admin_blacklist(user_id: int, reason: str = "violation", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    u = db.query(User).filter(User.id == user_id).first()
    if not u: raise HTTPException(status_code=404, detail="User not found")
    u.is_active = False
    BLACKLIST.append(u.email)
    db.commit()
    await log_audit(db, user_id=current_user.id, action="USER_BAN", resource_type="user", resource_id=str(user_id), success=True)
    return {"message": f"User {u.email} blacklisted", "blacklist": BLACKLIST}

@router.delete("/users/{user_id}/blacklist")
async def admin_unblacklist(email: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    if email in BLACKLIST:
        BLACKLIST.remove(email)
        u = db.query(User).filter(User.email == email).first()
        if u: u.is_active = True; db.commit()
    return {"blacklist": BLACKLIST}

@router.get("/blacklist")
async def get_blacklist(current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    return {"blacklist": BLACKLIST}

# Creator/Admin management
@router.get("/creators")
async def list_creators(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    creators = db.query(User).filter(User.role == UserRole.CREATOR).all()
    return [{"id":u.id, "email":u.email, "full_name":u.full_name} for u in creators]

@router.get("/admins")
async def list_admins(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
    return [{"id":u.id, "email":u.email} for u in admins]

# Subscriptions & Credits
@router.get("/subscriptions/{user_id}")
async def get_subscription(user_id: int, current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    return SUBSCRIPTIONS.get(user_id, {"plan":"free", "credits": CREDITS.get(user_id, 0)})

@router.patch("/subscriptions/{user_id}")
async def set_subscription(user_id: int, data: SubscriptionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    u = db.query(User).filter(User.id==user_id).first()
    if not u: raise HTTPException(status_code=404, detail="User not found")
    SUBSCRIPTIONS[user_id] = {"plan": data.plan, "expires_at": data.expires_at.isoformat() if data.expires_at else None}
    if data.credits is not None:
        CREDITS[user_id] = data.credits
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="subscription", resource_id=str(user_id), success=True)
    return {"subscription": SUBSCRIPTIONS[user_id], "credits": CREDITS.get(user_id, 0)}

@router.get("/credits/{user_id}")
async def get_credits(user_id: int, current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    return {"credits": CREDITS.get(user_id, 0)}

@router.post("/credits/{user_id}/add")
async def add_credits(user_id: int, amount: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    CREDITS[user_id] = CREDITS.get(user_id, 0) + amount
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="credits", resource_id=str(user_id), success=True)
    return {"credits": CREDITS[user_id]}

# Feature flags
@router.get("/feature-flags")
async def get_flags(current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    return FEATURE_FLAGS

@router.patch("/feature-flags")
async def set_flag(data: FeatureFlagUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    FEATURE_FLAGS[data.flag] = data.enabled
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="feature_flag", resource_id=data.flag, success=True)
    return FEATURE_FLAGS

# Skill access
@router.get("/skill-access")
async def get_skill_access(current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    return SKILL_ACCESS

@router.patch("/skill-access/{skill_id}")
async def set_skill_access(skill_id: str, roles: List[str], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    SKILL_ACCESS[skill_id] = roles
    return {"skill_id": skill_id, "roles": roles}

# System config & Audit
@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    logs = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).all()
    return [{"id":l.id, "action":l.action.value, "resource_type":l.resource_type, "resource_id":l.resource_id, "user_id":l.user_id, "success":l.success, "created_at":l.created_at} for l in logs]

@router.get("/system/config")
async def get_system_config(current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    return {
        "feature_flags": FEATURE_FLAGS,
        "blacklist_count": len(BLACKLIST),
        "skill_access_count": len(SKILL_ACCESS),
        "note": "All checks are server-side - UI hiding is not security"
    }

# Access control
@router.get("/access-control")
async def get_access_control(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    counts = {
        "total_users": db.query(User).count(),
        "admins": db.query(User).filter(User.role==UserRole.ADMIN).count(),
        "creators": db.query(User).filter(User.role==UserRole.CREATOR).count(),
        "users": db.query(User).filter(User.role==UserRole.USER).count(),
    }
    return counts

