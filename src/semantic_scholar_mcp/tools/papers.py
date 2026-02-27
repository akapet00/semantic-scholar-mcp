"""Paper-related MCP tools.

This module provides tools for searching, fetching details, citations,
and references of academic papers through the Semantic Scholar API.
"""

from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import (
    CitingPaper,
    Paper,
    PaperWithTldr,
    ReferencePaper,
    SearchResult,
)
from semantic_scholar_mcp.tools._common import (
    COMPACT_PAPER_FIELDS,
    DEFAULT_PAPER_FIELDS,
    PAPER_FIELDS_WITH_TLDR,
    build_nested_paper_fields,
    get_client,
    get_tracker,
    paper_not_found_message,
)


def _parse_year_filter(year: str) -> tuple[int, int]:
    """Parse year filter string into (min_year, max_year) tuple."""
    if "-" in year:
        parts = year.split("-", 1)
        return int(parts[0]), int(parts[1])
    return int(year), int(year)


def _filter_by_year(papers: list[Paper], year: str) -> list[Paper]:
    """Filter papers by year range (client-side)."""
    min_year, max_year = _parse_year_filter(year)
    return [p for p in papers if p.year is not None and min_year <= p.year <= max_year]


async def search_papers(
    query: str,
    year: str | None = None,
    min_citation_count: int | None = None,
    fields_of_study: list[str] | None = None,
    limit: int = 10,
) -> list[Paper] | str:
    """Search for academic papers by keyword or phrase.

    Use this tool to find relevant literature on a research topic. The search
    looks at paper titles, abstracts, and other metadata to find matches.

    Args:
        query: Search query string (e.g., "transformer attention mechanism",
            "machine learning for drug discovery").
        year: Optional year range filter in format "YYYY" for single year or
            "YYYY-YYYY" for range (e.g., "2020" or "2020-2024").
        min_citation_count: Optional minimum citation count filter. Papers with
            fewer citations will be excluded.
        fields_of_study: Optional list of fields to filter by (e.g.,
            ["Computer Science", "Medicine"]).
        limit: Maximum number of results to return (1-100, default 10).

    Returns:
        List of papers matching the search query, each containing:
        - paperId: Unique Semantic Scholar ID
        - title: Paper title
        - abstract: Paper abstract (if available)
        - year: Publication year
        - citationCount: Number of citations
        - authors: List of authors with names and IDs
        - venue: Publication venue (journal, conference)
        - openAccessPdf: Link to open access PDF (if available)
        - fieldsOfStudy: Research fields the paper belongs to

        Returns an informative message if no papers match the query.

    Examples:
        >>> search_papers("attention is all you need")
        >>> search_papers("CRISPR gene editing", year="2020-2024", min_citation_count=50)
        >>> search_papers("neural networks", fields_of_study=["Computer Science"], limit=20)
    """
    # Validate limit
    limit = max(1, min(100, limit))

    # Build query parameters
    params: dict[str, str | int] = {
        "query": query,
        "fields": COMPACT_PAPER_FIELDS,
        "limit": limit,
    }

    if year is not None:
        params["year"] = year

    if min_citation_count is not None:
        params["minCitationCount"] = min_citation_count

    if fields_of_study is not None:
        params["fieldsOfStudy"] = ",".join(fields_of_study)

    # Make API request with automatic retry on rate limits
    client = get_client()
    response = await client.get_with_retry("/paper/search", params=params)

    # Parse response
    result = SearchResult(**response)

    # Handle empty results
    if not result.data:
        return (
            f"No papers found matching '{query}'. Try broadening your search terms, "
            "removing filters, or using different keywords."
        )

    # Return papers (data is already list[Paper] from SearchResult)
    papers = [Paper(**paper.model_dump()) for paper in result.data]

    # Track papers for BibTeX export
    tracker = get_tracker()
    tracker.track_many(papers, "search_papers")

    return papers


async def get_paper_details(
    paper_id: str,
    include_tldr: bool = True,
) -> PaperWithTldr | str:
    """Get detailed information about a specific paper.

    Use this tool to retrieve comprehensive metadata about a paper when you have
    its ID. Supports Semantic Scholar IDs, DOIs, and ArXiv IDs.

    Args:
        paper_id: The paper identifier. Can be:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI with prefix (e.g., "DOI:10.18653/v1/N18-3011")
            - ArXiv ID with prefix (e.g., "ARXIV:2106.15928")
        include_tldr: Whether to include the AI-generated TL;DR summary.
            Defaults to True.

    Returns:
        Complete paper metadata including:
        - paperId: Unique Semantic Scholar ID
        - title: Paper title
        - abstract: Paper abstract (if available)
        - year: Publication year
        - citationCount: Number of citations
        - authors: List of authors with names and IDs
        - venue: Publication venue (journal, conference)
        - openAccessPdf: Link to open access PDF (if available)
        - fieldsOfStudy: Research fields the paper belongs to
        - tldr: AI-generated summary (if available and requested)

        Returns an error message if the paper is not found.

    Examples:
        >>> get_paper_details("649def34f8be52c8b66281af98ae884c09aef38b")
        >>> get_paper_details("DOI:10.18653/v1/N18-3011")
        >>> get_paper_details("ARXIV:2106.15928", include_tldr=False)
    """
    # Select fields based on whether TLDR is requested
    fields = PAPER_FIELDS_WITH_TLDR if include_tldr else DEFAULT_PAPER_FIELDS

    # Build query parameters
    params: dict[str, str] = {"fields": fields}

    # Make API request with automatic retry on rate limits
    client = get_client()
    try:
        response = await client.get_with_retry(f"/paper/{paper_id}", params=params)
    except NotFoundError:
        return paper_not_found_message(paper_id)

    # Parse and return response
    paper = PaperWithTldr(**response)

    # Track paper for BibTeX export
    tracker = get_tracker()
    tracker.track(paper, "get_paper_details")

    return paper


async def get_paper_citations(
    paper_id: str,
    limit: int = 100,
    year: str | None = None,
) -> list[Paper] | str:
    """Get papers that cite a given paper.

    Use this tool to find follow-on work that builds upon or references a paper.
    This is useful for understanding a paper's impact and discovering subsequent
    research in the field.

    Args:
        paper_id: The paper identifier. Can be:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI with prefix (e.g., "DOI:10.18653/v1/N18-3011")
            - ArXiv ID with prefix (e.g., "ARXIV:2106.15928")
        limit: Maximum number of citing papers to return (1-1000, default 100).
        year: Optional year filter in format "YYYY" for single year or
            "YYYY-YYYY" for range (e.g., "2020" or "2020-2024").
            Note: Filtering is performed client-side because the S2 citations
            API does not support a year parameter. When a year filter is active,
            more results are fetched internally and then filtered, so the actual
            number of returned papers may be less than ``limit`` for narrow
            year ranges.

    Returns:
        List of papers that cite the given paper, each containing:
        - paperId: Unique Semantic Scholar ID
        - title: Paper title
        - abstract: Paper abstract (if available)
        - year: Publication year
        - citationCount: Number of citations
        - authors: List of authors with names and IDs
        - venue: Publication venue (journal, conference)
        - openAccessPdf: Link to open access PDF (if available)
        - fieldsOfStudy: Research fields the paper belongs to

        Returns an informative message if the paper has no citations or is not found.

    Examples:
        >>> get_paper_citations("649def34f8be52c8b66281af98ae884c09aef38b")
        >>> get_paper_citations("DOI:10.18653/v1/N18-3011", limit=50)
        >>> get_paper_citations("ARXIV:1706.03762", year="2020-2024")
    """
    # Validate limit
    limit = max(1, min(1000, limit))

    fields = build_nested_paper_fields("citingPaper", compact=True)
    client = get_client()

    if year is None:
        # No year filter — single request, current behaviour
        params: dict[str, str | int] = {"fields": fields, "limit": limit}
        try:
            response = await client.get_with_retry(
                f"/paper/{paper_id}/citations", params=params
            )
        except NotFoundError:
            return paper_not_found_message(paper_id)

        data = response.get("data", [])
        if not data:
            return (
                f"No citations found for paper '{paper_id}'. This paper may be too new "
                "to have citations, or citations may not yet be indexed."
            )

        citing_papers: list[Paper] = []
        for item in data:
            citing_papers.append(CitingPaper(**item).citingPaper)
    else:
        # Year filter active — paginate and filter client-side because the
        # S2 citations API ignores the year parameter.
        year_range = _parse_year_filter(year)
        citing_papers = []
        offset = 0
        batch_size = 1000
        max_fetch = 10_000  # safety cap

        while len(citing_papers) < limit and offset < max_fetch:
            params = {"fields": fields, "limit": batch_size, "offset": offset}
            try:
                response = await client.get_with_retry(
                    f"/paper/{paper_id}/citations", params=params
                )
            except NotFoundError:
                return paper_not_found_message(paper_id)

            data = response.get("data", [])
            for item in data:
                paper = CitingPaper(**item).citingPaper
                if (
                    paper.year is not None
                    and year_range[0] <= paper.year <= year_range[1]
                ):
                    citing_papers.append(paper)
                    if len(citing_papers) >= limit:
                        break

            if len(data) < batch_size:
                break  # last page
            offset += batch_size

        citing_papers = citing_papers[:limit]

        if not citing_papers:
            return (
                f"No citations found for paper '{paper_id}' in the year range '{year}'. "
                "Try broadening the year range."
            )

    # Track papers for BibTeX export
    tracker = get_tracker()
    tracker.track_many(citing_papers, "get_paper_citations")

    return citing_papers


async def get_paper_references(
    paper_id: str,
    limit: int = 100,
) -> list[Paper] | str:
    """Get papers that a given paper references (cites).

    Use this tool to find foundational work that a paper builds upon. This is useful
    for understanding the background research and key prior work in a field.

    Args:
        paper_id: The paper identifier. Can be:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI with prefix (e.g., "DOI:10.18653/v1/N18-3011")
            - ArXiv ID with prefix (e.g., "ARXIV:2106.15928")
        limit: Maximum number of referenced papers to return (1-1000, default 100).

    Returns:
        List of papers that the given paper references, each containing:
        - paperId: Unique Semantic Scholar ID
        - title: Paper title
        - abstract: Paper abstract (if available)
        - year: Publication year
        - citationCount: Number of citations
        - authors: List of authors with names and IDs
        - venue: Publication venue (journal, conference)
        - openAccessPdf: Link to open access PDF (if available)
        - fieldsOfStudy: Research fields the paper belongs to

        Returns an informative message if the paper has no references or is not found.

    Examples:
        >>> get_paper_references("649def34f8be52c8b66281af98ae884c09aef38b")
        >>> get_paper_references("DOI:10.18653/v1/N18-3011", limit=50)
        >>> get_paper_references("ARXIV:1706.03762")
    """
    # Validate limit
    limit = max(1, min(1000, limit))

    # Build query parameters
    params: dict[str, str | int] = {
        "fields": build_nested_paper_fields("citedPaper", compact=True),
        "limit": limit,
    }

    # Make API request with automatic retry on rate limits
    client = get_client()
    try:
        response = await client.get_with_retry(f"/paper/{paper_id}/references", params=params)
    except NotFoundError:
        return paper_not_found_message(paper_id)

    # Parse response - references come as list of {citedPaper: {...}}
    data = response.get("data", [])

    # Handle empty references
    if not data:
        return (
            f"No references found for paper '{paper_id}'. This paper may not have "
            "any references indexed, or it may be a preprint without a reference list."
        )

    # Extract referenced papers from the nested structure
    referenced_papers: list[Paper] = []
    for item in data:
        reference_paper_data = ReferencePaper(**item)
        referenced_papers.append(reference_paper_data.citedPaper)

    # Track papers for BibTeX export
    tracker = get_tracker()
    tracker.track_many(referenced_papers, "get_paper_references")

    return referenced_papers
