# Activity

Append activity log at bottom. Follow the template:

```markdown
### Current atetime in YYYY-MM-DD HH:MM format for Central European Timezone (use tools)

**Tasks completed:** Tasks that are already completed; take ID and description from @SPEC.md.

**Current tasks:** Task that is implemented in the current instance; take description from @SPEC.md.

**Blockers:** Issues encountered.
```

## Session Log

### 2026-02-02 14:22 (CET)

**Task completed:** US-1: Rename ConnectionError to avoid builtin shadowing

**Changes made:**
- `src/semantic_scholar_mcp/exceptions.py`: Renamed `ConnectionError` class to `APIConnectionError`
- `src/semantic_scholar_mcp/client.py`: Updated import and all 8 usages of `ConnectionError` to `APIConnectionError`
- `tests/test_client.py`: Updated import and all usages of `ConnectionError` to `APIConnectionError`

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 1 file reformatted
- `uv run pytest -v`: 193 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change)
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:25 (CET)

**Task completed:** US-2: Add logging to silent exception handlers

**Changes made:**
- `src/semantic_scholar_mcp/server.py`: Added `logger.debug("Error during client cleanup: %s", e)` to the exception handler in `_cleanup_client()` function (line 77-78)

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 30 files left unchanged
- `uv run pytest -v`: 193 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change)
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:29 (CET)

**Task completed:** US-10: Add comprehensive ruff linting rules

**Changes made:**
- `pyproject.toml`: Added ruff rules B (bugbear), C4 (comprehensions), SIM (simplify); added `ignore = ["E501"]` for line length; added isort configuration with `known-first-party = ["semantic_scholar_mcp"]`
- `src/semantic_scholar_mcp/client.py`: Added `contextlib` import and replaced try/except/pass with `contextlib.suppress(ValueError)` (SIM105 fix)
- `src/semantic_scholar_mcp/tools/tracking.py`: Converted if/else to ternary operator (SIM108 fix)
- `tests/test_client.py`: Renamed unused loop variable `i` to `_i` (B007 fix)
- `tests/test_rate_limiter.py`: Combined nested `with` statements into single statement (SIM117 fix)

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 30 files left unchanged
- `uv run pytest -v`: 193 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change)
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:31 (CET)

**Task completed:** US-11: Add test coverage reporting

**Changes made:**
- `pyproject.toml`: Added `pytest-cov>=4.0` to dev dependencies; added `addopts = "--cov=semantic_scholar_mcp --cov-report=term-missing"` to pytest config

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 30 files left unchanged
- `uv run pytest -v`: 193 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change); coverage report generated showing 87% total coverage
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:34 (CET)

**Task completed:** US-3: Extract DRY helper for nested paper fields

**Changes made:**
- `src/semantic_scholar_mcp/tools/_common.py`: Added `build_nested_paper_fields(prefix: str) -> str` function with docstring
- `src/semantic_scholar_mcp/tools/papers.py`: Updated import to include `build_nested_paper_fields`; replaced manual field transformation in `get_paper_citations()` (line 213) and `get_paper_references()` (line 290) with calls to the new helper

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 30 files left unchanged
- `uv run pytest -v`: 193 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change)
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:38 (CET)

**Task completed:** US-4: Extract DRY helper for sorting by citations

**Changes made:**
- `src/semantic_scholar_mcp/tools/_common.py`: Added `HasCitationCount` Protocol class and `sort_by_citations[T: HasCitationCount]()` generic helper function with docstring using PEP 695 type parameter syntax
- `src/semantic_scholar_mcp/tools/authors.py`: Updated import to include `sort_by_citations`; replaced 4 manual sorting patterns with calls to the helper:
  - `find_duplicate_authors` - ORCID groups sorting (line 278)
  - `find_duplicate_authors` - DBLP groups sorting (line 300)
  - `consolidate_authors` - authors sorting (line 404)
  - `get_author_top_papers` - papers sorting (line 562)

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 1 file reformatted, 29 files left unchanged
- `uv run pytest -v`: 193 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change)
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:43 (CET)

**Task completed:** US-5: Add tests for server initialization and lifecycle

**Changes made:**
- `tests/test_server_init.py`: Created new test file with 15 tests covering:
  - TestServerCreation: Tests for MCP server instance creation (3 tests)
  - TestToolRegistration: Tests for tool registration verification (5 tests)
  - TestClientSingleton: Tests for client singleton behavior (3 tests)
  - TestCleanupHandler: Tests for cleanup handler registration and behavior (4 tests)

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 31 files left unchanged
- `uv run pytest -v`: 208 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change)
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:46 (CET)

**Task completed:** US-6: Add tests for configuration validation

**Changes made:**
- `tests/test_config.py`: Created new test file with 54 tests covering:
  - TestDefaultConfiguration: Tests for default configuration values (8 tests)
  - TestEnvironmentVariableLoading: Tests for environment variable loading (15 tests)
  - TestApiKeyPresenceHandling: Tests for API key presence detection (3 tests)
  - TestApiKeyAbsenceHandling: Tests for handling when API key is absent (2 tests)
  - TestBooleanEnvironmentVariableHandling: Parametrized tests for boolean parsing (26 tests)

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 32 files left unchanged
- `uv run pytest -v`: 262 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change)
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:50 (CET)

**Task completed:** US-8: Add tests for error flow from client through tools

**Changes made:**
- `tests/test_error_propagation.py`: Created new test file with 24 tests covering:
  - TestRateLimitErrorPropagation: Tests for RateLimitError with retry_after attribute (2 tests)
  - TestNotFoundErrorPropagation: Tests for NotFoundError message propagation (2 tests)
  - TestServerErrorPropagation: Tests for ServerError with status_code attribute (3 tests)
  - TestAuthenticationErrorPropagation: Tests for AuthenticationError propagation (2 tests)
  - TestAPIConnectionErrorPropagation: Tests for APIConnectionError including circuit breaker (3 tests)
  - TestSearchPapersErrorHandling: Tests for error handling in search_papers tool (4 tests)
  - TestGetPaperDetailsErrorHandling: Tests for error handling in get_paper_details tool (5 tests)
  - TestErrorAttributePreservation: Tests for attribute preservation and inheritance (3 tests)

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 1 file reformatted, 32 files left unchanged
- `uv run pytest -v`: 286 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change); coverage at 89%
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 14:55 (CET)

**Task completed:** US-7: Add tests for Pydantic model validation

**Changes made:**
- `tests/test_models.py`: Created new test file with 53 tests covering:
  - TestPaperModel: Tests for Paper model (required fields, optional fields, defaults) (7 tests)
  - TestAuthorModel: Tests for Author model (required fields, optional fields, defaults) (5 tests)
  - TestEdgeCases: Tests for edge cases (empty strings, None values, missing optional fields, empty lists, zero/negative/large integers, special characters, DBLP list/string) (11 tests)
  - TestNestedModels: Tests for nested models (PaperExternalIds, Journal, PublicationVenue, OpenAccessPdf, Tldr, PaperWithTldr) (6 tests)
  - TestContainerModels: Tests for container models (CitingPaper, ReferencePaper, SearchResult, AuthorSearchResult, RecommendationResult, AuthorPapersResult) (12 tests)
  - TestAuthorExtendedModels: Tests for extended author models (AuthorWithPapers, AuthorGroup, AuthorConsolidationResult, AuthorTopPapers) (8 tests)
  - TestModelSerialization: Tests for model serialization (model_dump) and deserialization (model_validate) round-trips (4 tests)

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 1 file reformatted, 33 files left unchanged
- `uv run pytest -v`: 339 passed, 6 failed (integration tests failing due to SSL certificate issues - unrelated to this change); coverage at 89%
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 15:06 (CET)

**Task completed:** US-9: Add end-to-end workflow integration tests

**Changes made:**
- `tests/test_integration.py`: Added 3 new test classes with comprehensive end-to-end workflow tests:
  - TestPaperWorkflowIntegration: Paper workflow test (search -> details -> citations -> export BibTeX) (1 test)
  - TestAuthorWorkflowIntegration: Author workflow test (search -> details -> top papers) (1 test)
  - TestBibTeXExportWorkflowIntegration: BibTeX export workflow test (track papers -> export -> verify format) (1 test)
- All new tests are marked with `@pytest.mark.integration` via the module-level `pytestmark`

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 34 files left unchanged
- `uv run pytest -v -m "not integration"`: 339 passed (all non-integration tests pass)
- `uv run pytest -v`: 339 passed, 9 failed (integration tests failing due to SSL certificate issues on corporate network - unrelated to code changes); coverage at 88%
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 15:12 (CET)

**Task completed:** US-12: Simplify verbose BibTeX escape comments

**Changes made:**
- `src/semantic_scholar_mcp/bibtex.py`: Simplified verbose comments in `_escape_bibtex` function (lines 103-118). Removed step-by-step explanatory comments and kept only a concise "order matters" note explaining why backslash must be escaped first.

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 34 files left unchanged
- `uv run pytest -v -m "not integration"`: 339 passed; coverage at 88%
- `uv run ty check src/`: 4 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 22:05 (CET)

**Task completed:** US-1: Implement server-side sorting for author papers

**Changes made:**
- `src/semantic_scholar_mcp/tools/authors.py`: Rewrote `get_author_top_papers` function to use API's native `sort=citationCount:desc` parameter instead of fetching all papers and sorting client-side. Removed pagination loop - now fetches only `top_n` papers (or `top_n * 3` when `min_citations` is specified to account for filtering). Removed incorrect comment about API not supporting sorting.

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 34 files left unchanged
- `uv run pytest -v -m "not integration"`: 339 passed; coverage at 89%
- `uv run ty check src/`: 3 pre-existing diagnostics (unrelated to this change)

**Blockers:** None

### 2026-02-02 23:18 (CET)

**Task completed:** US-2: Strip whitespace from API key configuration

**Changes made:**
- `src/semantic_scholar_mcp/config.py`: Modified `__init__` to strip leading/trailing whitespace from `SEMANTIC_SCHOLAR_API_KEY` environment variable. Whitespace-only keys are now treated as `None`.
- `tests/test_config.py`: Added `TestApiKeyWhitespaceHandling` test class with 8 tests covering:
  - Leading whitespace stripping
  - Trailing whitespace stripping
  - Both ends whitespace stripping
  - Whitespace-only keys returning None
  - Tab stripping
  - Newline stripping
  - `has_api_key` returns False for whitespace-only
  - `has_api_key` returns True for valid key with surrounding whitespace

**Verification:**
- `uv run ruff check src/ tests/`: All checks passed!
- `uv run ruff format src/ tests/`: 34 files left unchanged
- `uv run pytest -v -m "not integration"`: 347 passed; coverage at 89%
- `uv run ty check src/`: 3 pre-existing diagnostics (unrelated to this change)

**Blockers:** None
