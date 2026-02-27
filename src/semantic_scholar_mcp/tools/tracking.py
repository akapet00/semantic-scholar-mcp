"""Tracking-related MCP tools.

This module provides tools for listing, clearing tracked papers,
and exporting them to BibTeX format.
"""

import os

from semantic_scholar_mcp.bibtex import (
    BibTeXExportConfig,
    BibTeXFieldConfig,
    export_papers_to_bibtex,
)
from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import Paper
from semantic_scholar_mcp.tools._common import (
    DEFAULT_PAPER_FIELDS,
    get_client,
    get_tracker,
)


async def list_tracked_papers(
    source_tool: str | None = None,
) -> list[Paper] | str:
    """List papers tracked during this session.

    Use this tool to see which papers have been retrieved during the current
    session. These papers can then be exported to BibTeX format.

    Args:
        source_tool: Optional filter to only show papers from a specific tool
            (e.g., "search_papers", "get_paper_details", "get_recommendations").
            If not provided, returns all tracked papers.

    Returns:
        List of tracked papers, or a message if no papers are tracked.

    Examples:
        >>> list_tracked_papers()  # All papers
        >>> list_tracked_papers(source_tool="search_papers")  # Only from search
    """
    tracker = get_tracker()

    papers = tracker.get_papers_by_tool(source_tool) if source_tool else tracker.get_all_papers()

    if not papers:
        if source_tool:
            return (
                f"No papers tracked from '{source_tool}'. "
                "Use search_papers, get_paper_details, or other tools to find papers first."
            )
        return (
            "No papers tracked in this session. "
            "Use search_papers, get_paper_details, get_recommendations, or other tools "
            "to find papers first."
        )

    return papers


async def clear_tracked_papers() -> str:
    """Clear all tracked papers from this session.

    Use this tool to reset the paper tracker, removing all previously
    tracked papers. This is useful when starting a new research session.

    Returns:
        Confirmation message indicating papers were cleared.

    Examples:
        >>> clear_tracked_papers()
    """
    tracker = get_tracker()
    count = tracker.count()
    tracker.clear()
    return f"Cleared {count} tracked papers from this session."


async def export_bibtex(
    paper_ids: list[str] | None = None,
    include_abstract: bool = False,
    include_url: bool = True,
    include_doi: bool = True,
    cite_key_format: str = "author_year",
    file_path: str | None = None,
) -> str:
    """Export papers to BibTeX format.

    Use this tool to export tracked papers or specific papers to BibTeX
    format for use in LaTeX documents and citation managers.

    Args:
        paper_ids: Optional list of specific paper IDs to export. If not
            provided, exports all tracked papers from this session.
        include_abstract: Whether to include paper abstracts. Defaults to False.
        include_url: Whether to include URLs. Defaults to True.
        include_doi: Whether to include DOIs. Defaults to True.
        cite_key_format: Format for citation keys:
            - "author_year": AuthorYear format (e.g., "vaswani2017")
            - "author_year_title": AuthorYearTitle (e.g., "vaswani2017attention")
            - "paper_id": Use Semantic Scholar paper ID
            Defaults to "author_year".
        file_path: Optional file path to write BibTeX output. If not provided,
            returns the BibTeX string directly.

    Returns:
        BibTeX formatted string, or confirmation message if written to file.

    Examples:
        >>> export_bibtex()  # Export all tracked papers
        >>> export_bibtex(include_abstract=True)  # Include abstracts
        >>> export_bibtex(file_path="references.bib")  # Write to file
        >>> export_bibtex(paper_ids=["abc123", "def456"])  # Specific papers
    """
    tracker = get_tracker()

    # Get papers to export
    if paper_ids:
        papers = tracker.get_papers_by_ids(paper_ids)
        if not papers:
            # Try to fetch papers if not tracked (with automatic retry on rate limits)
            client = get_client()
            papers = []
            for paper_id in paper_ids:
                try:
                    params: dict[str, str] = {"fields": DEFAULT_PAPER_FIELDS}
                    response = await client.get_with_retry(f"/paper/{paper_id}", params=params)
                    paper = Paper(**response)
                    papers.append(paper)
                    tracker.track(paper, "export_bibtex")
                except NotFoundError:
                    continue

        if not papers:
            return (
                "No papers found with the provided IDs. Please verify the paper IDs "
                "are correct, or use list_tracked_papers() to see available papers."
            )
    else:
        papers = tracker.get_all_papers()
        if not papers:
            return (
                "No papers tracked in this session to export. "
                "Use search_papers, get_paper_details, get_recommendations, or other "
                "tools to find papers first, then call export_bibtex()."
            )

    # Re-fetch papers that lack externalIds (needed for DOI/URL in BibTeX)
    if include_doi or include_url:
        client = get_client()
        enriched_papers = []
        for paper in papers:
            if paper.externalIds is None and paper.paperId:
                try:
                    params = {"fields": DEFAULT_PAPER_FIELDS}
                    response = await client.get_with_retry(f"/paper/{paper.paperId}", params=params)
                    enriched_papers.append(Paper(**response))
                except Exception:
                    enriched_papers.append(paper)  # fallback to original
            else:
                enriched_papers.append(paper)
        papers = enriched_papers

    # Configure export
    field_config = BibTeXFieldConfig(
        include_abstract=include_abstract,
        include_url=include_url,
        include_doi=include_doi,
    )
    export_config = BibTeXExportConfig(
        fields=field_config,
        cite_key_format=cite_key_format,
    )

    # Generate BibTeX
    bibtex_output = export_papers_to_bibtex(papers, export_config)

    # Write to file if path provided
    if file_path:
        # Expand user path and make absolute
        expanded_path = os.path.expanduser(file_path)
        abs_path = os.path.abspath(expanded_path)

        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(bibtex_output)
            return (
                f"Successfully exported {len(papers)} papers to BibTeX format.\n"
                f"File written to: {abs_path}"
            )
        except OSError as e:
            return f"Error writing to file '{abs_path}': {e}"

    # Return BibTeX string directly
    return bibtex_output
