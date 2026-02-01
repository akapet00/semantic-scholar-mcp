# Project Plan

## Overview
Comprehensive improvement plan for the Semantic Scholar MCP server addressing 8 weak spots across 5 phases: structured logging, improved error handling, proactive rate limiting (token bucket), circuit breaker pattern, in-memory TTL caching, server refactoring into modular tools/ directory, and enhanced testing (isolation, integration, concurrency).

**Reference:** `PLAN.md`

---

## Task List

```json
[
  {
    "category": "setup",
    "id": "US-1",
    "title": "Add logging configuration settings to config.py",
    "description": "As a developer, I need logging configuration environment variables so that I can control log level and format at runtime",
    "steps": [
      "Add log_level setting with SS_LOG_LEVEL env var (default: INFO)",
      "Add log_format setting with SS_LOG_FORMAT env var (default: simple)",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "setup",
    "id": "US-2",
    "title": "Create logging_config.py module",
    "description": "As a developer, I need a centralized logging configuration module so that all components use consistent logging",
    "steps": [
      "Create src/semantic_scholar_mcp/logging_config.py",
      "Implement setup_logging() function with level and format_style parameters",
      "Implement get_logger(name) function returning namespaced logger",
      "Support simple and detailed format styles",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-3",
    "title": "Add logging to paper_tracker.py",
    "description": "As a developer, I want tracking operations logged so that I can debug paper tracking issues",
    "steps": [
      "Import get_logger from logging_config",
      "Add DEBUG log in track() method for paper tracking",
      "Add DEBUG log in track_many() method",
      "Add INFO log in clear() method with count of cleared papers",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-4",
    "title": "Add logging to bibtex.py",
    "description": "As a developer, I want BibTeX export operations logged so that I can track export activity",
    "steps": [
      "Import get_logger from logging_config",
      "Add DEBUG log for entry generation",
      "Add INFO log for export operations with entry count",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "setup",
    "id": "US-5",
    "title": "Add new exception classes to exceptions.py",
    "description": "As a developer, I need specific exception types for different API error scenarios so that error handling is precise",
    "steps": [
      "Add ServerError class with status_code attribute for 5xx errors",
      "Add AuthenticationError class for 401/403 errors",
      "Add ConnectionError class for network/timeout issues",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-6",
    "title": "Improve _handle_response() error handling in client.py",
    "description": "As a developer, I want the client to raise specific exceptions for different HTTP error codes so that callers can handle errors appropriately",
    "steps": [
      "Update _handle_response() to raise AuthenticationError for 401/403",
      "Update _handle_response() to raise ServerError for 5xx errors",
      "Keep existing RateLimitError for 429 and NotFoundError for 404",
      "Add helpful error messages with endpoint context",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-7",
    "title": "Add connection error handling in client.py",
    "description": "As a developer, I want HTTP connection errors wrapped in custom exceptions so that network issues are handled gracefully",
    "steps": [
      "Wrap httpx.ConnectError in ConnectionError in get() method",
      "Wrap httpx.TimeoutException in ConnectionError in get() method",
      "Apply same wrapping in post() method",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-8",
    "title": "Add TokenBucket class to rate_limiter.py",
    "description": "As a developer, I need a token bucket rate limiter so that requests are proactively throttled before hitting API limits",
    "steps": [
      "Create TokenBucket dataclass with rate and capacity parameters",
      "Implement async acquire() method that waits if tokens unavailable",
      "Use asyncio.Lock for thread-safety",
      "Track tokens and last_update time using time.monotonic()",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-9",
    "title": "Add create_rate_limiter() factory function",
    "description": "As a developer, I need a factory to create appropriate rate limiters based on API key status",
    "steps": [
      "Create create_rate_limiter(has_api_key: bool) function in rate_limiter.py",
      "Return TokenBucket(rate=1.0, capacity=1.0) when has_api_key is True",
      "Return TokenBucket(rate=10.0, capacity=20.0) when has_api_key is False",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-10",
    "title": "Integrate TokenBucket into client.py",
    "description": "As a developer, I want the client to use token bucket rate limiting so that API rate limits are not exceeded",
    "steps": [
      "Import TokenBucket and create_rate_limiter from rate_limiter",
      "Initialize _rate_limiter in __init__ using create_rate_limiter(settings.has_api_key)",
      "Call await self._rate_limiter.acquire() before each request in get()",
      "Call await self._rate_limiter.acquire() before each request in post()",
      "Add DEBUG log when rate limiter causes wait",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "setup",
    "id": "US-11",
    "title": "Add circuit breaker configuration to config.py",
    "description": "As a developer, I need configurable circuit breaker settings so that failure thresholds can be tuned",
    "steps": [
      "Add circuit_failure_threshold setting with SS_CIRCUIT_FAILURE_THRESHOLD env var (default: 5)",
      "Add circuit_recovery_timeout setting with SS_CIRCUIT_RECOVERY_TIMEOUT env var (default: 30.0)",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-12",
    "title": "Create circuit_breaker.py module",
    "description": "As a developer, I need a circuit breaker to prevent hammering a failing API so that the system degrades gracefully",
    "steps": [
      "Create src/semantic_scholar_mcp/circuit_breaker.py",
      "Implement CircuitState enum with CLOSED, OPEN, HALF_OPEN states",
      "Implement CircuitBreakerConfig dataclass with failure_threshold, recovery_timeout, half_open_max_calls",
      "Implement CircuitBreaker dataclass with call() method",
      "Implement state transitions: CLOSED->OPEN on threshold, OPEN->HALF_OPEN on timeout, HALF_OPEN->CLOSED on success",
      "Create CircuitOpenError exception class",
      "Add logging for state transitions",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "setup",
    "id": "US-13",
    "title": "Add cache configuration to config.py",
    "description": "As a developer, I need configurable cache settings so that caching behavior can be tuned",
    "steps": [
      "Add cache_enabled setting with SS_CACHE_ENABLED env var (default: true)",
      "Add cache_ttl setting with SS_CACHE_TTL env var (default: 300)",
      "Add cache_paper_ttl setting with SS_CACHE_PAPER_TTL env var (default: 3600)",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-14",
    "title": "Create cache.py module with CacheEntry and CacheConfig",
    "description": "As a developer, I need cache data structures so that API responses can be cached with TTL",
    "steps": [
      "Create src/semantic_scholar_mcp/cache.py",
      "Implement CacheEntry dataclass with value and expires_at, plus is_expired property",
      "Implement CacheConfig dataclass with enabled, default_ttl, paper_details_ttl, search_ttl, max_entries",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-15",
    "title": "Implement ResponseCache class",
    "description": "As a developer, I need a thread-safe in-memory cache so that repeated API requests return cached data",
    "steps": [
      "Implement ResponseCache class in cache.py",
      "Implement _make_key() static method using SHA256 hash of endpoint + params",
      "Implement get() method with TTL expiration check and LRU access order update",
      "Implement set() method with endpoint-specific TTL and LRU eviction at max_entries",
      "Implement clear() method to reset cache",
      "Implement get_stats() method returning hits, misses, hit_rate",
      "Use threading.Lock for thread-safety",
      "Add DEBUG logging for cache hits and stores",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-16",
    "title": "Add global cache accessor function",
    "description": "As a developer, I need a global cache instance so that all components share the same cache",
    "steps": [
      "Add get_cache() function in cache.py that returns singleton ResponseCache",
      "Use double-checked locking pattern with threading.Lock",
      "Initialize CacheConfig from settings",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-17",
    "title": "Integrate cache into client.py",
    "description": "As a developer, I want API responses cached so that repeated requests are fast",
    "steps": [
      "Import get_cache from cache module",
      "Check cache before making request in get() method",
      "Return cached response if available and not expired",
      "Cache successful responses after API call",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-18",
    "title": "Create tools/ directory structure",
    "description": "As a developer, I need the tools directory created so that server.py can be modularized",
    "steps": [
      "Create src/semantic_scholar_mcp/tools/ directory",
      "Create src/semantic_scholar_mcp/tools/__init__.py with exports for all tools",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-19",
    "title": "Create tools/_common.py with shared utilities",
    "description": "As a developer, I need shared constants and accessors so that tool modules have common dependencies",
    "steps": [
      "Create src/semantic_scholar_mcp/tools/_common.py",
      "Define DEFAULT_PAPER_FIELDS constant",
      "Define DEFAULT_AUTHOR_FIELDS constant",
      "Define PAPER_FIELDS_WITH_TLDR constant",
      "Implement get_tracker() function",
      "Implement set_client_getter() and get_client() functions",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-20",
    "title": "Extract paper tools to tools/papers.py",
    "description": "As a developer, I want paper-related tools in a dedicated module so that server.py is smaller",
    "steps": [
      "Create src/semantic_scholar_mcp/tools/papers.py",
      "Move search_papers function from server.py",
      "Move get_paper_details function from server.py",
      "Move get_paper_citations function from server.py",
      "Move get_paper_references function from server.py",
      "Update imports to use _common module",
      "Remove @mcp.tool() decorators (will be applied in server.py)",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-21",
    "title": "Extract author tools to tools/authors.py",
    "description": "As a developer, I want author-related tools in a dedicated module so that server.py is smaller",
    "steps": [
      "Create src/semantic_scholar_mcp/tools/authors.py",
      "Move search_authors function from server.py",
      "Move get_author_details function from server.py",
      "Move find_duplicate_authors function from server.py",
      "Move consolidate_authors function from server.py",
      "Update imports to use _common module",
      "Remove @mcp.tool() decorators",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-22",
    "title": "Extract recommendation tools to tools/recommendations.py",
    "description": "As a developer, I want recommendation tools in a dedicated module so that server.py is smaller",
    "steps": [
      "Create src/semantic_scholar_mcp/tools/recommendations.py",
      "Move get_recommendations function from server.py",
      "Move get_related_papers function from server.py",
      "Update imports to use _common module",
      "Remove @mcp.tool() decorators",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-23",
    "title": "Extract tracking tools to tools/tracking.py",
    "description": "As a developer, I want tracking tools in a dedicated module so that server.py is smaller",
    "steps": [
      "Create src/semantic_scholar_mcp/tools/tracking.py",
      "Move list_tracked_papers function from server.py",
      "Move clear_tracked_papers function from server.py",
      "Move export_bibtex function from server.py",
      "Update imports to use _common module",
      "Remove @mcp.tool() decorators",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-24",
    "title": "Update tools/__init__.py with all exports",
    "description": "As a developer, I need all tools exported from the tools package so that server.py can import them",
    "steps": [
      "Import all paper tools from tools.papers",
      "Import all author tools from tools.authors",
      "Import all recommendation tools from tools.recommendations",
      "Import all tracking tools from tools.tracking",
      "Add __all__ list with all 13 tool names",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-25",
    "title": "Refactor server.py to use tools/ modules",
    "description": "As a developer, I want server.py to only handle MCP setup so that it is maintainable (~100 lines)",
    "steps": [
      "Remove all tool function implementations from server.py",
      "Import all tools from semantic_scholar_mcp.tools",
      "Import set_client_getter from tools._common",
      "Call set_client_getter(get_client) to configure tools",
      "Register all 13 tools with mcp.tool() decorator",
      "Keep FastMCP initialization, client management, and main()",
      "Initialize logging using setup_logging()",
      "Typecheck passes"
    ],
    "passes": true
  },
  {
    "category": "testing",
    "id": "US-26",
    "title": "Add test isolation fixtures to conftest.py",
    "description": "As a developer, I want tests isolated so that they don't affect each other",
    "steps": [
      "Add reset_tracker() autouse fixture that resets PaperTracker singleton before/after each test",
      "Add reset_cache() autouse fixture that clears cache before/after each test",
      "Import PaperTracker and get_cache",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-27",
    "title": "Add integration test marker to pyproject.toml",
    "description": "As a developer, I want to run integration tests separately so that unit tests are fast",
    "steps": [
      "Add [tool.pytest.ini_options] section to pyproject.toml",
      "Set asyncio_mode = auto",
      "Set testpaths = [tests]",
      "Add markers list with integration marker and description",
      "Typecheck passes"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-28",
    "title": "Create test_integration.py with search tests",
    "description": "As a developer, I want integration tests for paper search so that I can verify real API behavior",
    "steps": [
      "Create tests/test_integration.py",
      "Add pytestmark = pytest.mark.integration",
      "Create real_client fixture that creates SemanticScholarClient",
      "Create reset_tracker_integration fixture",
      "Implement test_search_real_papers() testing attention is all you need query",
      "Implement test_search_with_year_filter() testing year range filter",
      "All tests pass (with -m integration)"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-29",
    "title": "Add paper details and workflow integration tests",
    "description": "As a developer, I want integration tests for paper details and workflows so that I can verify end-to-end behavior",
    "steps": [
      "Add TestPaperDetailsIntegration class to test_integration.py",
      "Implement test_get_known_paper() testing known paper ID",
      "Implement test_get_paper_by_doi() testing DOI lookup",
      "Add TestWorkflowIntegration class",
      "Implement test_search_track_workflow() verifying papers are tracked after search",
      "All tests pass (with -m integration)"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-30",
    "title": "Add rate limit integration tests",
    "description": "As a developer, I want integration tests for rate limiting so that I can verify multiple requests succeed",
    "steps": [
      "Add TestRateLimitIntegration class to test_integration.py",
      "Implement test_multiple_requests_succeed() making 3 sequential searches",
      "All tests pass (with -m integration)"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-31",
    "title": "Create test_concurrency.py with paper tracker tests",
    "description": "As a developer, I want concurrency tests for paper tracker so that I can verify thread-safety",
    "steps": [
      "Create tests/test_concurrency.py",
      "Add reset_tracker fixture",
      "Implement test_concurrent_tracking() with 10 threads tracking 100 papers each",
      "Implement test_concurrent_read_write() with concurrent readers and writers",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-32",
    "title": "Add cache concurrency tests",
    "description": "As a developer, I want concurrency tests for cache so that I can verify thread-safety",
    "steps": [
      "Add TestCacheConcurrency class to test_concurrency.py",
      "Implement test_concurrent_cache_operations() with 5 writer and 5 reader threads",
      "Verify no exceptions occur during concurrent access",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-33",
    "title": "Update test_server.py imports for new tools structure",
    "description": "As a developer, I want existing tests to work with the new tools structure so that refactoring doesn't break tests",
    "steps": [
      "Update imports to use semantic_scholar_mcp.tools.papers",
      "Update imports to use semantic_scholar_mcp.tools.authors",
      "Update imports to use semantic_scholar_mcp.tools.recommendations",
      "Import set_client_getter from tools._common",
      "Add mock_client_getter fixture using set_client_getter",
      "Remove patch.object and .fn calls, call tools directly",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-34",
    "title": "Add unit tests for TokenBucket",
    "description": "As a developer, I want unit tests for TokenBucket so that rate limiting logic is verified",
    "steps": [
      "Add tests/test_token_bucket.py or add to test_rate_limiter.py",
      "Test acquire() returns 0 when tokens available",
      "Test acquire() waits when tokens unavailable",
      "Test token replenishment over time",
      "Test create_rate_limiter() returns correct bucket for api key status",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-35",
    "title": "Add unit tests for CircuitBreaker",
    "description": "As a developer, I want unit tests for CircuitBreaker so that circuit breaker logic is verified",
    "steps": [
      "Create tests/test_circuit_breaker.py",
      "Test circuit starts in CLOSED state",
      "Test circuit opens after failure_threshold failures",
      "Test circuit transitions to HALF_OPEN after recovery_timeout",
      "Test circuit closes on success in HALF_OPEN state",
      "Test circuit reopens on failure in HALF_OPEN state",
      "Test CircuitOpenError raised when circuit is OPEN",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-36",
    "title": "Add unit tests for ResponseCache",
    "description": "As a developer, I want unit tests for ResponseCache so that caching logic is verified",
    "steps": [
      "Create tests/test_cache.py",
      "Test get() returns None for missing key",
      "Test set() and get() round-trip",
      "Test TTL expiration",
      "Test LRU eviction at max_entries",
      "Test cache disabled when config.enabled=False",
      "Test get_stats() returns correct hit/miss counts",
      "All tests pass"
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

Tasks should be executed in ID order (US-1 through US-36) as dependencies are built in:

1. **US-1 to US-4**: Logging foundation (needed to observe other changes)
2. **US-5 to US-7**: Error handling improvements
3. **US-8 to US-10**: Token bucket rate limiting
4. **US-11 to US-12**: Circuit breaker pattern
5. **US-13 to US-17**: Caching layer
6. **US-18 to US-25**: Server refactoring (largest change)
7. **US-26 to US-36**: Testing improvements
