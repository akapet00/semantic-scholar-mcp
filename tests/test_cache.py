"""Unit tests for the cache module."""

import time

import pytest

from semantic_scholar_mcp.cache import CacheConfig, CacheEntry, ResponseCache


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_not_expired(self) -> None:
        """Test that a fresh cache entry is not expired."""
        entry = CacheEntry(value={"data": "test"}, expires_at=time.monotonic() + 100)
        assert not entry.is_expired

    def test_cache_entry_expired(self) -> None:
        """Test that an old cache entry is expired."""
        entry = CacheEntry(value={"data": "test"}, expires_at=time.monotonic() - 1)
        assert entry.is_expired


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.default_ttl == 300
        assert config.paper_details_ttl == 3600
        assert config.search_ttl == 300
        assert config.max_entries == 1000

    def test_custom_values(self) -> None:
        """Test that custom values can be set."""
        config = CacheConfig(
            enabled=False,
            default_ttl=600,
            paper_details_ttl=7200,
            search_ttl=120,
            max_entries=500,
        )
        assert config.enabled is False
        assert config.default_ttl == 600
        assert config.paper_details_ttl == 7200
        assert config.search_ttl == 120
        assert config.max_entries == 500


class TestResponseCacheGet:
    """Tests for ResponseCache.get() method."""

    def test_get_returns_none_for_missing_key(self) -> None:
        """Test that get() returns None for missing key."""
        cache = ResponseCache()
        result = cache.get("/api/test", {"param": "value"})
        assert result is None

    def test_get_returns_none_when_cache_disabled(self) -> None:
        """Test that get() returns None when cache is disabled."""
        config = CacheConfig(enabled=False)
        cache = ResponseCache(config)
        cache.set("/api/test", None, {"data": "test"})
        result = cache.get("/api/test", None)
        assert result is None


class TestResponseCacheSetGet:
    """Tests for ResponseCache set() and get() round-trip."""

    def test_set_and_get_roundtrip(self) -> None:
        """Test that set() and get() work together."""
        cache = ResponseCache()
        endpoint = "/api/papers"
        params = {"query": "test"}
        value = {"data": [{"paperId": "123", "title": "Test Paper"}]}

        cache.set(endpoint, params, value)
        result = cache.get(endpoint, params)

        assert result == value

    def test_different_params_different_cache_entries(self) -> None:
        """Test that different params result in different cache entries."""
        cache = ResponseCache()
        endpoint = "/api/papers"

        cache.set(endpoint, {"query": "test1"}, {"data": "value1"})
        cache.set(endpoint, {"query": "test2"}, {"data": "value2"})

        result1 = cache.get(endpoint, {"query": "test1"})
        result2 = cache.get(endpoint, {"query": "test2"})

        assert result1 == {"data": "value1"}
        assert result2 == {"data": "value2"}

    def test_none_params_works(self) -> None:
        """Test that None params work correctly."""
        cache = ResponseCache()
        endpoint = "/api/test"

        cache.set(endpoint, None, {"data": "test"})
        result = cache.get(endpoint, None)

        assert result == {"data": "test"}


class TestResponseCacheTTL:
    """Tests for ResponseCache TTL expiration."""

    def test_expired_entry_returns_none(self) -> None:
        """Test that expired entry returns None."""
        config = CacheConfig(search_ttl=1)  # 1 second TTL
        cache = ResponseCache(config)

        cache.set("/api/search", None, {"data": "test"})

        # Manually expire the entry by modifying expires_at
        key = cache._make_key("/api/search", None)
        cache._cache[key].expires_at = time.monotonic() - 1

        result = cache.get("/api/search", None)
        assert result is None

    def test_custom_ttl_is_respected(self) -> None:
        """Test that custom TTL is respected."""
        cache = ResponseCache()

        cache.set("/api/test", None, {"data": "test"}, ttl=1)

        # Entry should exist
        result = cache.get("/api/test", None)
        assert result == {"data": "test"}

        # Manually expire
        key = cache._make_key("/api/test", None)
        cache._cache[key].expires_at = time.monotonic() - 1

        # Entry should be gone
        result = cache.get("/api/test", None)
        assert result is None

    def test_paper_details_use_longer_ttl(self) -> None:
        """Test that paper details use paper_details_ttl."""
        config = CacheConfig(paper_details_ttl=7200, search_ttl=300)
        cache = ResponseCache(config)

        # Paper details endpoint
        cache.set("/paper/123", None, {"data": "test"})

        key = cache._make_key("/paper/123", None)
        entry = cache._cache[key]

        # TTL should be close to paper_details_ttl (7200)
        expected_expires = time.monotonic() + 7200
        assert abs(entry.expires_at - expected_expires) < 1  # Within 1 second


class TestResponseCacheLRU:
    """Tests for ResponseCache LRU eviction."""

    def test_lru_eviction_at_max_entries(self) -> None:
        """Test that LRU eviction happens at max_entries."""
        config = CacheConfig(max_entries=3)
        cache = ResponseCache(config)

        # Add 3 entries (at capacity)
        cache.set("/api/1", None, {"data": "1"})
        cache.set("/api/2", None, {"data": "2"})
        cache.set("/api/3", None, {"data": "3"})

        # All 3 should be present
        assert cache.get("/api/1", None) is not None
        assert cache.get("/api/2", None) is not None
        assert cache.get("/api/3", None) is not None
        # After gets, LRU order is [1, 2, 3] (1 was accessed first, 3 last)

        # Add 4th entry, should evict oldest in LRU order (entry 1)
        cache.set("/api/4", None, {"data": "4"})

        # Entry 1 should be evicted (was first in LRU order after gets)
        assert cache.get("/api/1", None) is None
        assert cache.get("/api/4", None) is not None

    def test_accessing_entry_updates_lru_order(self) -> None:
        """Test that accessing an entry updates its LRU position."""
        config = CacheConfig(max_entries=3)
        cache = ResponseCache(config)

        # Add 3 entries
        cache.set("/api/1", None, {"data": "1"})
        cache.set("/api/2", None, {"data": "2"})
        cache.set("/api/3", None, {"data": "3"})

        # Access entry 1 to move it to end of LRU
        cache.get("/api/1", None)

        # Add 4th entry - should evict entry 2 (oldest not recently accessed)
        cache.set("/api/4", None, {"data": "4"})

        # Entry 1 should still exist (was accessed), entry 2 should be evicted
        assert cache.get("/api/1", None) is not None
        assert cache.get("/api/2", None) is None


class TestResponseCacheDisabled:
    """Tests for ResponseCache when disabled."""

    def test_set_does_nothing_when_disabled(self) -> None:
        """Test that set() does nothing when cache is disabled."""
        config = CacheConfig(enabled=False)
        cache = ResponseCache(config)

        cache.set("/api/test", None, {"data": "test"})

        # Cache should be empty
        assert len(cache._cache) == 0

    def test_get_returns_none_when_disabled(self) -> None:
        """Test that get() always returns None when disabled."""
        config = CacheConfig(enabled=False)
        cache = ResponseCache(config)

        # Bypass disabled check for set by directly manipulating cache
        key = cache._make_key("/api/test", None)
        cache._cache[key] = CacheEntry(value={"data": "test"}, expires_at=time.monotonic() + 100)

        # get() should still return None because cache is disabled
        result = cache.get("/api/test", None)
        assert result is None


class TestResponseCacheStats:
    """Tests for ResponseCache.get_stats() method."""

    def test_get_stats_returns_correct_hit_miss_counts(self) -> None:
        """Test that get_stats() returns correct hit/miss counts."""
        cache = ResponseCache()

        # 2 misses
        cache.get("/api/missing1", None)
        cache.get("/api/missing2", None)

        # Add entry
        cache.set("/api/test", None, {"data": "test"})

        # 3 hits
        cache.get("/api/test", None)
        cache.get("/api/test", None)
        cache.get("/api/test", None)

        stats = cache.get_stats()

        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["entries"] == 1
        assert stats["hit_rate"] == pytest.approx(0.6)  # 3/(3+2) = 0.6

    def test_get_stats_hit_rate_zero_when_no_requests(self) -> None:
        """Test that hit_rate is 0 when no requests made."""
        cache = ResponseCache()
        stats = cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0


class TestResponseCacheClear:
    """Tests for ResponseCache.clear() method."""

    def test_clear_removes_all_entries(self) -> None:
        """Test that clear() removes all entries."""
        cache = ResponseCache()

        cache.set("/api/1", None, {"data": "1"})
        cache.set("/api/2", None, {"data": "2"})

        cache.clear()

        assert len(cache._cache) == 0

    def test_clear_resets_stats(self) -> None:
        """Test that clear() resets statistics."""
        cache = ResponseCache()

        cache.set("/api/test", None, {"data": "test"})
        cache.get("/api/test", None)  # Hit
        cache.get("/api/missing", None)  # Miss

        cache.clear()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
