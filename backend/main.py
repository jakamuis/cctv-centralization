from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import logging
import os

from app.core.config import settings
from app.api.v1.api import api_router
from app.stream.manager import start_background_cleanup
from app.services.playback.playback_cleanup import (
    start_playback_cleanup_worker,
    stop_playback_cleanup_worker,
)

# ---------------------------------------------------------------------------
# Logging configuration
#
# LOG_LEVEL env var controls the root logger (default: INFO).
# PLAYBACK_LOG_LEVEL controls the playback service specifically (default: DEBUG)
# so that ISAPI XML request/response bodies are always visible when debugging.
# ---------------------------------------------------------------------------

_root_level = os.environ.get("LOG_LEVEL", "INFO").upper()
_playback_level = os.environ.get("PLAYBACK_LOG_LEVEL", "DEBUG").upper()

logging.basicConfig(
    level=getattr(logging, _root_level, logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Set playback module to DEBUG so ISAPI XML bodies are logged
logging.getLogger("app.services.playback").setLevel(
    getattr(logging, _playback_level, logging.DEBUG)
)
logging.getLogger("app.api.v1.routers.playback").setLevel(
    getattr(logging, _playback_level, logging.DEBUG)
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CCTV Centralization Backend",
    version="1.0.0",
)

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HEALTH CHECK
# =========================

@app.get("/health", tags=["Health"])
async def health():
    return JSONResponse(
        content={
            "status": "healthy"
        }
    )

# =========================
# API ROUTES
# =========================

app.include_router(api_router, prefix="/api/v1")

# =========================
# STARTUP
# =========================

@app.on_event("startup")
async def on_startup():
    logger.info("Backend application started")
    # Start background cleanup for idle live streams
    start_background_cleanup()
    # Start background cleanup for expired playback sessions (Phase 9)
    start_playback_cleanup_worker()

# =========================
# SHUTDOWN
# =========================

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Backend application stopped")
    # Stop playback cleanup worker gracefully
    stop_playback_cleanup_worker()
