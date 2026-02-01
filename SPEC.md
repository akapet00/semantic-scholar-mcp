# Project Plan

## Overview
Address 7 issues identified during code review: integrate the unused circuit breaker, fix integration test SSL issues, optimize cache LRU operations with OrderedDict, add POST request caching for recommendations, fix pattern-based cache invalidation, correct misleading rate limiter comments, and add missing `__all__` exports.

**Reference:** `PLAN.md`

---

## Task List

```json
[
  {
    "category": "feature",
    "id": "US-1",
    "title": "Implement half-open call limiting in circuit breaker",
    "description": "As a developer, I need the circuit breaker to limit calls in half-open state so that the system can probe API recovery without overwhelming it",
    "steps": [
      "Update call() method to track _half_open_calls when state is HALF_OPEN",
      "Raise CircuitOpenError when _half_open_calls exceeds half_open_max_calls",
      "Reset _half_open_calls to 0 when transitioning to HALF_OPEN state",
      "Typecheck passes",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-2",
    "title": "Integrate circuit breaker into client.py",
    "description": "As a developer, I want the client to use the circuit breaker so that cascading failures are prevented when the API is down",
    "steps": [
      "Import CircuitBreaker, CircuitBreakerConfig, CircuitOpenError from circuit_breaker",
      "Initialize _circuit_breaker in __init__ using settings.circuit_failure_threshold and settings.circuit_recovery_timeout",
      "Extract request logic into _do_get() internal method",
      "Wrap _do_get() call with self._circuit_breaker.call() in get() method",
      "Convert CircuitOpenError to ConnectionError with descriptive message",
      "Apply same pattern to post() method with _do_post()",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-3",
    "title": "Filter circuit breaker failures to connection/server errors only",
    "description": "As a developer, I want the circuit breaker to only trip on connection and server errors so that 404 and 429 errors do not incorrectly open the circuit",
    "steps": [
      "Create _is_circuit_breaker_error() helper method in client.py",
      "Return True for httpx.ConnectError, httpx.TimeoutException, and ServerError",
      "Return False for RateLimitError and NotFoundError",
      "Only record failures in circuit breaker when _is_circuit_breaker_error() returns True",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "testing",
    "id": "US-4",
    "title": "Add circuit breaker integration tests in test_client.py",
    "description": "As a developer, I want tests verifying circuit breaker behavior so that integration is reliable",
    "steps": [
      "Add test_circuit_opens_after_consecutive_failures() verifying circuit opens after N connection errors",
      "Add test_circuit_rejects_when_open() verifying requests fail fast when circuit is open",
      "Add test_circuit_half_open_after_timeout() verifying state transition after recovery timeout",
      "Add test_circuit_closes_on_successful_half_open() verifying circuit closes after success",
      "Add test_rate_limit_does_not_trip_circuit() verifying 429 errors do not trip circuit",
      "Add test_not_found_does_not_trip_circuit() verifying 404 errors do not trip circuit",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "testing",
    "id": "US-5",
    "title": "Add SSL bypass support for integration tests",
    "description": "As a developer, I want integration tests to respect SSL settings so that tests pass on corporate networks with SSL inspection",
    "steps": [
      "Update real_client fixture in test_integration.py to check DISABLE_SSL_VERIFY env var",
      "Add warning log when SSL verification is disabled",
      "Ensure client uses settings.disable_ssl_verify",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "testing",
    "id": "US-6",
    "title": "Add network availability check for integration tests",
    "description": "As a developer, I want integration tests to skip gracefully when network is unavailable so that CI does not fail on network issues",
    "steps": [
      "Create network_available() function using socket.create_connection() to api.semanticscholar.org:443",
      "Add pytest.mark.skipif decorator checking network_available() to test module",
      "Set timeout to 5 seconds for connection check",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-7",
    "title": "Optimize LRU cache with OrderedDict",
    "description": "As a developer, I want O(1) LRU operations so that cache performance is optimal for large entry counts",
    "steps": [
      "Import OrderedDict from collections in cache.py",
      "Replace _cache dict with OrderedDict[str, CacheEntry]",
      "Remove _access_order list field entirely",
      "Use self._cache.move_to_end(key) in get() for O(1) LRU update",
      "Use self._cache.popitem(last=False) in set() for O(1) eviction",
      "Delete key before re-adding in set() to move existing keys to end",
      "Typecheck passes",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-8",
    "title": "Add POST request caching for recommendations",
    "description": "As a developer, I want recommendation POST requests cached so that repeated queries return fast",
    "steps": [
      "Define CACHEABLE_POST_ENDPOINTS frozenset with /recommendations/v1/papers/ and /recommendations/v1/papers",
      "Create _is_cacheable_post() method checking if endpoint starts with any cacheable prefix",
      "Check cache before POST request for cacheable endpoints, including json_data in cache params as _body key",
      "Cache successful responses for cacheable POST endpoints",
      "Typecheck passes"
    ],
    "passes": false
  },
  {
    "category": "feature",
    "id": "US-9",
    "title": "Add endpoint field to CacheEntry for pattern invalidation",
    "description": "As a developer, I want cache entries to store their endpoint so that pattern-based invalidation works correctly",
    "steps": [
      "Add endpoint: str field to CacheEntry dataclass",
      "Update set() method to pass endpoint to CacheEntry constructor",
      "Typecheck passes"
    ],
    "passes": false
  },
  {
    "category": "feature",
    "id": "US-10",
    "title": "Fix invalidate() method for pattern matching",
    "description": "As a developer, I want invalidate() to only remove entries matching the pattern so that cache invalidation is precise",
    "steps": [
      "Update invalidate() to iterate through cache entries and check endpoint_pattern in entry.endpoint",
      "Collect keys to remove where pattern matches",
      "Delete only matching keys instead of clearing all",
      "Return count of invalidated entries",
      "Typecheck passes",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-11",
    "title": "Add cache tests for OrderedDict and POST caching",
    "description": "As a developer, I want tests verifying new cache functionality so that changes are reliable",
    "steps": [
      "Add test_lru_eviction_order() verifying oldest entries evicted first",
      "Add test_lru_access_updates_order() verifying accessed entries move to end",
      "Add test_pattern_invalidation() verifying only matching entries removed",
      "Add test_pattern_invalidation_no_match() verifying no entries removed when pattern doesn't match",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "refactor",
    "id": "US-12",
    "title": "Fix misleading rate limiter comment",
    "description": "As a developer, I want accurate comments so that the codebase is understandable",
    "steps": [
      "Update create_rate_limiter() docstring to explain rate limiting strategy",
      "Update comment for API key case to state '1 request per second (dedicated pool)'",
      "Update comment for no API key case to explain shared pool and conservative estimate",
      "Typecheck passes"
    ],
    "passes": false
  },
  {
    "category": "refactor",
    "id": "US-13",
    "title": "Add __all__ exports to circuit_breaker.py",
    "description": "As a developer, I want explicit exports so that module interfaces are clear",
    "steps": [
      "Add __all__ list with CircuitBreaker, CircuitBreakerConfig, CircuitOpenError, CircuitState",
      "Typecheck passes"
    ],
    "passes": false
  },
  {
    "category": "refactor",
    "id": "US-14",
    "title": "Add __all__ exports to cache.py",
    "description": "As a developer, I want explicit exports so that module interfaces are clear",
    "steps": [
      "Add __all__ list with CacheConfig, CacheEntry, ResponseCache, get_cache",
      "Typecheck passes"
    ],
    "passes": false
  }
]
```

---

## Notes

**Linting:**
```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

**Type checking:**
```bash
uv run ty check src/
```

**Tests:**
```bash
# Unit tests only
uv run pytest tests/ -v -m "not integration"

# Integration tests only
uv run pytest tests/ -v -m integration

# All tests
uv run pytest tests/ -v
```

**Run:**
```bash
uv run semantic-scholar-mcp
```

---

## Implementation Order

Tasks should be executed in ID order (US-1 through US-14) as dependencies are built in:

1. **US-1 to US-4**: Circuit breaker integration (Phase 1)
2. **US-5 to US-6**: Integration test fixes (Phase 2)
3. **US-7 to US-11**: Cache improvements (Phase 3)
4. **US-12 to US-14**: Code quality fixes (Phase 4)
