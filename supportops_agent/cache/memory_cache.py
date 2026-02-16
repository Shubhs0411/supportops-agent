"""In-memory caching with TTL support."""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        logger.info(f"MemoryCache initialized with TTL={default_ttl}s")

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            "prefix": prefix,
            "args": args,
            "kwargs": sorted(kwargs.items()) if kwargs else {},
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"{prefix}:{hashlib.sha256(key_str.encode()).hexdigest()[:16]}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() > entry["expires_at"]:
            # Expired, remove it
            del self._cache[key]
            return None

        entry["hits"] = entry.get("hits", 0) + 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
            "hits": 0,
        }

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        total_hits = sum(entry.get("hits", 0) for entry in self._cache.values())
        expired = sum(1 for entry in self._cache.values() if time.time() > entry["expires_at"])

        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "expired_entries": expired,
            "active_entries": total_entries - expired,
        }


# Global cache instance
_cache_instance: Optional[MemoryCache] = None


def get_cache() -> MemoryCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MemoryCache(default_ttl=3600)
    return _cache_instance
