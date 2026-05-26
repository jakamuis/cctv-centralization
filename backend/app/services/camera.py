# backend/app/services/camera.py

from app.models.camera import Camera
from app.repositories.camera import CameraRepository


class CameraService:

    def __init__(self, session):
        self.repo = CameraRepository(session)

    async def create_camera(self, camera_in):

        raw = camera_in.model_dump()

        allowed_fields = {
            "branch_id",
            "name",
            "stream_name",
            "rtsp_channel",
            "status",
            "enabled",
        }

        data = {
            k: v
            for k, v in raw.items()
            if k in allowed_fields and v is not None
        }

        camera = Camera(**data)

        return await self.repo.create(camera)

    async def get_camera(
        self,
        camera_id,
        include_deleted: bool = False
    ):

        return await self.repo.get(
            camera_id,
            include_deleted=include_deleted
        )

    async def list_cameras(
        self,
        skip: int = 0,
        limit: int = 100,
        **kwargs
    ):

        device_id = kwargs.get("device_id")

        result = await self.repo.list(
            skip=skip,
            limit=limit,
            device_id=device_id,
        )

        return result["items"]

    async def count_cameras(
        self,
        **kwargs
    ):

        device_id = kwargs.get("device_id")

        result = await self.repo.list(
            skip=0,
            limit=100000,
            device_id=device_id,
        )

        return result["total"]

    async def update_camera(
        self,
        camera,
        camera_in
    ):

        return await self.repo.update(
            camera,
            camera_in
        )

    async def soft_delete_camera(self, camera):

        return await self.repo.soft_delete(camera)

    async def restore_camera(self, camera):

        return await self.repo.restore(camera)
