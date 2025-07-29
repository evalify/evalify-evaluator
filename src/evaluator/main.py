"""
Main FastAPI application for the Evaluator service.

This module initializes the FastAPI app, sets up dependencies,
and includes all API routers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .dependencies import close_redis_client
from .version import __version__, get_version_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup - no initialization needed as Redis connection is lazy
    yield
    # Shutdown - close Redis connection
    await close_redis_client()


# Initialize FastAPI application
app = FastAPI(
    title="Evalify's Evaluator",
    description="Evaluation Backend for Evalify",
    version=__version__,
    lifespan=lifespan,
    debug=settings.debug_mode,
)

# Add CORS middleware if origins are configured
if settings.allowed_origins or settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=settings.allowed_methods_list,
        allow_headers=[settings.allowed_headers]
        if settings.allowed_headers != "*"
        else ["*"],
    )


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint to verify service is running."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": __version__,
    }


@app.get("/api/v1/version")
async def version_info():
    """Get detailed version information."""
    return get_version_info()
