import redis
import redis.asyncio
from ..config import settings


def get_async_redis_client() -> redis.asyncio.Redis:
    """
    Returns an async Redis client instance connected to the configured URL.
    This is intended for use with async frameworks like FastAPI.
    """
    # Using a connection pool is best practice for managing connections efficiently.
    return redis.asyncio.from_url(settings.redis_url, decode_responses=True)


def get_sync_redis_client() -> redis.Redis:
    """
    Returns a synchronous Redis client instance.
    This is useful for synchronous contexts like Celery's default workers.
    """
    return redis.from_url(settings.redis_url, decode_responses=True)
