"""
FastAPI dependencies for the Evaluator service.

This module provides dependency injection functions for FastAPI routes.
"""

from typing import AsyncGenerator, Optional

import redis.asyncio as redis

from .config import settings


# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    FastAPI dependency that provides an async Redis client.

    Yields:
        redis.Redis: Async Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore

    try:
        yield _redis_client
    finally:
        # Redis client is reused across requests, so we don't close it here
        pass


async def close_redis_client():
    """Close the global Redis client."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
