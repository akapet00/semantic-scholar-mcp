# PRD: Semantic Scholar MCP - Code Quality Improvements

## 1. Introduction/Overview

The Semantic Scholar MCP server is a FastMCP-based tool that enables Claude to search and analyze academic papers via the Semantic Scholar API. While functionally complete, the codebase has accumulated technical debt including:

- A custom `ConnectionError` exception that shadows Python's builtin
- Silent exception handlers that swallow errors without logging
- Duplicated code patterns for sorting and field building
- Incomplete linting configuration
- Missing test coverage for critical paths (server initialization, configuration, models, error propagation)

This PRD defines a structured approach to address these issues, improving code quality, maintainability, and developer experience for future enhancements.

---

## 2. Goals

- Eliminate all Python builtin shadowing (rename `ConnectionError` → `APIConnectionError`)
- Add logging to all silent exception handlers
- Reduce code duplication via DRY helper functions
- Achieve comprehensive test coverage for critical paths
- Configure strict linting rules (zero ruff errors as CI gate)
- Simplify over-commented code sections

---

## 3. User Stories

### US-1: Rename ConnectionError to APIConnectionError

- **Title:** Rename ConnectionError to avoid builtin shadowing
- **Priority:** P0 (Critical)
- **Description:** "As a developer, I want the custom connection exception renamed to `APIConnectionError` so that Python's builtin `ConnectionError` is not shadowed and code behaves predictably"
- **Acceptance Criteria:**
  - [ ] `ConnectionError` renamed to `APIConnectionError` in `exceptions.py`
  - [ ] All imports updated in `client.py` (8 occurrences)
  - [ ] All imports updated in `tests/test_client.py`
  - [ ] All tests pass (`uv run pytest`)
  - [ ] No ruff errors (`uv run ruff check src/ tests/`)

**Files to modify:**
- `src/semantic_scholar_mcp/exceptions.py`
- `src/semantic_scholar_mcp/client.py`
- `tests/test_client.py`

---

### US-2: Add Logging to Silent Exception Handlers

- **Title:** Add logging to silent exception handlers
- **Priority:** P1 (High)
- **Description:** "As a developer, I want exceptions logged in cleanup handlers so that I can debug issues during client shutdown"
- **Acceptance Criteria:**
  - [ ] Exception handler in `server.py:_cleanup_client()` logs error at DEBUG level
  - [ ] Log message includes exception details: `logger.debug("Error during client cleanup: %s", e)`
  - [ ] Existing behavior preserved (cleanup still runs, exceptions still caught)
  - [ ] All tests pass

**Files to modify:**
- `src/semantic_scholar_mcp/server.py` (lines 77-78)

---

### US-3: Extract Nested Paper Fields Builder Helper

- **Title:** Extract DRY helper for nested paper fields
- **Priority:** P1 (High)
- **Description:** "As a developer, I want a reusable helper function for building nested paper fields so that I don't repeat the field transformation logic"
- **Acceptance Criteria:**
  - [ ] `build_nested_paper_fields(prefix: str) -> str` added to `tools/_common.py`
  - [ ] Function documented with docstring
  - [ ] `papers.py` updated to use helper for `citingPaper` fields (line ~213)
  - [ ] `papers.py` updated to use helper for `citedPaper` fields (line ~290)
  - [ ] All tests pass
  - [ ] Type checker passes (`uv run ty check src/`)

**Files to modify:**
- `src/semantic_scholar_mcp/tools/_common.py`
- `src/semantic_scholar_mcp/tools/papers.py`

---

### US-4: Extract Citation Sorting Helper

- **Title:** Extract DRY helper for sorting by citations
- **Priority:** P1 (High)
- **Description:** "As a developer, I want a reusable helper function for sorting items by citation count so that I don't repeat the sorting lambda pattern"
- **Acceptance Criteria:**
  - [ ] `sort_by_citations()` generic helper added to `tools/_common.py`
  - [ ] Function uses type parameter for generic typing
  - [ ] Function documented with docstring
  - [ ] `authors.py` updated to use helper (4 occurrences: lines ~278, ~305, ~411, ~575)
  - [ ] All tests pass
  - [ ] Type checker passes

**Files to modify:**
- `src/semantic_scholar_mcp/tools/_common.py`
- `src/semantic_scholar_mcp/tools/authors.py`

---

### US-5: Create Server Initialization Tests

- **Title:** Add tests for server initialization and lifecycle
- **Priority:** P1 (High)
- **Description:** "As a developer, I want tests for server initialization so that I can catch regressions in tool registration and client lifecycle"
- **Acceptance Criteria:**
  - [ ] New file `tests/test_server_init.py` created
  - [ ] Tests cover: server creation, tool registration (14 tools), client singleton behavior
  - [ ] Tests cover: cleanup handler registration, double-check locking
  - [ ] All tests pass
  - [ ] Tests use appropriate fixtures from conftest.py

**Files to create:**
- `tests/test_server_init.py`

---

### US-6: Create Configuration Tests

- **Title:** Add tests for configuration validation
- **Priority:** P1 (High)
- **Description:** "As a developer, I want tests for configuration handling so that I can ensure environment variables and defaults work correctly"
- **Acceptance Criteria:**
  - [ ] New file `tests/test_config.py` created
  - [ ] Tests cover: default values, environment variable loading
  - [ ] Tests cover: API key presence/absence handling
  - [ ] Tests cover: invalid configuration handling
  - [ ] All tests pass

**Files to create:**
- `tests/test_config.py`

---

### US-7: Create Pydantic Model Tests

- **Title:** Add tests for Pydantic model validation
- **Priority:** P2 (Medium)
- **Description:** "As a developer, I want tests for Pydantic models so that I can ensure data validation and edge cases are handled correctly"
- **Acceptance Criteria:**
  - [ ] New file `tests/test_models.py` created
  - [ ] Tests cover: required fields, optional fields, default values
  - [ ] Tests cover: edge cases (empty strings, None values, missing fields)
  - [ ] Tests cover: model serialization/deserialization
  - [ ] All tests pass

**Files to create:**
- `tests/test_models.py`

---

### US-8: Create Error Propagation Tests

- **Title:** Add tests for error flow from client through tools
- **Priority:** P1 (High)
- **Description:** "As a developer, I want tests for error propagation so that I can ensure exceptions flow correctly from client to tool layer"
- **Acceptance Criteria:**
  - [ ] New file `tests/test_error_propagation.py` created
  - [ ] Tests cover: `RateLimitError`, `NotFoundError`, `ServerError`, `AuthenticationError`, `APIConnectionError`
  - [ ] Tests verify error messages and attributes are preserved
  - [ ] Tests cover error handling in at least 2 tool functions
  - [ ] All tests pass

**Files to create:**
- `tests/test_error_propagation.py`

---

### US-9: Enhance Integration Tests

- **Title:** Add end-to-end workflow integration tests
- **Priority:** P2 (Medium)
- **Description:** "As a developer, I want comprehensive integration tests so that I can verify complete workflows function correctly"
- **Acceptance Criteria:**
  - [ ] Paper workflow test: search → details → citations → export BibTeX
  - [ ] Author workflow test: search → details → top papers
  - [ ] BibTeX export workflow test: track papers → export → verify format
  - [ ] Tests use `@pytest.mark.integration` marker
  - [ ] All tests pass

**Files to modify:**
- `tests/test_integration.py`

---

### US-10: Enhance Ruff Configuration

- **Title:** Add comprehensive ruff linting rules
- **Priority:** P1 (High)
- **Description:** "As a developer, I want strict linting rules so that code quality issues are caught automatically"
- **Acceptance Criteria:**
  - [ ] Add rules to `pyproject.toml`: B (bugbear), C4 (comprehensions), SIM (simplify)
  - [ ] Add `ignore = ["E501"]` for line length (handled separately)
  - [ ] Add isort configuration with `known-first-party`
  - [ ] All files pass `uv run ruff check src/ tests/`
  - [ ] All files formatted with `uv run ruff format src/ tests/`

**Files to modify:**
- `pyproject.toml`

---

### US-11: Add pytest-cov Configuration

- **Title:** Add test coverage reporting
- **Priority:** P2 (Medium)
- **Description:** "As a developer, I want test coverage reports so that I can identify untested code paths"
- **Acceptance Criteria:**
  - [ ] Add `pytest-cov>=4.0` to dev dependencies
  - [ ] Add pytest addopts for coverage: `--cov=semantic_scholar_mcp --cov-report=term-missing`
  - [ ] Coverage report generated when running `uv run pytest`
  - [ ] All tests pass

**Files to modify:**
- `pyproject.toml`

---

### US-12: Simplify BibTeX Comments

- **Title:** Simplify verbose BibTeX escape comments
- **Priority:** P3 (Low)
- **Description:** "As a developer, I want concise comments in the BibTeX module so that the code is easier to read without losing important context"
- **Acceptance Criteria:**
  - [ ] Comments in `bibtex.py` lines 103-118 simplified
  - [ ] Keep only the "order matters" note explaining why backslash must be first
  - [ ] Remove step-by-step explanatory comments
  - [ ] Code behavior unchanged
  - [ ] All tests pass

**Files to modify:**
- `src/semantic_scholar_mcp/bibtex.py`

---

## 4. Functional Requirements

- **FR-1:** `APIConnectionError` must inherit from `SemanticScholarError` and maintain the same interface as the current `ConnectionError`
- **FR-2:** All logging must use the existing logger from `logging_config.py`
- **FR-3:** DRY helpers must be type-safe and work with existing Pydantic models
- **FR-4:** New tests must use pytest and pytest-asyncio patterns consistent with existing tests
- **FR-5:** Ruff configuration must not break existing CI workflows
- **FR-6:** All changes must maintain backward compatibility with existing tool interfaces

---

## 5. Non-Goals (Out of Scope)

- No client.py refactoring beyond exception rename
- No new features or API endpoints
- No changes to MCP tool signatures or behavior
- No migration to different testing framework
- No changes to existing docstrings (they serve as MCP tool descriptions)
- No ORM or database changes
- No async/await pattern changes
- No dependency version upgrades beyond adding pytest-cov

---

## 6. Dependencies & Risks

### Dependencies

- `uv` - Package manager (already in use)
- `ruff>=0.9` - Linting and formatting (already in dev dependencies)
- `ty>=0.0.1a6` - Type checking (already in dev dependencies)
- `pytest>=8.0` - Testing framework (already in dev dependencies)
- `pytest-asyncio>=0.24` - Async test support (already in dev dependencies)
- `pytest-cov>=4.0` - Coverage reporting (to be added)

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Renaming exception breaks external code | Medium | Exception is internal; no public API change |
| New ruff rules flag existing code | Low | Fix violations incrementally; use `ignore` for false positives |
| Test coverage reveals bugs | Low | Track and fix bugs separately from this refactor |
| DRY helpers change behavior subtly | Medium | Ensure existing tests pass; add specific helper tests |

---

## 7. Technical Considerations

- **Thread Safety:** Client singleton uses double-check locking; tests must account for this
- **Async Patterns:** All client methods are async; tests use `pytest-asyncio`
- **Type Hints:** Project uses Python 3.13+ type syntax; helpers should use type parameters
- **Pydantic v2:** Models use Pydantic v2 syntax; tests should use `model_validate()`

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Ruff errors | 0 |
| Ruff warnings | 0 |
| Type errors (ty) | 0 |
| Test pass rate | 100% |
| Critical paths tested | All exception types, server init, config |
| Code duplication | Sorting pattern consolidated to 1 helper |

---

## 9. Implementation Order

Recommended sequence for minimal risk:

1. **US-1** (ConnectionError rename) - Foundation fix, unblocks other work
2. **US-2** (Logging) - Quick win, isolated change
3. **US-10** (Ruff config) - Enables catching issues early
4. **US-11** (pytest-cov) - Enables coverage tracking
5. **US-3, US-4** (DRY helpers) - Refactoring with safety net
6. **US-5, US-6, US-7, US-8** (New tests) - Expand coverage
7. **US-9** (Integration tests) - End-to-end validation
8. **US-12** (Comments) - Polish, lowest risk

---

## 10. Open Questions

- Should `APIConnectionError` include retry information like `RateLimitError` does?
- Should coverage threshold be enforced in CI (fail build if below X%)?
- Are there additional silent exception handlers elsewhere in the codebase?

---

## 11. Verification Commands

After each user story:

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pytest -v
uv run ty check src/
```

Final validation:

```bash
uv run pytest tests/test_integration.py -v -m integration
```
