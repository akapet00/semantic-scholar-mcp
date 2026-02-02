"""MCP tools for Semantic Scholar API.

This package contains modular tool implementations organized by functionality:
- papers: Paper search and details
- authors: Author search and details
- recommendations: Paper recommendations
- tracking: Paper tracking and BibTeX export
"""

from semantic_scholar_mcp.tools.authors import (
    consolidate_authors,
    find_duplicate_authors,
    get_author_details,
    get_author_top_papers,
    search_authors,
)
from semantic_scholar_mcp.tools.papers import (
    get_paper_citations,
    get_paper_details,
    get_paper_references,
    search_papers,
)
from semantic_scholar_mcp.tools.recommendations import (
    get_recommendations,
    get_related_papers,
)
from semantic_scholar_mcp.tools.tracking import (
    clear_tracked_papers,
    export_bibtex,
    list_tracked_papers,
)

__all__ = [
    # Papers
    "search_papers",
    "get_paper_details",
    "get_paper_citations",
    "get_paper_references",
    # Authors
    "search_authors",
    "get_author_details",
    "get_author_top_papers",
    "find_duplicate_authors",
    "consolidate_authors",
    # Recommendations
    "get_recommendations",
    "get_related_papers",
    # Tracking
    "list_tracked_papers",
    "clear_tracked_papers",
    "export_bibtex",
]
