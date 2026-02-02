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
