# Project Plan

## Overview

Optimize the Semantic Scholar MCP server to reduce API calls, decrease response sizes, and improve reliability. The main issue is that `get_author_top_papers` incorrectly assumes the API doesn't support server-side sorting, leading to excessive API calls (up to 10,000 papers fetched) and large responses (~10.8k tokens). The API actually supports `sort=citationCount:desc`, which eliminates this problem.

**Reference:** `PRD.md`

---

## Task List

```json
[
  {
    "category": "feature",
    "id": "US-1",
    "title": "Implement server-side sorting for author papers",
    "description": "As an MCP user, I want get_author_top_papers to use the API's native sorting capability so that I get results quickly without hitting rate limits",
    "steps": [
      "Add sort=citationCount:desc parameter to author papers API request in tools/authors.py",
      "Remove pagination loop - only fetch top_n papers directly",
      "Remove or correct the incorrect comment about API sorting capability",
      "Update papers_fetched field in AuthorTopPapers response to reflect actual count",
      "Ensure min_citations filter is applied after API response (client-side filtering)",
      "Typecheck passes",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "setup",
    "id": "US-2",
    "title": "Strip whitespace from API key configuration",
    "description": "As a developer configuring the MCP server, I want API keys with accidental whitespace to be handled correctly so that I don't experience silent authentication failures",
    "steps": [
      "Modify config.py to strip leading/trailing whitespace from SEMANTIC_SCHOLAR_API_KEY",
      "Treat whitespace-only API keys as missing (None)",
      "Add unit test verifying whitespace stripping behavior",
      "Add unit test verifying whitespace-only keys return None",
      "Typecheck passes",
      "All tests pass"
    ],
    "passes": true
  },
  {
    "category": "feature",
    "id": "US-3",
    "title": "Use compact field sets for list responses",
    "description": "As an MCP user, I want search and list responses to include only essential fields so that responses are smaller and don't fill my context window",
    "steps": [
      "Define COMPACT_PAPER_FIELDS constant in tools/_common.py with: paperId, title, abstract, year, citationCount, authors, venue, openAccessPdf, fieldsOfStudy",
      "Update search_papers to use COMPACT_PAPER_FIELDS",
      "Update get_paper_citations to use compact fields for citingPaper",
      "Update get_paper_references to use compact fields for citedPaper",
      "Update get_author_top_papers to use COMPACT_PAPER_FIELDS",
      "Verify get_paper_details continues using DEFAULT_PAPER_FIELDS (full fields)",
      "Typecheck passes",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "setup",
    "id": "US-4",
    "title": "Environment variable configuration for default limits",
    "description": "As a developer deploying the MCP server, I want to configure default result limits via environment variables so that I can tune response sizes for my use case",
    "steps": [
      "Add SS_DEFAULT_SEARCH_LIMIT to config.py (default: 10, max: 100)",
      "Add SS_DEFAULT_PAPERS_LIMIT to config.py (default: 10, max: 1000)",
      "Add SS_DEFAULT_CITATIONS_LIMIT to config.py (default: 50, max: 1000)",
      "Add validation for positive integers within API limits",
      "Add unit tests verifying configuration is read correctly",
      "Add unit tests verifying defaults are applied when env vars not set",
      "Update README.md with new configuration options",
      "Typecheck passes",
      "All tests pass"
    ],
    "passes": false
  },
  {
    "category": "feature",
    "id": "US-5",
    "title": "Log warnings for large API responses",
    "description": "As a developer debugging the MCP server, I want large responses to be logged so that I can identify performance issues",
    "steps": [
      "Add SS_LARGE_RESPONSE_THRESHOLD to config.py (default: 50000 bytes)",
      "Add response size logging in client.py when response exceeds threshold",
      "Log at WARNING level with endpoint name and response size in bytes",
      "Measure size before JSON parsing (raw bytes)",
      "Add unit test verifying warning is logged for large responses",
      "Typecheck passes",
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
uv run ruff check .
```

**Type checking:**
```bash
uv run ty check
```

**Tests:**
```bash
uv run pytest tests/
```

**Run:**
```bash
uv run semantic-scholar-mcp
```

---

## Implementation Order

Tasks are ordered by priority:

1. **US-1** (P0 Critical): API sorting - biggest impact on rate limits and response size
2. **US-2** (P1 High): API key whitespace - quick fix, prevents configuration bugs
3. **US-3** (P1 High): Compact fields - reduces response size by 30-40%
4. **US-4** (P2 Medium): Configurable limits - nice to have after core optimizations
5. **US-5** (P3 Low): Response size logging - debugging aid

---

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| API calls (top 5 papers) | 2-11 | 2 |
| Response size (top papers) | 50-500KB | ~5KB |
| Token usage per query | ~10k | ~1-2k |
| Rate limit errors | Frequent | Rare |
