"""Redis cache. If Redis is down, the app just runs without caching."""
import contextlib
import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    """Return the Redis client, or None if Redis is down."""
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
            )
            _client.ping()
        except redis.RedisError:
            logger.warning("Redis unavailable - running without cache")
            _client = None
    return _client


def set_client(client: redis.Redis | None) -> None:
    """Swap in a Redis client (used by tests)."""
    global _client
    _client = client


class Cache:
    """Simple JSON cache on top of Redis."""

    def __init__(self, client: redis.Redis | None) -> None:
        self.client = client

    def get(self, key: str) -> Any | None:
        if self.client is None:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except redis.RedisError:
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self.client is None:
            return
        with contextlib.suppress(redis.RedisError):
            self.client.set(
                key,
                json.dumps(value, default=str),
                ex=ttl or settings.CACHE_TTL_SECONDS,
            )

    def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching a pattern, e.g. employees:*."""
        if self.client is None:
            return
        try:
            keys = list(self.client.scan_iter(match=pattern))
            if keys:
                self.client.delete(*keys)
        except redis.RedisError:
            pass


def get_cache() -> Cache:
    return Cache(get_redis())