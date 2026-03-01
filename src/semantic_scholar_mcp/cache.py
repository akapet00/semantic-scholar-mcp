"""In-memory TTL cache for API responses."""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from semantic_scholar_mcp.logging_config import get_logger

__all__ = [
    "CacheConfig",
    "CacheEntry",
    "ResponseCache",
    "get_cache",
]

logger = get_logger("cache")


@dataclass
class CacheEntry:
    """A cached value with expiration time.

    Attributes:
        value: The cached response data.
        expires_at: Timestamp when this entry expires (using monotonic time).
        endpoint: The original endpoint for pattern-based invalidation.
    """

    value: dict[str, Any]
    expires_at: float
    endpoint: str

    @property
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.monotonic() > self.expires_at


@dataclass
class CacheConfig:
    """Cache configuration.

    Attributes:
        enabled: Whether caching is enabled.
        default_ttl: Default time-to-live in seconds.
        paper_details_ttl: TTL for paper details in seconds.
        search_ttl: TTL for search results in seconds.
        max_entries: Maximum number of cached entries.
    """

    enabled: bool = True
    default_ttl: int = 300  # 5 minutes
    paper_details_ttl: int = 3600  # 1 hour for paper details
    search_ttl: int = 300  # 5 minutes for search results
    max_entries: int = 1000  # Max cached entries


class ResponseCache:
    """Thread-safe in-memory cache with TTL support.

    Features:
    - TTL-based expiration
    - LRU eviction when max entries reached
    - Thread-safe operations
    - Endpoint-specific TTLs
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Initialize the response cache.

        Args:
            config: Cache configuration. Uses defaults if not provided.
        """
        self._config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0}

    @staticmethod
    def _make_key(endpoint: str, params: dict[str, Any] | None = None) -> str:
        """Generate cache key from endpoint and params using SHA256 hash."""
        key_data = {"endpoint": endpoint, "params": params or {}}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Get cached response if available and not expired.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Cached response or None if not found/expired.
        """
        if not self._config.enabled:
            return None

        key = self._make_key(endpoint, params)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            # Move to end for LRU (O(1) with OrderedDict)
            self._cache.move_to_end(key)

            self._stats["hits"] += 1
            logger.debug("Cache hit for %s", endpoint)
            return entry.value

    def set(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        value: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Cache a response.

        Args:
            endpoint: API endpoint.
            params: Request parameters.
            value: Response to cache.
            ttl: Time-to-live in seconds (uses endpoint-specific default if not specified).
        """
        if not self._config.enabled:
            return

        key = self._make_key(endpoint, params)

        # Determine TTL based on endpoint
        if ttl is None:
            if "/paper/" in endpoint and "/search" not in endpoint:
                ttl = self._config.paper_details_ttl
            else:
                ttl = self._config.search_ttl

        expires_at = time.monotonic() + ttl

        with self._lock:
            # If key exists, remove it first (will be re-added at end)
            if key in self._cache:
                del self._cache[key]

            # Evict oldest if at capacity (O(1) with OrderedDict)
            while len(self._cache) >= self._config.max_entries:
                self._cache.popitem(last=False)  # Remove oldest

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at, endpoint=endpoint)
            logger.debug("Cached response for %s (ttl=%ds)", endpoint, ttl)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0}

    def invalidate(self, endpoint_pattern: str) -> int:
        """Invalidate cached entries matching pattern.

        Args:
            endpoint_pattern: Substring to match in endpoint (e.g., "/paper/")

        Returns:
            Number of entries invalidated.
        """
        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items() if endpoint_pattern in entry.endpoint
            ]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with entries, hits, misses, and hit_rate.
        """
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0.0
            return {
                "entries": len(self._cache),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": hit_rate,
            }


# Global cache instance
_cache: ResponseCache | None = None
_cache_lock = threading.Lock()


def get_cache() -> ResponseCache:
    """Get or create the global cache instance.

    Uses double-checked locking pattern with threading.Lock for thread-safety.
    Initializes CacheConfig from settings.

    Returns:
        The global ResponseCache singleton instance.
    """
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                from semantic_scholar_mcp.config import settings

                config = CacheConfig(
                    enabled=getattr(settings, "cache_enabled", True),
                    default_ttl=getattr(settings, "cache_ttl", 300),
                    paper_details_ttl=getattr(settings, "cache_paper_ttl", 3600),
                )
                _cache = ResponseCache(config)
    assert _cache is not None
    return _cache
