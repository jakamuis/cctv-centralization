from sqlalchemy.orm import Session

from app.models.role import Role, Permission


def seed_roles_permissions(db: Session):
    # Define roles
    roles = [
        {"name": "SUPER_ADMIN", "description": "Full system access"},
        {"name": "ADMIN", "description": "Administrative access"},
        {"name": "OPERATOR", "description": "Operate live streams"},
        {"name": "VIEWER", "description": "View-only access"},
        {"name": "AUDITOR", "description": "Audit and review access"},
        {"name": "VENDOR", "description": "Third-party limited access"},
        # keep legacy for backward compatibility
        {"name": "REGIONAL_ADMIN", "description": "Access only assigned regions"},
        {"name": "BRANCH_OPERATOR", "description": "Access own branch only"},
    ]

    # Define permissions
    permissions = [
        # Core RBAC
        {"code": "user:manage", "description": "Manage users"},
        {"code": "branch:manage", "description": "Manage branches"},
        {"code": "permission:manage", "description": "Manage permissions"},
        {"code": "user:view", "description": "View users"},

        # Devices/cameras
        {"code": "device.manage", "description": "Manage devices"},
        {"code": "camera.view", "description": "View cameras"},

        # Streaming/playback
        {"code": "stream.live", "description": "Start/view live streams"},
        {"code": "playback.view", "description": "View playback"},
        {"code": "playback.download", "description": "Download playback"},
        {"code": "ptz.control", "description": "Control PTZ"},

        # Legacy/misc
        {"code": "sync:google_sheets", "description": "Trigger Google Sheets sync"},
        {"code": "playback:full_access", "description": "Full playback/download access"},
        {"code": "device:view", "description": "View devices (legacy)"},
        {"code": "device:edit", "description": "Edit devices (legacy)"},
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

    # Assign permissions to roles (new mapping)
    # SUPER_ADMIN: all permissions
    role_objs["SUPER_ADMIN"].permissions = list(perm_objs.values())

    # ADMIN: manage devices, view playback, start streams, camera view
    admin_perms = [
        perm_objs["device.manage"],
        perm_objs["camera.view"],
        perm_objs["stream.live"],
        perm_objs["playback.view"],
        perm_objs["ptz.control"],
    ]
    if "ADMIN" in role_objs:
        role_objs["ADMIN"].permissions = admin_perms

    # OPERATOR: live streams + camera view
    operator_perms = [
        perm_objs["camera.view"],
        perm_objs["stream.live"],
        perm_objs["playback.view"],
    ]
    if "OPERATOR" in role_objs:
        role_objs["OPERATOR"].permissions = operator_perms

    # VIEWER: camera view + playback.view
    viewer_perms = [
        perm_objs["camera.view"],
        perm_objs["playback.view"],
    ]
    role_objs["VIEWER"].permissions = viewer_perms

    # AUDITOR: view-only, no live start
    auditor_perms = [
        perm_objs["camera.view"],
        perm_objs["playback.view"],
    ]
    if "AUDITOR" in role_objs:
        role_objs["AUDITOR"].permissions = auditor_perms

    # VENDOR: minimal camera view
    vendor_perms = [
        perm_objs["camera.view"],
    ]
    if "VENDOR" in role_objs:
        role_objs["VENDOR"].permissions = vendor_perms

    # Back-compat roles
    regional_perms = [
        perm_objs["camera.view"],
        perm_objs["stream.live"],
        perm_objs["playback.view"],
    ]
    role_objs["REGIONAL_ADMIN"].permissions = regional_perms

    branch_operator_perms = [
        perm_objs["camera.view"],
        perm_objs["stream.live"],
        perm_objs["playback.view"],
    ]
    role_objs["BRANCH_OPERATOR"].permissions = branch_operator_perms

    # Commit all changes
    db.commit()