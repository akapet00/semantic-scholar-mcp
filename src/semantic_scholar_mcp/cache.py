"""In-memory TTL cache for API responses."""

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """A cached value with expiration time.

    Attributes:
        value: The cached response data.
        expires_at: Timestamp when this entry expires (using monotonic time).
    """

    value: dict[str, Any]
    expires_at: float

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
