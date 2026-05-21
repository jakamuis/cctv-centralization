from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from starlette.requests import Request

from app.api.v1.dependencies import (
    get_current_user,
    require_role,
    require_permission,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.security import jwt
from app.security.jwt import verify_password, get_password_hash
from app.models.audit_log import AuditLog


router = APIRouter()


@router.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), request: Request = None):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log failed login
        audit = AuditLog(
            user_id=user.id if user else None,
            action="failed_login",
            ip_address=request.client.host if request else None,
        )
        db.add(audit)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = jwt.create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)
    refresh_token = jwt.create_refresh_token(data={"sub": user.id}, expires_delta=refresh_token_expires)

    # Log login
    audit = AuditLog(
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request else None,
    )
    db.add(audit)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/auth/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    # Log logout
    audit = AuditLog(
        user_id=current_user.id,
        action="logout",
        ip_address=request.client.host if request else None,
    )
    db.add(audit)
    db.commit()
    return {"msg": "Successfully logged out"}


@router.post("/auth/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = jwt.decode_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/auth/me", response_model=dict)
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "roles": [role.name for role in current_user.roles],
        "is_active": current_user.is_active,
        "last_login": current_user.last_login,
    }


@router.get("/users", dependencies=[Depends(require_role("SUPER_ADMIN"))])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


@router.post("/users", dependencies=[Depends(require_role("SUPER_ADMIN"))])
def create_user(user_data: dict, db: Session = Depends(get_db)):
    # user_data should be validated schema in real implementation
    hashed_password = get_password_hash(user_data["password"])
    user = User(
        username=user_data["username"],
        full_name=user_data.get("full_name"),
        email=user_data["email"],
        hashed_password=hashed_password,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Log user creation
    audit = AuditLog(
        user_id=None,
        action="user_creation",
        target_type="user",
        target_id=str(user.id),
    )
    db.add(audit)
    db.commit()
    return user


@router.put("/users/{user_id}", dependencies=[Depends(require_role("SUPER_ADMIN"))])
def update_user(user_id: int, user_data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in user_data.items():
        if key == "password":
            setattr(user, "hashed_password", get_password_hash(value))
        elif hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    # Log user update
    audit = AuditLog(
        user_id=None,
        action="user_update",
        target_type="user",
        target_id=str(user.id),
    )
    db.add(audit)
    db.commit()
    return user


@router.delete("/users/{user_id}", dependencies=[Depends(require_role("SUPER_ADMIN"))])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    # Log user deletion
    audit = AuditLog(
        user_id=None,
        action="user_deletion",
        target_type="user",
        target_id=str(user_id),
    )
    db.add(audit)
    db.commit()
    return {"detail": "User deleted"}


@router.get("/roles")
def list_roles(db: Session = Depends(get_db)):
    roles = db.query(Role).all()
    return roles


@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db)):
    from app.models.role import Permission
    permissions = db.query(Permission).all()
    return permissions

api_router = router