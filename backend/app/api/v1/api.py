from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
from app.models.role import Role, Permission
from app.models.audit_log import AuditLog

from app.security import jwt
from app.security.jwt import verify_password, get_password_hash

# IMPORT OPERATIONAL ROUTERS
from app.api.v1.routers.site import router as sites_router
from app.api.v1.routers.device import router as devices_router
from app.api.v1.routers.camera import router as cameras_router
from app.api.v1.routers.telemetry import router as telemetry_router
from app.api.v1.routers.streams import router as streams_router
from app.api.v1.routers.alerts import router as alerts_router

# Phase 7B — Discovery sync router
from app.api.v1.routers.discovery import router as discovery_router

# Import new endpoints
from app.api.v1.endpoints.branches import router as branches_router
from app.api.v1.endpoints.cameras import router as cameras_v2_router


router = APIRouter()


# =========================
# AUTH
# =========================

@router.post("/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):

        audit = AuditLog(
            user_id=user.id if user else None,
            action="failed_login",
            ip_address=request.client.host if request else None,
        )

        db.add(audit)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(
        minutes=settings.security.jwt_access_token_expire_minutes
    )

    access_token = jwt.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    audit = AuditLog(
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request else None,
    )

    db.add(audit)
    await db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    audit = AuditLog(
        user_id=current_user.id,
        action="logout",
        ip_address=request.client.host if request else None,
    )

    db.add(audit)
    await db.commit()

    return {"msg": "Successfully logged out"}


@router.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "roles": [role.name for role in current_user.roles],
        "is_active": current_user.is_active,
    }


# =========================
# USERS
# =========================

@router.get("/users", dependencies=[Depends(require_role("SUPER_ADMIN"))])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()


@router.post("/users", dependencies=[Depends(require_role("SUPER_ADMIN"))])
async def create_user(user_data: dict, db: AsyncSession = Depends(get_db)):

    hashed_password = get_password_hash(user_data["password"])

    user = User(
        username=user_data["username"],
        full_name=user_data.get("full_name"),
        email=user_data["email"],
        hashed_password=hashed_password,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    audit = AuditLog(
        user_id=None,
        action="user_creation",
        target_type="user",
        target_id=str(user.id),
    )

    db.add(audit)
    await db.commit()

    return user


@router.put("/users/{user_id}", dependencies=[Depends(require_role("SUPER_ADMIN"))])
async def update_user(user_id: int, user_data: dict, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user_data.items():

        if key == "password":
            setattr(user, "hashed_password", get_password_hash(value))

        elif hasattr(user, key):
            setattr(user, key, value)

    await db.commit()

    audit = AuditLog(
        user_id=None,
        action="user_update",
        target_type="user",
        target_id=str(user.id),
    )

    db.add(audit)
    await db.commit()

    return user


@router.delete("/users/{user_id}", dependencies=[Depends(require_role("SUPER_ADMIN"))])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()

    audit = AuditLog(
        user_id=None,
        action="user_deletion",
        target_type="user",
        target_id=str(user_id),
    )

    db.add(audit)
    await db.commit()

    return {"detail": "User deleted"}


@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role))
    return result.scalars().all()


@router.get("/permissions")
async def list_permissions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Permission))
    return result.scalars().all()


# =========================
# OPERATIONAL APIs
# =========================

router.include_router(sites_router)

router.include_router(devices_router)

router.include_router(cameras_router)

router.include_router(telemetry_router)

router.include_router(alerts_router)

# Include new routers
router.include_router(branches_router)
router.include_router(cameras_v2_router)
router.include_router(streams_router)

# Phase 7B — Discovery
router.include_router(discovery_router)

api_router = router
