"""
CogniCompanion — FastAPI Application Entry Point
=================================================
Configures:
  - CORS
  - Static file serving (uploads/)
  - All domain routers
  - Event handler registration
  - Startup health check
  - OpenAPI metadata
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.rate_limiter import RateLimitMiddleware
from app.core.body_size_limit import RequestSizeLimitMiddleware
from app.events.bus import event_bus
from app.events.handlers import register_event_handlers

# ── Domain Routers ────────────────────────────────────────────────────────────
from app.domains.auth.router import router as auth_router
from app.domains.patients.router import router as patients_router
from app.domains.memories.router import router as memories_router
from app.domains.timeline.router import router as timeline_router
from app.domains.games.router import router as games_router
from app.domains.voice.router import router as voice_router
from app.domains.analytics.router import router as analytics_router

settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup:
      - Register event handlers on the in-process event bus.
      - Future: warm up AI providers, verify DB connection.

    Shutdown:
      - Graceful cleanup (if needed).
    """
    register_event_handlers(event_bus)
    yield
    # Shutdown tasks go here


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="CogniCompanion API",
    description=(
        "AI-Based Cognitive Gaming and Memory Assistance Platform "
        "for Elderly Dementia Patients.\n\n"
        "**CPI is an assistive performance indicator and is NOT a medical diagnosis.**"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security Hardening Middlewares ───────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware, auth_limit=15, ai_limit=35, general_limit=300)

# ── Static Files (uploaded media) ─────────────────────────────────────────────
import os

os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────

API_PREFIX = settings.API_V1_PREFIX

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(patients_router, prefix=API_PREFIX)
app.include_router(memories_router, prefix=API_PREFIX)
app.include_router(timeline_router, prefix=API_PREFIX)
app.include_router(games_router, prefix=API_PREFIX)
app.include_router(voice_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="API health check")
async def health() -> dict:
    """Returns application status. Used by deployment health checks."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }
