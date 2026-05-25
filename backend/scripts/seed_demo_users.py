"""
Seed script: creates three demo users for testing the role-based UI.

Users created (idempotent — safe to run multiple times):
  admin    / admin123    → role: SUPER_ADMIN  (full access)
  operator / operator123 → role: OPERATOR     (monitoring, playback, alerts)
  viewer   / viewer123   → role: VIEWER       (monitoring only)

Run from inside the backend container:
    python scripts/seed_demo_users.py

Or from the project root (with venv active):
    cd backend && python scripts/seed_demo_users.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User, user_roles
from app.models.role import Role
from app.models.base import Base  # noqa – ensures metadata is populated
import app.models  # noqa – registers all models

DATABASE_URL = settings.database.get_database_url()

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def _hash_password(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ─── Demo accounts ────────────────────────────────────────────────────────────
# Each entry: (username, password, role_name, full_name, email)
DEMO_USERS = [
    ("admin",    "admin123",    "SUPER_ADMIN", "Administrator",    "admin@samator.id"),
    ("operator", "operator123", "OPERATOR",    "Operator User",    "operator@samator.id"),
    ("viewer",   "viewer123",   "VIEWER",      "Viewer User",      "viewer@samator.id"),
]

# Role descriptions
ROLE_DESCRIPTIONS = {
    "SUPER_ADMIN": "Full system access — all menus and management features",
    "OPERATOR":    "Operational access — Monitoring, Playback, Alerts",
    "VIEWER":      "Read-only access — Monitoring only",
}


async def ensure_role(session: AsyncSession, role_name: str) -> Role:
    """Get or create a role by name."""
    result = await session.execute(select(Role).where(Role.name == role_name))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(
            name=role_name,
            description=ROLE_DESCRIPTIONS.get(role_name, ""),
        )
        session.add(role)
        await session.flush()
        print(f"  [+] Created role: {role_name}")
    else:
        print(f"  [=] Role already exists: {role_name}")
    return role


async def ensure_user(
    session: AsyncSession,
    username: str,
    password: str,
    role: Role,
    full_name: str,
    email: str,
) -> User:
    """Get or create a user, then ensure they have the given role."""
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            username=username,
            full_name=full_name,
            email=email,
            hashed_password=_hash_password(password),
            is_active=True,
        )
        session.add(user)
        await session.flush()
        print(f"  [+] Created user: {username} (id={user.id})")
    else:
        # Update password so demo credentials always work
        user.hashed_password = _hash_password(password)
        user.is_active = True
        await session.flush()
        print(f"  [=] User already exists: {username} (id={user.id}) — password refreshed")

    # Assign role (idempotent)
    result = await session.execute(
        select(user_roles).where(
            user_roles.c.user_id == user.id,
            user_roles.c.role_id == role.id,
        )
    )
    if result.first() is None:
        await session.execute(
            user_roles.insert().values(user_id=user.id, role_id=role.id)
        )
        print(f"  [+] Assigned role {role.name} to {username}")
    else:
        print(f"  [=] {username} already has role {role.name}")

    return user


async def seed():
    print("=" * 55)
    print("  SAMATOR — Demo User Seed Script")
    print("=" * 55)

    async with AsyncSessionLocal() as session:
        for username, password, role_name, full_name, email in DEMO_USERS:
            print(f"\n→ {username} / {password}  [{role_name}]")
            role = await ensure_role(session, role_name)
            await ensure_user(session, username, password, role, full_name, email)

        await session.commit()

    print("\n" + "=" * 55)
    print("  Done! Demo accounts ready:")
    print("  admin    / admin123    → SUPER_ADMIN (full access)")
    print("  operator / operator123 → OPERATOR    (monitoring, playback, alerts)")
    print("  viewer   / viewer123   → VIEWER      (monitoring only)")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(seed())
