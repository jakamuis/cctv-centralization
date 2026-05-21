from fastapi import APIRouter, Depends

from app.api.v1.dependencies import require_role, require_permission, get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/admin-only")
def admin_only_endpoint(user: User = Depends(require_role("SUPER_ADMIN"))):
    return {"message": f"Hello, {user.username}. You have SUPER_ADMIN access."}


@router.get("/device-edit")
def device_edit_endpoint(user: User = Depends(require_permission("device:edit"))):
    return {"message": f"Hello, {user.username}. You have permission to edit devices."}


@router.get("/branch-access/{branch_id}")
def branch_access_endpoint(branch_id: int, user: User = Depends()):
    # This example assumes require_branch_access is used in dependencies.py
    from app.api.v1.dependencies import require_branch_access

    user = require_branch_access(branch_id, user)
    return {"message": f"Hello, {user.username}. You have access to branch {branch_id}."}