from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from typing import Optional, List
import uuid

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, user_sites
from app.security import jwt
from app.models.role import Role
from app.models.camera import Camera
from app.models.site import Site

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode_token(token)
        if not payload:
            raise credentials_exception
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.sites),
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(role_name: str):
    def role_checker(user: User = Depends(get_current_user)):
        if not user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role_name}",
            )
        return user

    return role_checker


def require_permission(permission_code: str):
    def permission_checker(user: User = Depends(get_current_user)):
        user_permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                user_permissions.add(perm.code)
        if permission_code not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required permission: {permission_code}",
            )
        return user

    return permission_checker


async def get_current_user_stream(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Like get_current_user but also accepts ?token= query param.
    Used only for media stream endpoints where <video src> can't send headers.
    """
    token: Optional[str] = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode_token(token)
        if not payload:
            raise credentials_exception
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.sites),
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def user_has_permission(user: User, permission_code: str) -> bool:
    perms = {perm.code for role in user.roles for perm in role.permissions}
    return permission_code in perms


def has_camera_access(user: User, camera: Camera) -> bool:
    if user.has_any_role(["ADMIN", "IT", "MANAGER"]):
        return True
    if user.has_role("REGIONAL"):
        allowed = {site.id for site in user.sites}
        return camera.site_id in allowed if hasattr(camera, "site_id") else False
    return False


def get_allowed_site_ids(user: User):
    """
    Returns list of allowed site UUIDs, or None meaning 'all sites'.
    ADMIN / IT / MANAGER → None (unrestricted).
    REGIONAL → explicit list from user_sites.
    """
    if user.has_any_role(["ADMIN", "IT", "MANAGER"]):
        return None
    return [site.id for site in user.sites]


def require_site_access(site_id):
    """
    Dependency factory: raises 403 if a REGIONAL user does not have access to site_id.
    Pass the site UUID directly or as a path param dependency.
    """
    async def checker(user: User = Depends(get_current_user)):
        if user.has_any_role(["ADMIN", "IT", "MANAGER"]):
            return user
        allowed = {site.id for site in user.sites}
        if site_id not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this site",
            )
        return user
    return checker