"""FastMCP server for Semantic Scholar API.

This module initializes the MCP server and registers all tools.
"""

import asyncio
import atexit
import threading

from fastmcp import FastMCP

from semantic_scholar_mcp.client import SemanticScholarClient
from semantic_scholar_mcp.logging_config import get_logger, setup_logging
from semantic_scholar_mcp.tools import (
    clear_tracked_papers,
    consolidate_authors,
    export_bibtex,
    find_duplicate_authors,
    get_author_details,
    get_author_top_papers,
    get_paper_citations,
    get_paper_details,
    get_paper_references,
    get_recommendations,
    get_related_papers,
    list_tracked_papers,
    search_authors,
    search_papers,
)
from semantic_scholar_mcp.tools._common import set_client_getter

# Initialize logging
setup_logging()
logger = get_logger("server")

# Initialize the MCP server
mcp = FastMCP(
    name="semantic-scholar",
    instructions="Search and analyze academic papers through Semantic Scholar API",
)

# Shared client instance with thread-safe initialization
_client: SemanticScholarClient | None = None
_client_lock = threading.Lock()


def get_client() -> SemanticScholarClient:
    """Get or create the shared client instance (thread-safe).

    Returns:
        The shared SemanticScholarClient instance.
    """
    global _client
    if _client is None:
        with _client_lock:
            # Double-check locking pattern
            if _client is None:
                _client = SemanticScholarClient()
                logger.info("Created new SemanticScholarClient")
    assert _client is not None
    return _client


# Configure tools to use our client getter
set_client_getter(get_client)


def _cleanup_client() -> None:
    """Clean up the shared client instance on exit."""
    global _client
    if _client is not None:
        try:
            # Run the async close in a new event loop if needed
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_client.close())
            loop.close()
            logger.info("Client closed successfully")
        except Exception as e:
            logger.debug("Error during client cleanup: %s", e)
        _client = None


# Register cleanup handler
atexit.register(_cleanup_client)


# Register all tools with the MCP server
mcp.tool()(search_papers)
mcp.tool()(get_paper_details)
mcp.tool()(get_paper_citations)
mcp.tool()(get_paper_references)
mcp.tool()(search_authors)
mcp.tool()(get_author_details)
mcp.tool()(get_author_top_papers)
mcp.tool()(find_duplicate_authors)
mcp.tool()(consolidate_authors)
mcp.tool()(get_recommendations)
mcp.tool()(get_related_papers)
mcp.tool()(list_tracked_papers)
mcp.tool()(clear_tracked_papers)
mcp.tool()(export_bibtex)

logger.info("Registered %d MCP tools", 14)


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Semantic Scholar MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
