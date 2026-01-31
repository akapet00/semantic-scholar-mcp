"""FastMCP server for Semantic Scholar API.

This module provides MCP tools for searching and analyzing academic papers
through the Semantic Scholar API.
"""

import atexit
import asyncio
import os
import threading

from fastmcp import FastMCP

from semantic_scholar_mcp.bibtex import (
    BibTeXExportConfig,
    BibTeXFieldConfig,
    export_papers_to_bibtex,
)
from semantic_scholar_mcp.client import SemanticScholarClient
from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import (
    Author,
    AuthorConsolidationResult,
    AuthorGroup,
    AuthorPapersResult,
    AuthorSearchResult,
    AuthorWithPapers,
    CitingPaper,
    Paper,
    PaperWithTldr,
    RecommendationResult,
    ReferencePaper,
    SearchResult,
)
from semantic_scholar_mcp.paper_tracker import get_tracker

# Default fields to request from the API for comprehensive paper data
DEFAULT_PAPER_FIELDS = (
    "paperId,title,abstract,year,citationCount,authors,venue,"
    "publicationTypes,openAccessPdf,fieldsOfStudy,journal,externalIds,"
    "publicationDate,publicationVenue"
)

# Default fields to request from the API for comprehensive author data
DEFAULT_AUTHOR_FIELDS = (
    "authorId,name,affiliations,paperCount,citationCount,hIndex,externalIds,aliases,homepage"
)

# Fields to request when TLDR is included
PAPER_FIELDS_WITH_TLDR = f"{DEFAULT_PAPER_FIELDS},tldr"

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
    return _client


def _cleanup_client() -> None:
    """Clean up the shared client instance on exit."""
    global _client
    if _client is not None:
        try:
            # Run the async close in a new event loop if needed
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_client.close())
            loop.close()
        except Exception:
            pass  # Ignore errors during cleanup
        _client = None


# Register cleanup handler
atexit.register(_cleanup_client)


@mcp.tool()
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
        "fields": DEFAULT_PAPER_FIELDS,
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
    if not result.data or len(result.data) == 0:
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


@mcp.tool()
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
        return (
            f"Paper not found with ID '{paper_id}'. Please verify the ID is correct. "
            "For DOIs, use format 'DOI:10.xxxx/xxxxx'. "
            "For ArXiv IDs, use format 'ARXIV:xxxx.xxxxx'."
        )

    # Parse and return response
    paper = PaperWithTldr(**response)

    # Track paper for BibTeX export
    tracker = get_tracker()
    tracker.track(paper, "get_paper_details")

    return paper


@mcp.tool()
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

    # Build query parameters
    params: dict[str, str | int] = {
        "fields": f"citingPaper.{DEFAULT_PAPER_FIELDS.replace(',', ',citingPaper.')}",
        "limit": limit,
    }

    if year is not None:
        params["year"] = year

    # Make API request with automatic retry on rate limits
    client = get_client()
    try:
        response = await client.get_with_retry(f"/paper/{paper_id}/citations", params=params)
    except NotFoundError:
        return (
            f"Paper not found with ID '{paper_id}'. Please verify the ID is correct. "
            "For DOIs, use format 'DOI:10.xxxx/xxxxx'. "
            "For ArXiv IDs, use format 'ARXIV:xxxx.xxxxx'."
        )

    # Parse response - citations come as list of {citingPaper: {...}}
    data = response.get("data", [])

    # Handle empty citations
    if not data:
        return (
            f"No citations found for paper '{paper_id}'. This paper may be too new "
            "to have citations, or citations may not yet be indexed."
        )

    # Extract citing papers from the nested structure
    citing_papers: list[Paper] = []
    for item in data:
        citing_paper_data = CitingPaper(**item)
        citing_papers.append(citing_paper_data.citingPaper)

    # Track papers for BibTeX export
    tracker = get_tracker()
    tracker.track_many(citing_papers, "get_paper_citations")

    return citing_papers


@mcp.tool()
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
        "fields": f"citedPaper.{DEFAULT_PAPER_FIELDS.replace(',', ',citedPaper.')}",
        "limit": limit,
    }

    # Make API request with automatic retry on rate limits
    client = get_client()
    try:
        response = await client.get_with_retry(f"/paper/{paper_id}/references", params=params)
    except NotFoundError:
        return (
            f"Paper not found with ID '{paper_id}'. Please verify the ID is correct. "
            "For DOIs, use format 'DOI:10.xxxx/xxxxx'. "
            "For ArXiv IDs, use format 'ARXIV:xxxx.xxxxx'."
        )

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


@mcp.tool()
async def search_authors(
    query: str,
    limit: int = 10,
) -> list[Author] | str:
    """Search for authors by name.

    Use this tool to find researchers and experts in a field by their name.
    This is useful for tracking specific researchers, finding experts on a topic,
    or discovering collaborators.

    Args:
        query: Author name to search for (e.g., "Geoffrey Hinton",
            "Yann LeCun", "Fei-Fei Li").
        limit: Maximum number of results to return (1-1000, default 10).

    Returns:
        List of authors matching the search query, each containing:
        - authorId: Unique Semantic Scholar ID for the author
        - name: Author's full name
        - affiliations: List of institutional affiliations (if available)
        - paperCount: Total number of papers by this author
        - citationCount: Total citation count across all papers
        - hIndex: Author's h-index (measure of research impact)

        Returns an informative message if no authors match the query.

    Examples:
        >>> search_authors("Geoffrey Hinton")
        >>> search_authors("Yoshua Bengio", limit=5)
        >>> search_authors("Smith", limit=20)  # Common names return multiple results
    """
    # Validate limit
    limit = max(1, min(1000, limit))

    # Build query parameters
    params: dict[str, str | int] = {
        "query": query,
        "fields": DEFAULT_AUTHOR_FIELDS,
        "limit": limit,
    }

    # Make API request with automatic retry on rate limits
    client = get_client()
    response = await client.get_with_retry("/author/search", params=params)

    # Parse response
    result = AuthorSearchResult(**response)

    # Handle empty results
    if not result.data or len(result.data) == 0:
        return (
            f"No authors found matching '{query}'. Try using the author's full name, "
            "a different spelling, or check for any accents or special characters."
        )

    # Return authors
    return [Author(**author.model_dump()) for author in result.data]


@mcp.tool()
async def get_author_details(
    author_id: str,
    include_papers: bool = True,
    papers_limit: int = 10,
) -> AuthorWithPapers | str:
    """Get detailed information about a specific author.

    Use this tool to retrieve comprehensive metadata about an author when you have
    their ID. This includes their profile information and optionally their list
    of publications.

    Args:
        author_id: The Semantic Scholar author ID (e.g., "1741101").
        include_papers: Whether to include the author's publications.
            Defaults to True.
        papers_limit: Maximum number of papers to return when include_papers is True.
            Defaults to 10.

    Returns:
        Complete author metadata including:
        - authorId: Unique Semantic Scholar ID for the author
        - name: Author's full name
        - affiliations: List of institutional affiliations (if available)
        - paperCount: Total number of papers by this author
        - citationCount: Total citation count across all papers
        - hIndex: Author's h-index (measure of research impact)
        - papers: List of the author's publications (if requested)

        Returns an error message if the author is not found.

    Examples:
        >>> get_author_details("1741101")
        >>> get_author_details("1741101", include_papers=False)
        >>> get_author_details("1741101", papers_limit=20)
    """
    # Build query parameters for author details
    params: dict[str, str] = {"fields": DEFAULT_AUTHOR_FIELDS}

    # Make API request for author details with automatic retry on rate limits
    client = get_client()
    try:
        author_response = await client.get_with_retry(f"/author/{author_id}", params=params)
    except NotFoundError:
        return (
            f"Author not found with ID '{author_id}'. Please verify the author ID is "
            "correct. You can find author IDs by using the search_authors tool."
        )

    # Parse author data
    author = Author(**author_response)

    # If papers are requested, fetch them separately
    papers: list[Paper] | None = None
    if include_papers:
        papers_params: dict[str, str | int] = {
            "fields": DEFAULT_PAPER_FIELDS,
            "limit": papers_limit,
        }
        papers_response = await client.get_with_retry(f"/author/{author_id}/papers", params=papers_params)
        papers_result = AuthorPapersResult(**papers_response)
        papers = papers_result.data

    # Track papers for BibTeX export if papers were fetched
    if papers:
        tracker = get_tracker()
        tracker.track_many(papers, "get_author_details")

    # Combine author data with papers
    return AuthorWithPapers(
        authorId=author.authorId,
        name=author.name,
        affiliations=author.affiliations,
        paperCount=author.paperCount,
        citationCount=author.citationCount,
        hIndex=author.hIndex,
        papers=papers,
    )


@mcp.tool()
async def get_recommendations(
    paper_id: str,
    limit: int = 10,
    from_pool: str = "recent",
) -> list[Paper] | str:
    """Find papers similar to a given paper using ML-based recommendations.

    Use this tool to discover related work that you might have missed. The
    Semantic Scholar recommendation system uses machine learning to find papers
    that are semantically similar to the input paper based on content, citations,
    and other signals.

    Args:
        paper_id: The paper identifier. Can be:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI with prefix (e.g., "DOI:10.18653/v1/N18-3011")
            - ArXiv ID with prefix (e.g., "ARXIV:2106.15928")
        limit: Maximum number of recommended papers to return (default 10).
        from_pool: The pool of papers to recommend from:
            - "recent": Recently published papers (default). Good for finding
              the latest related work.
            - "all-cs": All Computer Science papers. Good for comprehensive
              literature coverage.

    Returns:
        List of recommended papers ranked by similarity, each containing:
        - paperId: Unique Semantic Scholar ID
        - title: Paper title
        - abstract: Paper abstract (if available)
        - year: Publication year
        - citationCount: Number of citations
        - authors: List of authors with names and IDs
        - venue: Publication venue (journal, conference)
        - openAccessPdf: Link to open access PDF (if available)
        - fieldsOfStudy: Research fields the paper belongs to

        Returns an informative message if no recommendations are available
        or the paper is not found.

    Examples:
        >>> get_recommendations("649def34f8be52c8b66281af98ae884c09aef38b")
        >>> get_recommendations("ARXIV:1706.03762", limit=20)
        >>> get_recommendations("DOI:10.18653/v1/N18-3011", from_pool="all-cs")
    """
    # Validate from_pool parameter
    valid_pools = ("recent", "all-cs")
    if from_pool not in valid_pools:
        from_pool = "recent"

    # Build query parameters
    params: dict[str, str | int] = {
        "fields": DEFAULT_PAPER_FIELDS,
        "limit": limit,
        "from": from_pool,
    }

    # Make API request to recommendations endpoint with automatic retry on rate limits
    client = get_client()
    try:
        response = await client.get_with_retry(
            f"/papers/forpaper/{paper_id}",
            params=params,
            use_recommendations_api=True,
        )
    except NotFoundError:
        return (
            f"Paper not found with ID '{paper_id}'. Please verify the ID is correct. "
            "For DOIs, use format 'DOI:10.xxxx/xxxxx'. "
            "For ArXiv IDs, use format 'ARXIV:xxxx.xxxxx'."
        )

    # Parse response
    result = RecommendationResult(**response)

    # Handle empty recommendations
    if not result.recommendedPapers:
        return (
            f"No recommendations found for paper '{paper_id}'. This may happen for "
            "very new papers, papers in niche fields, or papers not well-covered "
            "in the recommendation model's training data."
        )

    # Track papers for BibTeX export
    tracker = get_tracker()
    tracker.track_many(result.recommendedPapers, "get_recommendations")

    return result.recommendedPapers


@mcp.tool()
async def get_related_papers(
    positive_paper_ids: list[str],
    negative_paper_ids: list[str] | None = None,
    limit: int = 10,
) -> list[Paper] | str:
    """Find papers related to multiple example papers using ML recommendations.

    Use this tool to refine your literature search by providing multiple papers
    as positive examples (papers you want more like) and optionally negative
    examples (papers you want to avoid). The Semantic Scholar recommendation
    system uses machine learning to find papers that are similar to the positive
    examples and dissimilar to the negative examples.

    This is particularly useful when you have identified a few relevant papers
    and want to find more work in the same area, while excluding certain
    tangential topics.

    Args:
        positive_paper_ids: List of paper IDs to find similar papers to.
            At least one paper ID is required. Can be:
            - Semantic Scholar IDs (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOIs with prefix (e.g., "DOI:10.18653/v1/N18-3011")
            - ArXiv IDs with prefix (e.g., "ARXIV:2106.15928")
        negative_paper_ids: Optional list of paper IDs to find dissimilar papers to.
            Papers similar to these will be ranked lower. Same ID formats as positive.
        limit: Maximum number of recommended papers to return (default 10).

    Returns:
        List of recommended papers ranked by relevance, each containing:
        - paperId: Unique Semantic Scholar ID
        - title: Paper title
        - abstract: Paper abstract (if available)
        - year: Publication year
        - citationCount: Number of citations
        - authors: List of authors with names and IDs
        - venue: Publication venue (journal, conference)
        - openAccessPdf: Link to open access PDF (if available)
        - fieldsOfStudy: Research fields the paper belongs to

        Returns an error message if no positive paper IDs are provided,
        or if no recommendations are available.

    Examples:
        >>> get_related_papers(["649def34f8be52c8b66281af98ae884c09aef38b"])
        >>> get_related_papers(
        ...     ["ARXIV:1706.03762", "ARXIV:1810.04805"],
        ...     limit=20
        ... )
        >>> get_related_papers(
        ...     positive_paper_ids=["DOI:10.18653/v1/N18-3011"],
        ...     negative_paper_ids=["DOI:10.1145/3292500.3330701"],
        ...     limit=15
        ... )
    """
    # Validate that at least one positive paper ID is provided
    if not positive_paper_ids or len(positive_paper_ids) == 0:
        return (
            "At least one positive paper ID is required. Please provide one or more "
            "paper IDs as examples of the type of papers you want to find."
        )

    # Build request body
    body: dict[str, list[str]] = {
        "positivePaperIds": positive_paper_ids,
    }

    if negative_paper_ids:
        body["negativePaperIds"] = negative_paper_ids

    # Build query parameters
    params: dict[str, str | int] = {
        "fields": DEFAULT_PAPER_FIELDS,
        "limit": limit,
    }

    # Make API request to recommendations endpoint with automatic retry on rate limits
    client = get_client()
    response = await client.post_with_retry(
        "/papers/",
        json_data=body,
        params=params,
        use_recommendations_api=True,
    )

    # Parse response
    result = RecommendationResult(**response)

    # Handle empty recommendations
    if not result.recommendedPapers:
        return (
            "No recommendations found for the provided papers. This may happen if "
            "the papers are too niche, too new, or not well-covered in the "
            "recommendation model's training data. Try using different seed papers."
        )

    # Track papers for BibTeX export
    tracker = get_tracker()
    tracker.track_many(result.recommendedPapers, "get_related_papers")

    return result.recommendedPapers


@mcp.tool()
async def find_duplicate_authors(
    author_names: list[str],
    match_by_orcid: bool = True,
    match_by_dblp: bool = True,
) -> list[AuthorGroup] | str:
    """Find potential duplicate author records by searching for names.

    Use this tool to identify authors who may have multiple records in
    Semantic Scholar. It searches for each name and groups results by
    matching external identifiers (ORCID, DBLP).

    Args:
        author_names: List of author names to search for (e.g.,
            ["Geoffrey Hinton", "G. Hinton", "Geoffrey E. Hinton"]).
        match_by_orcid: Whether to group authors by matching ORCID.
            Defaults to True.
        match_by_dblp: Whether to group authors by matching DBLP ID.
            Defaults to True.

    Returns:
        List of AuthorGroup objects, each containing:
        - primary_author: The main author record (highest citation count)
        - candidates: Other author records that may be duplicates
        - match_reasons: Reasons for grouping (e.g., "same_orcid", "same_dblp")

        Returns an informative message if no potential duplicates are found.

    Examples:
        >>> find_duplicate_authors(["Geoffrey Hinton", "G. Hinton"])
        >>> find_duplicate_authors(["Yoshua Bengio"], match_by_orcid=True)
    """
    if not author_names:
        return "Please provide at least one author name to search for."

    # Search for all author names with automatic retry on rate limits
    client = get_client()
    all_authors: list[Author] = []

    for name in author_names:
        params: dict[str, str | int] = {
            "query": name,
            "fields": DEFAULT_AUTHOR_FIELDS,
            "limit": 20,
        }
        try:
            response = await client.get_with_retry("/author/search", params=params)
            result = AuthorSearchResult(**response)
            all_authors.extend(result.data)
        except Exception:
            # Continue with other names if one fails
            continue

    if not all_authors:
        return (
            f"No authors found for the provided names: {', '.join(author_names)}. "
            "Try different name variations or check spelling."
        )

    # Group authors by external IDs
    orcid_groups: dict[str, list[Author]] = {}
    dblp_groups: dict[str, list[Author]] = {}
    seen_author_ids: set[str] = set()

    for author in all_authors:
        if author.authorId and author.authorId in seen_author_ids:
            continue
        if author.authorId:
            seen_author_ids.add(author.authorId)

        if match_by_orcid and author.externalIds and author.externalIds.ORCID:
            orcid = author.externalIds.ORCID
            if orcid not in orcid_groups:
                orcid_groups[orcid] = []
            orcid_groups[orcid].append(author)

        if match_by_dblp and author.externalIds and author.externalIds.DBLP:
            dblp = author.externalIds.DBLP
            if dblp not in dblp_groups:
                dblp_groups[dblp] = []
            dblp_groups[dblp].append(author)

    # Create author groups from matches
    author_groups: list[AuthorGroup] = []
    processed_author_ids: set[str] = set()

    # Process ORCID matches
    for orcid, authors in orcid_groups.items():
        if len(authors) > 1:
            # Sort by citation count to pick primary
            sorted_authors = sorted(
                authors,
                key=lambda a: a.citationCount or 0,
                reverse=True,
            )
            primary = sorted_authors[0]
            candidates = sorted_authors[1:]

            if primary.authorId:
                processed_author_ids.add(primary.authorId)
            for c in candidates:
                if c.authorId:
                    processed_author_ids.add(c.authorId)

            author_groups.append(
                AuthorGroup(
                    primary_author=primary,
                    candidates=candidates,
                    match_reasons=[f"same_orcid:{orcid}"],
                )
            )

    # Process DBLP matches (avoid duplicates from ORCID)
    for dblp, authors in dblp_groups.items():
        # Filter out already processed authors
        remaining = [a for a in authors if a.authorId and a.authorId not in processed_author_ids]
        if len(remaining) > 1:
            sorted_authors = sorted(
                remaining,
                key=lambda a: a.citationCount or 0,
                reverse=True,
            )
            primary = sorted_authors[0]
            candidates = sorted_authors[1:]

            if primary.authorId:
                processed_author_ids.add(primary.authorId)
            for c in candidates:
                if c.authorId:
                    processed_author_ids.add(c.authorId)

            author_groups.append(
                AuthorGroup(
                    primary_author=primary,
                    candidates=candidates,
                    match_reasons=[f"same_dblp:{dblp}"],
                )
            )

    if not author_groups:
        return (
            f"No potential duplicate authors found for: {', '.join(author_names)}. "
            "The authors found have unique external identifiers, or no external IDs "
            "are available to match against."
        )

    return author_groups


@mcp.tool()
async def consolidate_authors(
    author_ids: list[str],
    confirm_merge: bool = False,
) -> AuthorConsolidationResult | str:
    """Preview or confirm merging of duplicate author records.

    Use this tool after find_duplicate_authors to merge author records
    that represent the same person. By default, it shows a preview of
    what the merged record would look like.

    Note: This tool creates a local consolidated view. The actual Semantic
    Scholar database records are not modified.

    Args:
        author_ids: List of Semantic Scholar author IDs to merge
            (e.g., ["1741101", "1741102"]).
        confirm_merge: If False (default), shows preview of merged record.
            If True, returns the consolidated result.

    Returns:
        AuthorConsolidationResult containing:
        - merged_author: The consolidated author record
        - source_authors: Original author records that were merged
        - match_type: Type of match ("orcid", "dblp", "user_confirmed")
        - confidence: Confidence score if external IDs match

        Returns an error message if authors cannot be found or merged.

    Examples:
        >>> consolidate_authors(["1741101", "1741102"])  # Preview
        >>> consolidate_authors(["1741101", "1741102"], confirm_merge=True)
    """
    if not author_ids or len(author_ids) < 2:
        return "Please provide at least two author IDs to consolidate."

    # Fetch all author details with automatic retry on rate limits
    client = get_client()
    authors: list[Author] = []

    for author_id in author_ids:
        params: dict[str, str] = {"fields": DEFAULT_AUTHOR_FIELDS}
        try:
            response = await client.get_with_retry(f"/author/{author_id}", params=params)
            authors.append(Author(**response))
        except NotFoundError:
            return (
                f"Author not found with ID '{author_id}'. Please verify the author ID is correct."
            )

    if len(authors) < 2:
        return "Could not retrieve enough author records to consolidate."

    # Determine match type and confidence
    match_type = "user_confirmed"
    confidence: float | None = None

    # Check for ORCID match
    orcids = [a.externalIds.ORCID for a in authors if a.externalIds and a.externalIds.ORCID]
    if len(orcids) >= 2 and len(set(orcids)) == 1:
        match_type = "orcid"
        confidence = 1.0

    # Check for DBLP match
    dblps = [a.externalIds.DBLP for a in authors if a.externalIds and a.externalIds.DBLP]
    if match_type == "user_confirmed" and len(dblps) >= 2 and len(set(dblps)) == 1:
        match_type = "dblp"
        confidence = 0.95

    # Sort by citation count to determine primary
    sorted_authors = sorted(
        authors,
        key=lambda a: a.citationCount or 0,
        reverse=True,
    )
    primary = sorted_authors[0]

    # Merge author records
    merged_affiliations: list[str] = []
    merged_aliases: list[str] = []

    for author in authors:
        if author.affiliations:
            for aff in author.affiliations:
                if aff not in merged_affiliations:
                    merged_affiliations.append(aff)
        if author.aliases:
            for alias in author.aliases:
                if alias not in merged_aliases:
                    merged_aliases.append(alias)
        if author.name and author.name not in merged_aliases:
            merged_aliases.append(author.name)

    # Remove primary name from aliases
    if primary.name and primary.name in merged_aliases:
        merged_aliases.remove(primary.name)

    # Sum paper and citation counts
    total_papers = sum(a.paperCount or 0 for a in authors)
    total_citations = sum(a.citationCount or 0 for a in authors)
    max_hindex = max((a.hIndex or 0) for a in authors)

    # Get best external IDs
    best_external_ids = primary.externalIds
    if not best_external_ids:
        for author in authors:
            if author.externalIds:
                best_external_ids = author.externalIds
                break

    merged_author = Author(
        authorId=primary.authorId,
        name=primary.name,
        affiliations=merged_affiliations if merged_affiliations else None,
        paperCount=total_papers,
        citationCount=total_citations,
        hIndex=max_hindex,
        aliases=merged_aliases if merged_aliases else None,
        homepage=primary.homepage,
        externalIds=best_external_ids,
    )

    result = AuthorConsolidationResult(
        merged_author=merged_author,
        source_authors=authors,
        match_type=match_type,
        confidence=confidence,
        is_preview=not confirm_merge,
    )

    return result


@mcp.tool()
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

    if source_tool:
        papers = tracker.get_papers_by_tool(source_tool)
    else:
        papers = tracker.get_all_papers()

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


@mcp.tool()
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


@mcp.tool()
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


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
