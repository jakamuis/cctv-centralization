from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch


class BranchRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, branch_id: UUID):
        result = await self.db.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
    ):
        query = select(Branch)

        total_query = select(func.count()).select_from(
            query.subquery()
        )

        total_result = await self.db.execute(total_query)

        total = total_result.scalar()

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)

        items = result.scalars().all()

        return {
            "total": total,
            "items": items,
        }