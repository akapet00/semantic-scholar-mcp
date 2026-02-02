# Semantic Scholar MCP - Code Quality Improvement Plan

## Summary
Comprehensive code quality improvements following best practices, DRY principle, and proper testing.

## Decisions
- **Docstrings:** Keep verbose - they serve as MCP tool descriptions
- **Test coverage:** Comprehensive - all 4 new test files
- **Client refactor:** Keep as-is - current design is cohesive

---

## Phase 1: Fix Anti-patterns and Dead Code

### 1.1 Rename `ConnectionError` to avoid shadowing Python builtin
**Files:**
- `src/semantic_scholar_mcp/exceptions.py` - Rename class to `APIConnectionError`
- `src/semantic_scholar_mcp/client.py` - Update imports and usages (lines 17, 56-57, 287, 289, 335, 389, 391, 443)
- `tests/test_client.py` - Update test imports

### 1.2 Add logging to silent exception handlers
**File:** `src/semantic_scholar_mcp/server.py` (line 77-78)
```python
except Exception as e:
    logger.debug("Error during client cleanup: %s", e)
```

**Note:** `AuthenticationError` is NOT dead code - it's raised in `client.py:222` for 401/403 responses.

---

## Phase 2: DRY Refactoring

### 2.1 Extract nested paper fields builder
**File:** `src/semantic_scholar_mcp/tools/_common.py`
```python
def build_nested_paper_fields(prefix: str) -> str:
    """Build nested paper fields for citations/references API."""
    return f"{prefix}.{DEFAULT_PAPER_FIELDS.replace(',', f',{prefix}.')}"
```

**Updates:**
- `src/semantic_scholar_mcp/tools/papers.py:213` - Use `build_nested_paper_fields("citingPaper")`
- `src/semantic_scholar_mcp/tools/papers.py:290` - Use `build_nested_paper_fields("citedPaper")`

### 2.2 Extract author sorting helper
**File:** `src/semantic_scholar_mcp/tools/_common.py`
```python
def sort_by_citations[T](items: list[T], key_attr: str = "citationCount") -> list[T]:
    """Sort items by citation count (descending)."""
    return sorted(items, key=lambda x: getattr(x, key_attr, 0) or 0, reverse=True)
```

**Updates:** `src/semantic_scholar_mcp/tools/authors.py` - Replace 4 sorting patterns (lines 278, 305, 411, 575)

---

## Phase 3: Testing Improvements

### 3.1 New test files to create

| File | Purpose |
|------|---------|
| `tests/test_server_init.py` | Server initialization, tool registration, client lifecycle |
| `tests/test_config.py` | Configuration validation, env vars, defaults |
| `tests/test_models.py` | Pydantic model validation, edge cases |
| `tests/test_error_propagation.py` | Error flow from client through tools |

### 3.2 Enhance integration tests
**File:** `tests/test_integration.py`
- Add end-to-end workflow tests (search -> details -> citations -> export)
- Add author workflow tests
- Add BibTeX export workflow tests

---

## Phase 4: Tooling Configuration

### 4.1 Enhance ruff configuration
**File:** `pyproject.toml`
```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "SIM",  # flake8-simplify
]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["semantic_scholar_mcp"]
```

### 4.2 Add pytest-cov
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=4.0",
    "ruff>=0.9",
    "ty>=0.0.1a6",
]

[tool.pytest.ini_options]
addopts = "--cov=semantic_scholar_mcp --cov-report=term-missing"
```

---

## Phase 5: Comment Cleanup

### 5.1 Simplify verbose bibtex comments
**File:** `src/semantic_scholar_mcp/bibtex.py` (lines 103-118)
- Remove step-by-step comments, keep only the important "order matters" note

**Note:** Tool docstrings should remain verbose - they serve as MCP tool descriptions for Claude.

---

## Verification

After each phase:
```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pytest -v
uv run ty check src/
```

Final integration test:
```bash
uv run pytest tests/test_integration.py -v -m integration
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/semantic_scholar_mcp/exceptions.py` | Rename ConnectionError -> APIConnectionError |
| `src/semantic_scholar_mcp/client.py` | Update ConnectionError imports/usages |
| `src/semantic_scholar_mcp/server.py` | Add logging to cleanup exception handler |
| `src/semantic_scholar_mcp/tools/_common.py` | Add DRY helpers |
| `src/semantic_scholar_mcp/tools/papers.py` | Use nested fields helper |
| `src/semantic_scholar_mcp/tools/authors.py` | Use sort helper |
| `src/semantic_scholar_mcp/bibtex.py` | Simplify comments |
| `pyproject.toml` | Enhance ruff, add pytest-cov |
| `tests/test_client.py` | Update exception imports |

## New Test Files

- `tests/test_server_init.py`
- `tests/test_config.py`
- `tests/test_models.py`
- `tests/test_error_propagation.py`
