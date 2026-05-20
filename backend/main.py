from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.db.session import async_session_maker
from app.api.v1.api import api_router

app = FastAPI(title="CCTV Centralization Backend")

# Structured logging setup
logger = logging.getLogger("uvicorn.access")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# CORS middleware example (optional, can be adjusted later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health():
    return JSONResponse(content={"status": "healthy"})

# Include API v1 router without prefix here (prefix handled in api.py)
app.include_router(api_router)

# Startup event handler
@app.on_event("startup")
async def on_startup():
    logger.info("Starting up backend application")

# Shutdown event handler
@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down backend application")

