"""
Cache Service - Redis Cache Layer

Provides Redis caching for the stock prediction platform.
This is an OPTIMIZATION layer - Redis failures should not break the application.

Features:
- JSON serialization
- TTL management
- Connection pooling
- Graceful degradation
- Cache-aside pattern
- Upstash Redis support
"""

import json
import logging
import os
from typing import Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import redis, but handle gracefully if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not available, using in-memory fallback")


# ============================================================================
# REDIS CACHE CLASS
# ============================================================================

class RedisCache:
    """
    Redis cache with graceful fallback to in-memory cache.

    Supports Upstash Redis (REST API) and standard Redis.
    If Redis is unavailable, all operations silently fall back to
    in-memory caching to ensure the application remains functional.
    """

    def __init__(self, redis_url: str = None, prefix: str = "stockpred:"):
        self.prefix = prefix
        self._redis = None
        self._memory_cache = {}  # Fallback in-memory cache
        self._memory_timestamps = {}
        self._is_upstash = False

        # Get Redis URL from environment if not provided
        if not redis_url:
            redis_url = os.environ.get('REDIS_URL', '')

        if REDIS_AVAILABLE and redis_url:
            try:
                # Check if this is an Upstash URL (contains .upstash.io)
                if 'upstash' in redis_url.lower():
                    self._is_upstash = True
                    # Upstash uses REST API, need to use different connection
                    redis_token = os.environ.get('REDIS_TOKEN', '')
                    if redis_token:
                        self._redis = self._create_upstash_client(redis_url, redis_token)
                    else:
                        logger.warning("Upstash Redis selected but REDIS_TOKEN not set")
                else:
                    # Standard Redis connection
                    self._redis = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )

                # Test connection
                if self._redis:
                    self._redis.ping()
                    logger.info(f"Redis connection established (Upstash: {self._is_upstash})")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
                self._redis = None
                self._is_upstash = False
        elif not REDIS_AVAILABLE:
            logger.info("Redis package not installed, using in-memory fallback")

    def _create_upstash_client(self, redis_url: str, token: str):
        """Create an Upstash Redis client using REST API."""
        try:
            # Upstash REST API client
            from upstash_redis import UpstashRedis
            return UpstashRedis(url=redis_url, token=token)
        except ImportError:
            # Fallback: use HTTP client directly
            logger.info("Using HTTP fallback for Upstash")
            return self._UpstashHttpClient(redis_url, token)

    class _UpstashHttpClient:
        """Simple HTTP client for Upstash Redis REST API."""
        def __init__(self, url: str, token: str):
            self.url = url
            self.token = token
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            })

        def ping(self) -> bool:
            try:
                resp = self.session.get(self.url)
                return resp.status_code == 200
            except Exception:
                return False

        def get(self, key: str) -> Optional[str]:
            try:
                resp = self.session.get(f"{self.url}/get/{key}")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('result')
                return None
            except Exception as e:
                logger.warning(f"Upstash GET error: {e}")
                return None

        def setex(self, key: str, ttl: int, value: str) -> bool:
            try:
                resp = self.session.post(
                    f"{self.url}/set/{key}",
                    json={"value": value, "ex": ttl}
                )
                return resp.status_code == 200
            except Exception as e:
                logger.warning(f"Upstash SET error: {e}")
                return False

        def delete(self, key: str) -> bool:
            try:
                resp = self.session.delete(f"{self.url}/del/{key}")
                return resp.status_code == 200
            except Exception as e:
                logger.warning(f"Upstash DELETE error: {e}")
                return False

        def keys(self, pattern: str) -> list:
            try:
                # Upstash KEYS command
                resp = self.session.post(
                    f"{self.url}/keys",
                    json={"pattern": pattern}
                )
                if resp.status_code == 200:
                    return resp.json().get('result', [])
                return []
            except Exception as e:
                logger.warning(f"Upstash KEYS error: {e}")
                return []

        def info(self, section: str = None) -> dict:
            # Not fully implemented for Upstash
            return {}

    def _make_key(self, key: str) -> str:
        """Prefix key with namespace."""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Returns None on cache miss or Redis failure (graceful fallback).
        """
        full_key = self._make_key(key)

        # Try Redis first
        if self._redis:
            try:
                value = self._redis.get(full_key)
                if value:
                    logger.debug(f"Redis HIT: {key}")
                    return json.loads(value)
                logger.debug(f"Redis MISS: {key}")
                return None
            except Exception as e:
                logger.warning(f"Redis GET error: {e}")

        # Fallback to memory cache
        if key in self._memory_cache:
            from time import time
            value, expiry = self._memory_cache[key]
            if time() < expiry:
                logger.debug(f"Memory cache HIT: {key}")
                return value
            del self._memory_cache[key]

        logger.debug(f"Cache MISS: {key}")
        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """
        Set value in cache with TTL.

        Returns True on success, False on failure (graceful fallback).
        """
        full_key = self._make_key(key)

        # Serialize value
        try:
            serialized = json.dumps(value)
        except Exception as e:
            logger.error(f"JSON serialization failed: {e}")
            return False

        # Try Redis first
        if self._redis:
            try:
                self._redis.setex(full_key, ttl, serialized)
                logger.debug(f"Redis SET: {key} (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.warning(f"Redis SET error: {e}")

        # Fallback to memory cache
        from time import time
        expiry = time() + ttl
        self._memory_cache[key] = (value, expiry)
        logger.debug(f"Memory cache SET: {key} (TTL: {ttl}s)")
        return True

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        full_key = self._make_key(key)

        if self._redis:
            try:
                self._redis.delete(full_key)
                logger.debug(f"Redis DELETE: {key}")
            except Exception as e:
                logger.warning(f"Redis DELETE error: {e}")

        # Also delete from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]

        return True

    def clear(self, pattern: str = "*") -> int:
        """
        Clear all keys matching pattern.

        Returns number of keys deleted.
        """
        deleted = 0

        if self._redis:
            try:
                full_pattern = self._make_key(pattern)
                keys = self._redis.keys(full_pattern)
                if keys:
                    deleted = len(keys)
                    self._redis.delete(*keys)
                    logger.info(f"Redis CLEAR: deleted {deleted} keys")
            except Exception as e:
                logger.warning(f"Redis CLEAR error: {e}")

        # Clear memory cache
        if pattern == "*":
            deleted += len(self._memory_cache)
            self._memory_cache.clear()
            logger.info("Memory cache CLEAR: deleted all keys")

        return deleted

    def get_many(self, keys: list) -> dict:
        """Get multiple keys at once."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, data: dict, ttl: int = 60) -> bool:
        """Set multiple keys at once."""
        success = True
        for key, value in data.items():
            if not self.set(key, value, ttl):
                success = False
        return success

    def is_redis_available(self) -> bool:
        """Check if Redis is available."""
        if not self._redis:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            return False

    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = {
            "redis_available": self.is_redis_available(),
            "memory_cache_size": len(self._memory_cache),
            "prefix": self.prefix
        }

        if self._redis and self.is_redis_available():
            try:
                info = self._redis.info("stats")
                stats["redis_connected"] = True
                stats["hits"] = info.get("keyspace_hits", 0)
                stats["misses"] = info.get("keyspace_misses", 0)
            except Exception:
                stats["redis_connected"] = False
        else:
            stats["redis_connected"] = False

        return stats


# ============================================================================
# CACHE KEY BUILDERS
# ============================================================================

class CacheKeys:
    """Standardized cache key builders."""

    @staticmethod
    def live_price(symbol: str) -> str:
        return f"price:live:{symbol.upper()}"

    @staticmethod
    def historical(symbol: str, period: str = "1y") -> str:
        return f"price:hist:{symbol.upper()}:{period}"

    @staticmethod
    def stock_summary(symbol: str) -> str:
        return f"stock:summary:{symbol.upper()}"

    @staticmethod
    def market_movers() -> str:
        return "market:movers"

    @staticmethod
    def market_news(category: str = "general") -> str:
        return f"market:news:{category}"

    @staticmethod
    def portfolio(user_id: str) -> str:
        return f"portfolio:summary:{user_id}"

    @staticmethod
    def prediction(symbol: str, days: int) -> str:
        return f"prediction:{symbol.upper()}:{days}d"

    @staticmethod
    def stock_info(symbol: str) -> str:
        return f"stock:info:{symbol.upper()}"


# ============================================================================
# CACHE TTLs
# ============================================================================

class CacheTTLs:
    """Standardized TTL values in seconds."""

    LIVE_PRICE = 30           # 30 seconds
    HISTORICAL = 300          # 5 minutes
    NEWS = 600                # 10 minutes
    MOVERS = 60               # 1 minute
    PORTFOLIO = 60             # 1 minute
    PREDICTION = 300          # 5 minutes
    STOCK_INFO = 300          # 5 minutes


# ============================================================================
# CACHED FUNCTION DECORATOR
# ============================================================================

def cached(key_builder, ttl: int = 60, skip_cache: bool = False):
    """
    Decorator for caching function results.

    Usage:
        @cached(lambda symbol: CacheKeys.live_price(symbol), ttl=30)
        def get_live_price(symbol):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function arguments
            if callable(key_builder):
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = key_builder

            # Get cache instance
            cache = _get_cache()

            # Check cache first (unless explicitly skipped)
            if not skip_cache:
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    logger.info(f"CACHE HIT: {cache_key}")
                    return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            if result is not None:
                cache.set(cache_key, result, ttl)
                logger.info(f"CACHE SET: {cache_key} (TTL: {ttl}s)")

            return result

        return wrapper
    return decorator


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_cache_instance = None


def init_cache(redis_url: str = None, redis_token: str = None) -> RedisCache:
    """Initialize the cache singleton."""
    global _cache_instance
    if _cache_instance is None:
        # Get from environment if not provided
        if not redis_url:
            redis_url = os.environ.get('REDIS_URL', '')
        if not redis_token:
            redis_token = os.environ.get('REDIS_TOKEN', '')

        _cache_instance = RedisCache(
            redis_url=redis_url,
            prefix="stockpred:"
        )
    return _cache_instance


def _get_cache() -> RedisCache:
    """Get or create cache instance."""
    global _cache_instance
    if _cache_instance is None:
        # Try to get from environment
        redis_url = os.environ.get("REDIS_URL")
        redis_token = os.environ.get("REDIS_TOKEN")
        _cache_instance = RedisCache(
            redis_url=redis_url,
            prefix="stockpred:"
        )
    return _cache_instance


def get_cache() -> RedisCache:
    """Get the cache singleton instance."""
    return _get_cache()


def clear_all_cache() -> int:
    """Clear all cache entries."""
    return _get_cache().clear("*")


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return _get_cache().get_stats()