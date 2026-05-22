from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import Camera


class CameraRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload):

        if isinstance(payload, Camera):

            self.db.add(payload)

            await self.db.commit()

            await self.db.refresh(payload)

            return payload

        if hasattr(payload, "model_dump"):
            data = payload.model_dump()
        else:
            data = {
                k: v
                for k, v in payload.__dict__.items()
                if not k.startswith("_")
            }

        camera = Camera(**data)

        self.db.add(camera)

        await self.db.commit()

        await self.db.refresh(camera)

        return camera

    async def get(
        self,
        camera_id,
        include_deleted: bool = False
    ):

        query = select(Camera).where(
            Camera.id == camera_id
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_by_id(self, camera_id: UUID):

        result = await self.db.execute(
            select(Camera).where(
                Camera.id == camera_id
            )
        )

        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        branch_id: Optional[UUID] = None,
        enabled: Optional[bool] = None,
    ):

        query = select(Camera)

        if branch_id:
            query = query.where(
                Camera.branch_id == branch_id
            )

        if enabled is not None:
            query = query.where(
                Camera.enabled == enabled
            )

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

    async def update(self, camera, payload):

        if hasattr(payload, "model_dump"):
            data = payload.model_dump(exclude_unset=True)
        else:
            data = {
                k: v
                for k, v in payload.__dict__.items()
                if not k.startswith("_")
            }

        for key, value in data.items():
            setattr(camera, key, value)

        if hasattr(camera, "updated_at"):
            camera.updated_at = datetime.utcnow()

        await self.db.commit()

        await self.db.refresh(camera)

        return camera

    async def soft_delete(self, camera):

        await self.db.delete(camera)

        await self.db.commit()

        return True

    async def restore(self, camera):

        return camera