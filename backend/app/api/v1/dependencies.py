from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.security import jwt
from app.models.role import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode_token(token)
        if not payload:
            raise credentials_exception
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
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


def require_branch_access(branch_id: int, user: User = Depends(get_current_user)):
    # SUPER_ADMIN bypass
    if user.has_role("SUPER_ADMIN"):
        return user

    # REGIONAL_ADMIN can access branches in their regions
    if user.has_role("REGIONAL_ADMIN"):
        user_regions = {branch.region_id for branch in user_branches(user)}
        from app.db.session import get_db
        db = next(get_db())
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if branch and branch.region_id in user_regions:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this branch",
        )

    # BRANCH_OPERATOR can access own branch only
    if user.has_role("BRANCH_OPERATOR"):
        user_branch_ids = {branch.id for branch in user_branches(user)}
        if branch_id in user_branch_ids:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this branch",
        )

    # VIEWER or others no access by default
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User does not have access to this branch",
    )


def user_branches(user: User):
    # This function should return branches assigned to the user
    # Placeholder: implement actual user-branch relationship
    return []