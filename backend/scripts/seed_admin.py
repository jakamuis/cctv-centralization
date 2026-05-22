"""
Seed script: creates an admin user with username=admin / password=admin
and assigns the SUPER_ADMIN role (creating it if it doesn't exist).

Run from inside the backend container:
    python scripts/seed_admin.py
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


async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Ensure SUPER_ADMIN role exists
        result = await session.execute(select(Role).where(Role.name == "SUPER_ADMIN"))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name="SUPER_ADMIN", description="Full system access")
            session.add(role)
            await session.flush()
            print("Created role: SUPER_ADMIN")
        else:
            print("Role SUPER_ADMIN already exists")

        # 2. Ensure admin user exists
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                username="admin",
                full_name="Administrator",
                email="admin@localhost",
                hashed_password=_hash_password("admin"),
                is_active=True,
            )
            session.add(user)
            await session.flush()
            print(f"Created user: admin (id={user.id})")
        else:
            print(f"User admin already exists (id={user.id})")

        # 3. Assign SUPER_ADMIN role to admin user (idempotent)
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
            print("Assigned SUPER_ADMIN role to admin")
        else:
            print("admin already has SUPER_ADMIN role")

        await session.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
