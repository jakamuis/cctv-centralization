from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.auth import router as auth_router
from app.devices import router as devices_router
from app.audit import router as audit_router
from app.stream import router as stream_router
from app.playback import router as playback_router

api_router = APIRouter(prefix="/api/v1")

@api_router.get("/test", tags=["test"])
async def test():
    return JSONResponse(content={"message": "API v1 working"})

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(devices_router, prefix="/devices", tags=["devices"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(stream_router, prefix="/stream", tags=["stream"])
api_router.include_router(playback_router, prefix="/playback", tags=["playback"])

# Placeholder for future v1 API routes
# Example:
# from .endpoints import devices
# api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
