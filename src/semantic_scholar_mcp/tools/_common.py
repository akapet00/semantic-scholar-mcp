"""Shared utilities for MCP tools.

This module provides shared constants, client accessor, and tracker accessor
for all tool modules to use consistently.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from semantic_scholar_mcp.client import SemanticScholarClient
from semantic_scholar_mcp.paper_tracker import PaperTracker
from semantic_scholar_mcp.paper_tracker import get_tracker as _get_tracker


class HasCitationCount(Protocol):
    """Protocol for objects that have a citationCount attribute."""

    citationCount: int | None


# Default fields to request from the API for comprehensive paper data
DEFAULT_PAPER_FIELDS = (
    "paperId,title,abstract,year,citationCount,authors,venue,"
    "publicationTypes,openAccessPdf,fieldsOfStudy,journal,externalIds,"
    "publicationDate,publicationVenue"
)

# Compact fields for list responses (search, citations, references, top papers)
# Reduces response size by excluding rarely-needed fields like journal, externalIds, etc.
COMPACT_PAPER_FIELDS = (
    "paperId,title,abstract,year,citationCount,authors,venue,openAccessPdf,fieldsOfStudy"
)

# Default fields to request from the API for comprehensive author data
DEFAULT_AUTHOR_FIELDS = (
    "authorId,name,affiliations,paperCount,citationCount,hIndex,externalIds,homepage"
)

# Fields to request when TLDR is included
PAPER_FIELDS_WITH_TLDR = f"{DEFAULT_PAPER_FIELDS},tldr"


def build_nested_paper_fields(prefix: str, *, compact: bool = False) -> str:
    """Build nested paper fields string for API requests.

    When fetching citations or references, the API requires field names to be
    prefixed with the nested object name (e.g., 'citingPaper.title').

    Args:
        prefix: The prefix to prepend to each field (e.g., 'citingPaper', 'citedPaper').
        compact: If True, use COMPACT_PAPER_FIELDS instead of DEFAULT_PAPER_FIELDS.
            Defaults to False for backward compatibility.

    Returns:
        A comma-separated string of prefixed field names.

    Example:
        >>> build_nested_paper_fields('citingPaper')
        'citingPaper.paperId,citingPaper.title,citingPaper.abstract,...'
        >>> build_nested_paper_fields('citingPaper', compact=True)
        'citingPaper.paperId,citingPaper.title,...'  # fewer fields
    """
    fields = COMPACT_PAPER_FIELDS if compact else DEFAULT_PAPER_FIELDS
    return f"{prefix}.{fields.replace(',', f',{prefix}.')}"


def sort_by_citations[T: HasCitationCount](items: Sequence[T], *, reverse: bool = True) -> list[T]:
    """Sort items by citation count.

    Generic helper function for sorting papers, authors, or any object with
    a citationCount attribute. Handles None values by treating them as 0.

    Args:
        items: Sequence of items with citationCount attribute.
        reverse: If True (default), sort in descending order (highest first).
                 If False, sort in ascending order (lowest first).

    Returns:
        A new list of items sorted by citation count.

    Example:
        >>> papers = [paper1, paper2, paper3]
        >>> top_papers = sort_by_citations(papers)  # Highest citations first
        >>> low_papers = sort_by_citations(papers, reverse=False)  # Lowest first
    """
    return sorted(items, key=lambda x: x.citationCount or 0, reverse=reverse)


def paper_not_found_message(paper_id: str) -> str:
    """Generate a user-friendly error message for paper not found errors.

    Args:
        paper_id: The paper ID that was not found.

    Returns:
        A formatted error message with guidance on paper ID formats.
    """
    return (
        f"Paper not found with ID '{paper_id}'. Please verify the ID is correct. "
        "For DOIs, use format 'DOI:10.xxxx/xxxxx'. "
        "For ArXiv IDs, use format 'ARXIV:xxxx.xxxxx'."
    )


def author_not_found_message(author_id: str) -> str:
    """Generate a user-friendly error message for author not found errors.

    Args:
        author_id: The author ID that was not found.

    Returns:
        A formatted error message with guidance on finding author IDs.
    """
    return (
        f"Author not found with ID '{author_id}'. Please verify the author ID is "
        "correct. You can find author IDs by using the search_authors tool."
    )


def get_tracker() -> PaperTracker:
    """Get the paper tracker instance.

    Returns:
        The singleton PaperTracker instance.
    """
    return _get_tracker()


# Client accessor - this will be set by server.py
_get_client_func: Callable[[], SemanticScholarClient] | None = None


def set_client_getter(func: Callable[[], SemanticScholarClient]) -> None:
    """Set the function to get the client (called by server.py).

    Args:
        func: A callable that returns a SemanticScholarClient instance.
    """
    global _get_client_func
    _get_client_func = func


def get_client() -> SemanticScholarClient:
    """Get the shared client instance.

    Returns:
        The shared SemanticScholarClient instance.

    Raises:
        RuntimeError: If the client getter has not been configured.
    """
    if _get_client_func is None:
        raise RuntimeError("Client getter not configured. Call set_client_getter first.")
    return _get_client_func()
