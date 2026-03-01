# Semantic Scholar MCP Server

A Model Context Protocol (MCP) server for searching and analyzing academic papers via the Semantic Scholar API.

> **Disclaimer:** This project is not officially affiliated with, endorsed by, or sponsored by Semantic Scholar or the Allen Institute for AI.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

## Quick Start

### Claude Code

```bash
claude mcp add semantic-scholar -s user -- uvx --from git+https://github.com/akapet00/semantic-scholar-mcp semantic-scholar-mcp
```

### Claude Desktop

Add to your config file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "semantic-scholar": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/akapet00/semantic-scholar-mcp",
        "semantic-scholar-mcp"
      ]
    }
  }
}
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "semantic-scholar": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/akapet00/semantic-scholar-mcp",
        "semantic-scholar-mcp"
      ]
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "semantic-scholar": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/akapet00/semantic-scholar-mcp",
        "semantic-scholar-mcp"
      ]
    }
  }
}
```

### OpenCode

Add to `opencode.json`:

```json
{
  "mcpServers": {
    "semantic-scholar": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/akapet00/semantic-scholar-mcp",
        "semantic-scholar-mcp"
      ]
    }
  }
}
```

### Other Clients

Any MCP-compatible client can use this server via stdio transport. Run the server with:

```bash
uvx --from git+https://github.com/akapet00/semantic-scholar-mcp semantic-scholar-mcp
```

## API Key (Optional)

The server works without an API key. For higher rate limits, get a key at https://www.semanticscholar.org/product/api and pass it as an environment variable.

| Access Level | Rate Limit |
|---|---|
| Without key | 5,000 requests per 5 minutes (shared pool) |
| With key | 1 request per second (dedicated) |

**Claude Code:**

```bash
claude mcp add semantic-scholar -s user -e SEMANTIC_SCHOLAR_API_KEY=your_key -- uvx --from git+https://github.com/akapet00/semantic-scholar-mcp semantic-scholar-mcp
```

**Claude Desktop / Cursor / Windsurf / OpenCode** — add an `"env"` block to the config:

```json
"env": {
  "SEMANTIC_SCHOLAR_API_KEY": "your_key"
}
```

## SSL Issues

If you're behind a corporate proxy or firewall and see `CERTIFICATE_VERIFY_FAILED` errors, set `DISABLE_SSL_VERIFY=true` as an environment variable (same approach as the API key above). Only use this in trusted networks.

## Why MCP?

The same prompt was run with and without this MCP server connected to Claude Code (Opus 4.6):

> *Find the first journal paper by Ante Kapetanovic and extract all references from that paper.*

| | Without MCP | With MCP |
|---|---|---|
| **Recall** | 85.3% (58/68 refs) | 100% (68/68 refs) |
| **Tool calls** | 40 (75% failed) | 14 (43% failed) |
| **Agent turns** | 30 | 10 |
| **Side effects** | pip install, temp files | None |

Without MCP, the agent spent most of its turns fighting HTTP errors, parsing raw HTML, and installing packages. With MCP, the author and paper were found in 2 turns. The same publisher restriction on references was hit, but recovery was faster and every reference was retrieved via a clean fallback.

Full analysis: [ANALYSIS.md](ANALYSIS.md)

## Tools Overview

### Papers

| Tool | What it does | Example |
|---|---|---|
| `search_papers` | Search papers by keyword with filters | `"CRISPR gene editing, 2020-2024, 50+ citations"` |
| `get_paper_details` | Get full metadata for a paper | `"DOI:10.18653/v1/N18-3011"` |
| `get_paper_citations` | Find papers that cite a given paper | `"ARXIV:1706.03762, year 2020-2024"` |
| `get_paper_references` | Find papers a given paper cites | `"ARXIV:1706.03762"` |

### Authors

| Tool | What it does | Example |
|---|---|---|
| `search_authors` | Search researchers by name | `"Geoffrey Hinton"` |
| `get_author_details` | Get author profile and publications | `author ID "1741101"` |
| `get_author_top_papers` | Get an author's most cited papers | `author ID "1741101", top 10` |
| `find_duplicate_authors` | Detect duplicate author records | `["G. Hinton", "Geoffrey Hinton"]` |
| `consolidate_authors` | Preview/merge duplicate records | `["1741101", "1741102"]` |

### Recommendations

| Tool | What it does | Example |
|---|---|---|
| `get_recommendations` | ML-based similar paper discovery | `"ARXIV:1706.03762"` |
| `get_related_papers` | Multi-paper recommendations | `positive: [paper1, paper2]` |

### Session & Export

| Tool | What it does | Example |
|---|---|---|
| `list_tracked_papers` | View papers retrieved this session | `source_tool="search_papers"` |
| `clear_tracked_papers` | Reset session tracking | — |
| `export_bibtex` | Export papers to BibTeX format | `file_path="references.bib"` |

## Updating

When installed via `git+https://...`, updates are not pulled automatically. To get the latest version:

```bash
# Refresh the cached package
uvx --refresh --from git+https://github.com/akapet00/semantic-scholar-mcp semantic-scholar-mcp

# Or re-add in Claude Code
claude mcp remove semantic-scholar -s user
claude mcp add semantic-scholar -s user -- uvx --from git+https://github.com/akapet00/semantic-scholar-mcp semantic-scholar-mcp
```

You can also pin to a specific branch, tag, or commit:

```bash
uvx --from git+https://github.com/akapet00/semantic-scholar-mcp@v0.1.0 semantic-scholar-mcp
```

## Development

```bash
git clone https://github.com/akapet00/semantic-scholar-mcp.git
cd semantic-scholar-mcp
uv sync

# Run tests
uv run pytest tests/ -v

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run ty check src/

# Dev mode with inspector
uv run fastmcp dev src/semantic_scholar_mcp/server.py
```

## Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for all environment variables (cache, retry, circuit breaker, logging, default limits).

## License

[MIT](LICENSE)
