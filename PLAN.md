# Semantic Scholar MCP - Improvement Plan

## Summary

This plan addresses 7 issues identified during code review across 4 phases. All changes include formatting (`ruff`), and testing.

**Commands used throughout:**
```bash
uv run pytest tests/ -v                              # Run unit tests
uv run pytest tests/ -v -m integration               # Run integration tests
uv run pytest tests/ -v -m "not integration"         # Skip integration tests
uv run ruff check src/ tests/                        # Lint
uv run ruff format src/ tests/                       # Format
```

---

## Issues Identified

| # | Issue | Severity | Phase |
|---|-------|----------|-------|
| 1 | Circuit breaker implemented but never used | High | 1 |
| 2 | Integration tests fail due to SSL issues | Medium | 2 |
| 3 | LRU cache uses O(n) list operations | Medium | 3 |
| 4 | POST requests (recommendations) bypass cache | Medium | 3 |
| 5 | Rate limiter comment is misleading | Low | 4 |
| 6 | `_half_open_calls` tracked but never used in circuit breaker | Low | 1 |
| 7 | `invalidate()` method in cache clears all entries instead of pattern matching | Low | 3 |

---

## Phase 1: Integrate Circuit Breaker

### 1.1 Fix Unused `_half_open_calls` Logic

**File:** `src/semantic_scholar_mcp/circuit_breaker.py`

The `_half_open_calls` counter is incremented nowhere, and `half_open_max_calls` config is unused. Either:
- Implement proper half-open logic that limits test calls, OR
- Remove unused fields to simplify

**Recommended approach:** Implement the half-open call limiting:

```python
async def call[T](self, func: Any, *args: Any, **kwargs: Any) -> T:
    async with self._lock:
        self._check_state_transition()

        if self._state == CircuitState.OPEN:
            raise CircuitOpenError("Circuit breaker is open. Service appears to be down.")

        # Track half-open calls
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls > self.config.half_open_max_calls:
                raise CircuitOpenError("Circuit breaker: max half-open calls reached")

    try:
        result = await func(*args, **kwargs)
        await self._record_success()
        return result
    except Exception:
        await self._record_failure()
        raise
```

### 1.2 Integrate Circuit Breaker into Client

**File:** `src/semantic_scholar_mcp/client.py`

Add circuit breaker to protect against cascading failures when the API is down.

**Changes:**

1. Add import:
```python
from semantic_scholar_mcp.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitOpenError
from semantic_scholar_mcp.config import settings
```

2. Add to `__init__`:
```python
self._circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        failure_threshold=settings.circuit_failure_threshold,
        recovery_timeout=settings.circuit_recovery_timeout,
    )
)
```

3. Wrap requests in `get()` and `post()` methods:
```python
async def get(self, endpoint: str, ...) -> Any:
    # Check cache first (before circuit breaker)
    cache = get_cache()
    cached = cache.get(endpoint, params)
    if cached is not None:
        return cached

    # Use circuit breaker for the actual request
    try:
        result = await self._circuit_breaker.call(
            self._do_get, endpoint, params, use_recommendations_api
        )
        cache.set(endpoint, params, result)
        return result
    except CircuitOpenError:
        raise ConnectionError(
            "Service temporarily unavailable. The circuit breaker is open due to repeated failures."
        ) from None

async def _do_get(self, endpoint: str, params: dict[str, Any] | None, use_recommendations_api: bool) -> Any:
    """Internal GET request (called by circuit breaker)."""
    # ... existing request logic ...
```

4. Only trip circuit breaker on connection/server errors, not on 404/429:
```python
async def _record_failure(self) -> None:
    """Record a failed call (only for connection/server errors)."""
    # Don't record rate limits or not-found as circuit breaker failures
```

**Alternative approach:** Create a decorator or wrapper that selectively applies circuit breaker only to certain error types.

### 1.3 Add Tests for Circuit Breaker Integration

**File:** `tests/test_client.py`

Add tests verifying:
- Circuit opens after N consecutive connection errors
- Circuit rejects requests when open
- Circuit transitions to half-open after timeout
- Circuit closes after successful half-open call
- Rate limit errors do NOT trip the circuit breaker
- Not found errors do NOT trip the circuit breaker

---

## Phase 2: Fix Integration Tests

### 2.1 Add SSL Bypass for Integration Tests

**File:** `tests/test_integration.py`

Modify the `real_client` fixture to respect SSL settings:

```python
import os

@pytest_asyncio.fixture
async def real_client():
    """Create a real client for integration tests.

    Respects DISABLE_SSL_VERIFY environment variable for corporate networks.
    """
    # Check if we should disable SSL verification
    disable_ssl = os.getenv("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes")

    if disable_ssl:
        import warnings
        warnings.warn("SSL verification disabled for integration tests")

    client = SemanticScholarClient()
    # The client already respects settings.disable_ssl_verify
    set_client_getter(lambda: client)
    yield client
    await client.close()
```

### 2.2 Add Skip Decorator for Network-Dependent Tests

**File:** `tests/test_integration.py`

Add a skip condition for when network isn't available:

```python
import socket

def network_available() -> bool:
    """Check if we can reach Semantic Scholar API."""
    try:
        socket.create_connection(("api.semanticscholar.org", 443), timeout=5)
        return True
    except OSError:
        return False

# Add to each test class or use as module-level skip
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not network_available(), reason="Network not available"),
]
```

### 2.3 Document SSL Bypass in README

**File:** `README.md`

Add section explaining how to run integration tests on corporate networks:

```markdown
### Running Integration Tests

Integration tests hit the real Semantic Scholar API. To run them:

```bash
uv run pytest tests/test_integration.py -v -m integration
```

On corporate networks with SSL inspection, set:

```bash
DISABLE_SSL_VERIFY=true uv run pytest tests/test_integration.py -v -m integration
```
```

---

## Phase 3: Cache Improvements

### 3.1 Optimize LRU with OrderedDict

**File:** `src/semantic_scholar_mcp/cache.py`

Replace list-based LRU tracking with `collections.OrderedDict` for O(1) operations:

```python
from collections import OrderedDict

class ResponseCache:
    def __init__(self, config: CacheConfig | None = None) -> None:
        self._config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0}

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
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

    def set(self, endpoint: str, params: dict[str, Any] | None, value: dict[str, Any], ttl: int | None = None) -> None:
        if not self._config.enabled:
            return

        key = self._make_key(endpoint, params)

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

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            logger.debug("Cached response for %s (ttl=%ds)", endpoint, ttl)
```

**Remove:** The `_access_order` list field entirely.

### 3.2 Add POST Request Caching for Recommendations

**File:** `src/semantic_scholar_mcp/client.py`

Add caching to POST requests for read-only endpoints:

```python
# Endpoints that are read-only despite using POST
CACHEABLE_POST_ENDPOINTS = frozenset([
    "/recommendations/v1/papers/",
    "/recommendations/v1/papers",
])

def _is_cacheable_post(self, endpoint: str) -> bool:
    """Check if POST endpoint should be cached."""
    return any(endpoint.startswith(prefix) for prefix in CACHEABLE_POST_ENDPOINTS)

async def post(self, endpoint: str, json_data: dict[str, Any] | None = None, ...) -> Any:
    # Check cache for cacheable POST endpoints
    cache = get_cache()
    if self._is_cacheable_post(endpoint):
        # Include json_data in cache key for POST
        cache_params = {"_body": json_data, **(params or {})}
        cached = cache.get(endpoint, cache_params)
        if cached is not None:
            return cached

    # ... existing request logic ...

    result = await self._handle_response(response, endpoint)

    # Cache cacheable POST responses
    if self._is_cacheable_post(endpoint):
        cache_params = {"_body": json_data, **(params or {})}
        cache.set(endpoint, cache_params, result)

    return result
```

### 3.3 Fix `invalidate()` Method

**File:** `src/semantic_scholar_mcp/cache.py`

The current `invalidate()` clears ALL entries regardless of pattern. Fix it:

```python
def invalidate(self, endpoint_pattern: str) -> int:
    """Invalidate cached entries matching pattern.

    Args:
        endpoint_pattern: Substring to match in endpoint (e.g., "/paper/")

    Returns:
        Number of entries invalidated
    """
    with self._lock:
        # We need to store endpoint with cache entry to do pattern matching
        # For now, this clears all - which is safe but suboptimal
        # TODO: Store endpoint in CacheEntry for proper pattern matching
        count = len(self._cache)
        self._cache.clear()
        return count
```

**Better approach** - store endpoint in CacheEntry:

```python
@dataclass
class CacheEntry:
    """A cached value with expiration time."""
    value: dict[str, Any]
    expires_at: float
    endpoint: str  # Add this field

def invalidate(self, endpoint_pattern: str) -> int:
    """Invalidate cached entries matching pattern."""
    with self._lock:
        keys_to_remove = [
            key for key, entry in self._cache.items()
            if endpoint_pattern in entry.endpoint
        ]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)
```

### 3.4 Update Cache Tests

**File:** `tests/test_cache.py`

Add tests for:
- OrderedDict LRU behavior
- POST endpoint caching
- Pattern-based invalidation
- Verify O(1) behavior with larger entry counts

---

## Phase 4: Code Quality Fixes

### 4.1 Fix Misleading Rate Limiter Comment

**File:** `src/semantic_scholar_mcp/rate_limiter.py`

Update comment to match implementation:

```python
def create_rate_limiter(has_api_key: bool) -> TokenBucket:
    """Create appropriate rate limiter based on authentication status.

    Args:
        has_api_key: Whether an API key is configured.

    Returns:
        TokenBucket configured for the appropriate rate limit.
    """
    if has_api_key:
        # With API key: 1 request per second (dedicated pool)
        return TokenBucket(rate=1.0, capacity=1.0)
    else:
        # Without API key: 5000 requests per 5 minutes (~16.67 req/s) from shared pool
        # Using 10 req/s with burst of 20 as conservative estimate
        # to account for other users sharing the pool
        return TokenBucket(rate=10.0, capacity=20.0)
```

### 4.2 Add Missing `__all__` Exports

**File:** `src/semantic_scholar_mcp/circuit_breaker.py`

Add explicit exports:

```python
__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
]
```

**File:** `src/semantic_scholar_mcp/cache.py`

```python
__all__ = [
    "CacheConfig",
    "CacheEntry",
    "ResponseCache",
    "get_cache",
]
```

---

## Verification Plan

### Step 1: Format and Lint
```bash
uv run ruff format src/ tests/
uv run ruff check src/ tests/ --fix
```

### Step 2: Run Unit Tests
```bash
uv run pytest tests/ -v -m "not integration"
```

### Step 3: Run Integration Tests (if network available)
```bash
# Normal network
uv run pytest tests/test_integration.py -v -m integration

# Corporate network with SSL inspection
DISABLE_SSL_VERIFY=true uv run pytest tests/test_integration.py -v -m integration
```

### Step 4: Manual Verification
```bash
# Start the server
uv run semantic-scholar-mcp

# Test scenarios:
# 1. Make requests - verify circuit breaker doesn't interfere
# 2. Verify cache hits for repeated searches
# 3. Verify recommendations are cached
# 4. Simulate API downtime - verify circuit opens
```

---

## Implementation Order

1. **Phase 1.1** - Fix unused `_half_open_calls` in circuit breaker
2. **Phase 1.2** - Integrate circuit breaker into client
3. **Phase 1.3** - Add circuit breaker integration tests
4. **Phase 2.1-2.3** - Fix integration tests SSL handling
5. **Phase 3.1** - Optimize cache with OrderedDict
6. **Phase 3.2** - Add POST caching for recommendations
7. **Phase 3.3** - Fix invalidate() method
8. **Phase 3.4** - Update cache tests
9. **Phase 4.1-4.2** - Code quality fixes

---

## Files Summary

### Modified Files (7)

| File | Changes |
|------|---------|
| `src/semantic_scholar_mcp/circuit_breaker.py` | Implement `_half_open_calls` logic, add `__all__` |
| `src/semantic_scholar_mcp/client.py` | Integrate circuit breaker, add POST caching |
| `src/semantic_scholar_mcp/cache.py` | Use OrderedDict, fix invalidate(), add endpoint to CacheEntry, add `__all__` |
| `src/semantic_scholar_mcp/rate_limiter.py` | Fix misleading comment |
| `tests/test_integration.py` | Add SSL bypass, network availability check |
| `tests/test_client.py` | Add circuit breaker integration tests |
| `tests/test_cache.py` | Add OrderedDict and POST caching tests |

### Documentation Updates (1)

| File | Changes |
|------|---------|
| `README.md` | Document SSL bypass for integration tests |

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Circuit breaker integration | Medium - could reject valid requests | Only trip on connection/server errors, not 404/429 |
| OrderedDict migration | Low - same semantics | Comprehensive test coverage exists |
| POST caching | Low - read-only endpoints | Limited to known cacheable endpoints |
| Integration test changes | None - test-only changes | No production impact |

---

## Success Criteria

- [ ] All 175+ unit tests pass
- [ ] Integration tests pass (or skip gracefully when network unavailable)
- [ ] Circuit breaker activates on repeated connection failures
- [ ] Cache hit rate improves with POST caching
- [ ] No regression in API response times
- [ ] Code passes ruff lint and format checks
