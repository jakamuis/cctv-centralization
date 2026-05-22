from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api.v1.api import api_router
from app.stream.manager import start_background_cleanup

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
    # Start background cleanup for idle streams
    start_background_cleanup()

# =========================
# SHUTDOWN
# =========================

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Backend application stopped")