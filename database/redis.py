import os

from redis import Redis


redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)


def get_redis_client() -> Redis:
    """Return the shared Redis client."""
    return redis_client
