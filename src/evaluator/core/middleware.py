"""Application middleware utilities for the Evaluator service."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from evaluator.config import settings


def add_api_key_auth_middleware(app: FastAPI) -> None:
    """Attach API key authentication middleware to the FastAPI app."""

    @app.middleware("http")
    async def api_key_auth_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[JSONResponse]],
    ):
        public_paths = {
            "/api/v1/health",
            "/api/v1/version",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

        # Always allow public metadata endpoints and CORS preflight requests.
        if request.method == "OPTIONS" or request.url.path in public_paths:
            return await call_next(request)

        provided_api_key = request.headers.get("API_KEY")
        expected_api_key = settings.evaluation_service_api_key

        if not provided_api_key or not secrets.compare_digest(
            provided_api_key, expected_api_key
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "status": status.HTTP_401_UNAUTHORIZED,
                },
            )

        return await call_next(request)
