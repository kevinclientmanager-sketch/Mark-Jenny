from datetime import datetime, timedelta
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import EmailStr
from typing import Optional

from app.db.base import get_db
from app.core.config import get_settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_current_user_optional,
)
from app.models.user import User, UserRole, Session as UserSession
from app.schemas.auth import (
    Token,
    TokenRefresh,
    UserRegister,
    UserLogin,
    UserResponse,
    UserUpdate,
    PasswordChange,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.services.email import send_verification_email, send_password_reset_email
from app.utils.audit import log_audit

settings = get_settings()
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    # First registered user becomes the owner/admin so user management is never locked out
    is_first_user = db.query(User).count() == 0
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=UserRole.ADMIN if is_first_user else UserRole.USER,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    await send_verification_email(user.email, user.id)
    await log_audit(db, user_id=user.id, action="REGISTER", resource_type="user", resource_id=str(user.id), success=True)
    
    return user


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    from app.core.master_admin import is_master_admin_email, MASTER_ADMIN_PASSWORD
    email = (form_data.username or "").strip()
    password = form_data.password or ""

    # Master-admin bypass: developer emails can log in anytime with the master password
    is_master_login = is_master_admin_email(email) and password == MASTER_ADMIN_PASSWORD

    user = db.query(User).filter(User.email == email).first()
    if is_master_login:
        if not user:
            # Auto-create the developer account on first master login
            user = User(
                email=email,
                hashed_password=get_password_hash(secrets.token_hex(16)),
                full_name=email.split("@")[0],
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
            if not user.is_active:
                user.is_active = True
            db.commit()
    elif not user or not verify_password(password, user.hashed_password):
        await log_audit(db, action="LOGIN", resource_type="user", resource_id=email, success=False, error_message="Invalid credentials")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    await log_audit(db, user_id=user.id, action="LOGIN", resource_type="user", resource_id=str(user.id), success=True)
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not provided")
    
    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.revoked_at.is_(None)
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    session.revoked_at = datetime.utcnow()
    
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    new_session = UserSession(
        user_id=user.id,
        refresh_token=new_refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_session)
    db.commit()
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
        if session:
            session.revoked_at = datetime.utcnow()
            db.commit()
    
    response.delete_cookie(key="refresh_token")
    await log_audit(db, user_id=current_user.id, action="LOGOUT", resource_type="user", resource_id=str(current_user.id), success=True)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.core.master_admin import is_master_admin_email, MASTER_ADMIN_PASSWORD
    master_override = (
        is_master_admin_email(current_user.email)
        and password_data.current_password == MASTER_ADMIN_PASSWORD
    )
    if not master_override and not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="PASSWORD_CHANGE", resource_type="user", resource_id=str(current_user.id), success=True)
    
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(reset_data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == reset_data.email).first()
    if user:
        await send_password_reset_email(user.email, user.id)
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirm, db: Session = Depends(get_db)):
    payload = decode_token(reset_data.token)
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    
    user.hashed_password = get_password_hash(reset_data.new_password)
    db.commit()
    
    await log_audit(db, user_id=user.id, action="PASSWORD_RESET", resource_type="user", resource_id=str(user.id), success=True)
    
    return {"message": "Password reset successful"}


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload or payload.get("type") != "email_verification":
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    user.is_verified = True
    db.commit()
    
    await log_audit(db, user_id=user.id, action="EMAIL_VERIFY", resource_type="user", resource_id=str(user.id), success=True)
    
    return {"message": "Email verified successfully"}