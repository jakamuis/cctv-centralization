from sqlalchemy.orm import Session

from app.models.role import Role, Permission


def seed_roles_permissions(db: Session):
    # Define roles
    roles = [
        {"name": "SUPER_ADMIN", "description": "Full system access"},
        {"name": "REGIONAL_ADMIN", "description": "Access only assigned regions"},
        {"name": "BRANCH_OPERATOR", "description": "Access own branch only"},
        {"name": "VIEWER", "description": "View-only access"},
    ]

    # Define permissions
    permissions = [
        {"code": "user:manage", "description": "Manage users"},
        {"code": "branch:manage", "description": "Manage branches"},
        {"code": "permission:manage", "description": "Manage permissions"},
        {"code": "sync:google_sheets", "description": "Trigger Google Sheets sync"},
        {"code": "playback:full_access", "description": "Full playback/download access"},
        {"code": "device:view", "description": "View devices"},
        {"code": "device:edit", "description": "Edit devices"},
        {"code": "playback:view", "description": "View playback"},
        {"code": "user:view", "description": "View users"},
    ]

    # Create or get roles
    role_objs = {}
    for role_data in roles:
        role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not role:
            role = Role(name=role_data["name"], description=role_data["description"])
            db.add(role)
            db.commit()
            db.refresh(role)
        role_objs[role.name] = role

    # Create or get permissions
    perm_objs = {}
    for perm_data in permissions:
        perm = db.query(Permission).filter(Permission.code == perm_data["code"]).first()
        if not perm:
            perm = Permission(code=perm_data["code"], description=perm_data["description"])
            db.add(perm)
            db.commit()
            db.refresh(perm)
        perm_objs[perm.code] = perm

    # Assign permissions to roles
    # SUPER_ADMIN: all permissions
    role_objs["SUPER_ADMIN"].permissions = list(perm_objs.values())

    # REGIONAL_ADMIN: limited permissions
    regional_perms = [
        perm_objs["branch:manage"],
        perm_objs["device:view"],
        perm_objs["playback:view"],
        perm_objs["user:view"],
    ]
    role_objs["REGIONAL_ADMIN"].permissions = regional_perms

    # BRANCH_OPERATOR: limited permissions
    branch_operator_perms = [
        perm_objs["device:view"],
        perm_objs["playback:view"],
    ]
    role_objs["BRANCH_OPERATOR"].permissions = branch_operator_perms

    # VIEWER: view-only permissions
    viewer_perms = [
        perm_objs["device:view"],
        perm_objs["user:view"],
    ]
    role_objs["VIEWER"].permissions = viewer_perms

    # Commit all changes
    db.commit()