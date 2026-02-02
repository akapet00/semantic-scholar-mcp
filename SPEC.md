# Project Plan

## Overview

Code quality improvements for the Semantic Scholar MCP server addressing technical debt: Python builtin shadowing (`ConnectionError`), silent exception handlers, duplicated code patterns, incomplete linting configuration, and missing test coverage for critical paths.

**Reference:** `tasks/prd-code-quality-improvements.md`

---

## Task List

```json
[
  {
    "category": "refactor",
    "id": "US-1",
    "title": "Rename ConnectionError to avoid builtin shadowing",
    "description": "As a developer, I want the custom connection exception renamed to APIConnectionError so that Python's builtin ConnectionError is not shadowed and code behaves predictably",
    "steps": [
      "Rename ConnectionError to APIConnectionError in src/semantic_scholar_mcp/exceptions.py",
      "Update all imports and usages in src/semantic_scholar_mcp/client.py (8 occurrences)",
      "Update all imports and usages in tests/test_client.py",
      "All tests pass (uv run pytest)",
      "No ruff errors (uv run ruff check src/ tests/)"
    ],
    "passes": true
  },
  {
    "category": "refactor",
    "id": "US-2",
    "title": "Add logging to silent exception handlers",
    "description": "As a developer, I want exceptions logged in cleanup handlers so that I can debug issues during client shutdown",
    "steps": [
      "Add logger.debug call to exception handler in server.py:_cleanup_client()",
      "Log message format: logger.debug('Error during client cleanup: %s', e)",
      "Verify existing behavior preserved (cleanup still runs, exceptions still caught)",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "setup",
    "id": "US-10",
    "title": "Add comprehensive ruff linting rules",
    "description": "As a developer, I want strict linting rules so that code quality issues are caught automatically",
    "steps": [
      "Add rules B (bugbear), C4 (comprehensions), SIM (simplify) to pyproject.toml",
      "Add ignore = ['E501'] for line length",
      "Add isort configuration with known-first-party = ['semantic_scholar_mcp']",
      "Fix any new violations in src/ and tests/",
      "All files pass uv run ruff check src/ tests/",
      "All files formatted with uv run ruff format src/ tests/"
    ],
    "passes": true
  },
  {
    "category": "setup",
    "id": "US-11",
    "title": "Add test coverage reporting",
    "description": "As a developer, I want test coverage reports so that I can identify untested code paths",
    "steps": [
      "Add pytest-cov>=4.0 to dev dependencies in pyproject.toml",
      "Add addopts = '--cov=semantic_scholar_mcp --cov-report=term-missing' to pytest config",
      "Run uv sync to install new dependency",
      "Verify coverage report generated when running uv run pytest",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "refactor",
    "id": "US-3",
    "title": "Extract DRY helper for nested paper fields",
    "description": "As a developer, I want a reusable helper function for building nested paper fields so that I don't repeat the field transformation logic",
    "steps": [
      "Add build_nested_paper_fields(prefix: str) -> str function to src/semantic_scholar_mcp/tools/_common.py",
      "Add docstring documenting the function purpose and usage",
      "Update papers.py to use helper for citingPaper fields (get_paper_citations)",
      "Update papers.py to use helper for citedPaper fields (get_paper_references)",
      "All tests pass",
      "Type checker passes (uv run ty check src/)"
    ],
    "passes": false
  },
  {
    "category": "refactor",
    "id": "US-4",
    "title": "Extract DRY helper for sorting by citations",
    "description": "As a developer, I want a reusable helper function for sorting items by citation count so that I don't repeat the sorting lambda pattern",
    "steps": [
      "Add sort_by_citations[T]() generic helper to src/semantic_scholar_mcp/tools/_common.py",
      "Use type parameter for generic typing",
      "Add docstring documenting the function purpose and usage",
      "Update authors.py to use helper in get_author_details (papers sorting)",
      "Update authors.py to use helper in get_author_top_papers (top papers sorting)",
      "Update authors.py to use helper in find_duplicate_authors (candidates sorting)",
      "Update authors.py to use helper in consolidate_authors (papers sorting)",
      "All tests pass",
      "Type checker passes (uv run ty check src/)"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-5",
    "title": "Add tests for server initialization and lifecycle",
    "description": "As a developer, I want tests for server initialization so that I can catch regressions in tool registration and client lifecycle",
    "steps": [
      "Create new file tests/test_server_init.py",
      "Add test for server creation (mcp instance exists)",
      "Add test for tool registration (verify 14 tools registered)",
      "Add test for client singleton behavior (same instance returned)",
      "Add test for cleanup handler registration (atexit registered)",
      "Use appropriate fixtures from conftest.py",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-6",
    "title": "Add tests for configuration validation",
    "description": "As a developer, I want tests for configuration handling so that I can ensure environment variables and defaults work correctly",
    "steps": [
      "Create new file tests/test_config.py",
      "Add test for default configuration values",
      "Add test for environment variable loading (SEMANTIC_SCHOLAR_API_KEY)",
      "Add test for API key presence handling",
      "Add test for API key absence handling",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-8",
    "title": "Add tests for error flow from client through tools",
    "description": "As a developer, I want tests for error propagation so that I can ensure exceptions flow correctly from client to tool layer",
    "steps": [
      "Create new file tests/test_error_propagation.py",
      "Add test for RateLimitError propagation with retry_after attribute",
      "Add test for NotFoundError propagation with message",
      "Add test for ServerError propagation with status_code attribute",
      "Add test for AuthenticationError propagation",
      "Add test for APIConnectionError propagation",
      "Test error handling in search_papers tool function",
      "Test error handling in get_paper_details tool function",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-7",
    "title": "Add tests for Pydantic model validation",
    "description": "As a developer, I want tests for Pydantic models so that I can ensure data validation and edge cases are handled correctly",
    "steps": [
      "Create new file tests/test_models.py",
      "Add tests for Paper model (required fields, optional fields, defaults)",
      "Add tests for Author model (required fields, optional fields, defaults)",
      "Add tests for edge cases (empty strings, None values, missing optional fields)",
      "Add tests for model serialization (model_dump)",
      "Add tests for model deserialization (model_validate)",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "testing",
    "id": "US-9",
    "title": "Add end-to-end workflow integration tests",
    "description": "As a developer, I want comprehensive integration tests so that I can verify complete workflows function correctly",
    "steps": [
      "Add paper workflow test: search -> details -> citations -> export BibTeX",
      "Add author workflow test: search -> details -> top papers",
      "Add BibTeX export workflow test: track papers -> export -> verify format",
      "Mark all new tests with @pytest.mark.integration",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "refactor",
    "id": "US-12",
    "title": "Simplify verbose BibTeX escape comments",
    "description": "As a developer, I want concise comments in the BibTeX module so that the code is easier to read without losing important context",
    "steps": [
      "Locate verbose comments in src/semantic_scholar_mcp/bibtex.py (lines 103-118)",
      "Keep only the 'order matters' note explaining why backslash must be first",
      "Remove step-by-step explanatory comments",
      "Verify code behavior unchanged (existing tests pass)",
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
uv run pytest -v
```

**Integration tests:**
```bash
uv run pytest tests/test_integration.py -v -m integration
```

**Full verification (run after each task):**
```bash
uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run pytest -v && uv run ty check src/
```
