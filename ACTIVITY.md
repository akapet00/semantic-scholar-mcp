# Activity

Append activity log at bottom. Follow the template:

```markdown
### Current atetime in YYYY-MM-DD HH:MM format for Central European Timezone (use tools)

**Tasks completed:** Tasks that are already completed; take ID and description from @SPEC.md.

**Current tasks:** Task that is implemented in the current instance; take description from @SPEC.md.

**Blockers:** Issues encountered.
```

## Session Log

### 2026-02-01 15:20 (CET)

**Tasks completed:** None (starting fresh)

**Current task:** US-1 - Implement half-open call limiting in circuit breaker

**Changes made:**
- Modified `src/semantic_scholar_mcp/circuit_breaker.py`: Added half-open call tracking and limiting in the `call()` method
- Modified `tests/test_circuit_breaker.py`: Added `TestHalfOpenCallLimiting` class with 3 tests

**Verification:**
- ruff format: PASS
- ruff check: PASS
- ty check: PASS (circuit_breaker.py - existing issues in other files are pre-existing)
- pytest: PASS (178 passed, 6 deselected)

**Blockers:** None

---

### 2026-02-01 21:37 (CET)

**Tasks completed:** US-1 - Implement half-open call limiting in circuit breaker

**Current task:** US-2 - Integrate circuit breaker into client.py

**Changes made:**
- Modified `src/semantic_scholar_mcp/client.py`:
  - Added imports for CircuitBreaker, CircuitBreakerConfig, CircuitOpenError
  - Initialized _circuit_breaker in __init__ using settings
  - Extracted GET request logic into _do_get() internal method
  - Wrapped _do_get() call with self._circuit_breaker.call() in get() method
  - Extracted POST request logic into _do_post() internal method
  - Wrapped _do_post() call with self._circuit_breaker.call() in post() method
  - CircuitOpenError is converted to ConnectionError with descriptive message
- Modified `tests/conftest.py`:
  - Added circuit_failure_threshold and circuit_recovery_timeout to mock settings fixtures

**Verification:**
- ruff format: PASS
- ruff check: PASS
- ty check: PASS (3 pre-existing issues in other files)
- pytest: PASS (178 passed, 6 deselected)

**Blockers:** None

---

### 2026-02-01 21:46 (CET)

**Tasks completed:** US-1, US-2

**Current task:** US-3 - Filter circuit breaker failures to connection/server errors only

**Changes made:**
- Modified `src/semantic_scholar_mcp/client.py`:
  - Added `_is_circuit_breaker_error()` helper function to determine which errors should trip the circuit breaker
  - Added `_NonCircuitBreakerResult` class to wrap exceptions that should not trip the circuit breaker
  - Modified `_do_get()` to catch non-circuit-breaker errors and wrap them in `_NonCircuitBreakerResult`
  - Modified `_do_post()` with the same pattern
  - Modified `get()` to unwrap `_NonCircuitBreakerResult` and re-raise the original exception
  - Modified `post()` with the same pattern

**Verification:**
- ruff format: PASS
- ruff check: PASS
- ty check: PASS (client.py - 3 pre-existing issues in other files)
- pytest: PASS (178 passed, 6 deselected)

**Blockers:** None

---

### 2026-02-01 21:48 (CET)

**Tasks completed:** US-1, US-2, US-3

**Current task:** US-4 - Add circuit breaker integration tests in test_client.py

**Changes made:**
- Modified `tests/test_client.py`:
  - Added `TestCircuitBreakerIntegration` class with 6 tests:
    - `test_circuit_opens_after_consecutive_failures()` - verifies circuit opens after N connection errors
    - `test_circuit_rejects_when_open()` - verifies requests fail fast when circuit is open
    - `test_circuit_half_open_after_timeout()` - verifies state transition after recovery timeout
    - `test_circuit_closes_on_successful_half_open()` - verifies circuit closes after success
    - `test_rate_limit_does_not_trip_circuit()` - verifies 429 errors do not trip circuit
    - `test_not_found_does_not_trip_circuit()` - verifies 404 errors do not trip circuit

**Verification:**
- ruff format: PASS
- ruff check: PASS
- ty check: PASS (3 pre-existing issues in other files)
- pytest: PASS (184 passed, 6 deselected)

**Blockers:** None

---

### 2026-02-01 22:10 (CET)

**Tasks completed:** US-1, US-2, US-3, US-4, US-5, US-6

**Current task:** US-7 - Optimize LRU cache with OrderedDict

**Changes made:**
- Modified `src/semantic_scholar_mcp/cache.py`:
  - Added import for `OrderedDict` from collections
  - Replaced `_cache: dict[str, CacheEntry]` with `OrderedDict[str, CacheEntry]`
  - Removed `_access_order` list field entirely
  - Updated `get()` method to use `move_to_end(key)` for O(1) LRU update
  - Updated `set()` method to use `popitem(last=False)` for O(1) eviction
  - Updated `set()` to delete key before re-adding to move existing keys to end
  - Updated `clear()` to remove reference to `_access_order`
- Modified `tests/test_cache.py`:
  - Removed assertion for `_access_order` in `test_clear_removes_all_entries()`

**Verification:**
- ruff format: PASS
- ruff check: PASS
- ty check: PASS (3 pre-existing issues in other files)
- pytest: PASS (184 passed, 6 deselected)

**Blockers:** None

---

### 2026-02-01 21:56 (CET)

**Tasks completed:** US-1, US-2, US-3, US-4, US-5

**Current task:** US-6 - Add network availability check for integration tests

**Changes made:**
- Modified `tests/test_integration.py`:
  - Added import for `socket` module
  - Added `network_available()` function that checks connectivity to api.semanticscholar.org:443 with 5 second timeout
  - Updated `pytestmark` from single marker to list with both `pytest.mark.integration` and `pytest.mark.skipif(not network_available(), reason="Network not available")`

**Verification:**
- ruff format: PASS
- ruff check: PASS
- ty check: PASS (3 pre-existing issues in other files)
- pytest: PASS (184 passed, 6 deselected)

**Blockers:** None

---

### 2026-02-01 21:50 (CET)

**Tasks completed:** US-1, US-2, US-3, US-4

**Current task:** US-5 - Add SSL bypass support for integration tests

**Changes made:**
- Modified `tests/test_integration.py`:
  - Added import for `logging` and `settings` from config
  - Added module-level logger
  - Updated `real_client` fixture docstring to explain SSL bypass support
  - Added warning log when `settings.disable_ssl_verify` is True
  - Added documentation in module docstring explaining how to use DISABLE_SSL_VERIFY

**Verification:**
- ruff format: PASS
- ruff check: PASS (1 unused import auto-fixed)
- ty check: PASS (3 pre-existing issues in other files)
- pytest: PASS (184 passed, 6 deselected)

**Blockers:** None

---

### 2026-02-01 21:23 (CET)
