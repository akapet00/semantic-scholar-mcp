"""FastMCP server for Semantic Scholar API.

This module provides MCP tools for searching and analyzing academic papers
through the Semantic Scholar API.
"""

from fastmcp import FastMCP

from semantic_scholar_mcp.client import SemanticScholarClient
from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import (
    Author,
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

# Default fields to request from the API for comprehensive paper data
DEFAULT_PAPER_FIELDS = (
    "paperId,title,abstract,year,citationCount,authors,venue,"
    "publicationTypes,openAccessPdf,fieldsOfStudy"
)

# Default fields to request from the API for comprehensive author data
DEFAULT_AUTHOR_FIELDS = "authorId,name,affiliations,paperCount,citationCount,hIndex"

# Fields to request when TLDR is included
PAPER_FIELDS_WITH_TLDR = f"{DEFAULT_PAPER_FIELDS},tldr"

# Initialize the MCP server
mcp = FastMCP(
    name="semantic-scholar",
    instructions="Search and analyze academic papers through Semantic Scholar API",
)

# Shared client instance
_client: SemanticScholarClient | None = None


def get_client() -> SemanticScholarClient:
    """Get or create the shared client instance.

    Returns:
        The shared SemanticScholarClient instance.
    """
    global _client
    if _client is None:
        _client = SemanticScholarClient()
    return _client


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

    # Make API request
    client = get_client()
    response = await client.get("/paper/search", params=params)

    # Parse response
    result = SearchResult(**response)

    # Handle empty results
    if not result.data or len(result.data) == 0:
        return (
            f"No papers found matching '{query}'. Try broadening your search terms, "
            "removing filters, or using different keywords."
        )

    # Return papers (data is already list[Paper] from SearchResult)
    return [Paper(**paper.model_dump()) for paper in result.data]


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

    # Make API request
    client = get_client()
    try:
        response = await client.get(f"/paper/{paper_id}", params=params)
    except NotFoundError:
        return (
            f"Paper not found with ID '{paper_id}'. Please verify the ID is correct. "
            "For DOIs, use format 'DOI:10.xxxx/xxxxx'. "
            "For ArXiv IDs, use format 'ARXIV:xxxx.xxxxx'."
        )

    # Parse and return response
    return PaperWithTldr(**response)


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

    # Make API request
    client = get_client()
    try:
        response = await client.get(f"/paper/{paper_id}/citations", params=params)
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

    # Make API request
    client = get_client()
    try:
        response = await client.get(f"/paper/{paper_id}/references", params=params)
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

    # Make API request
    client = get_client()
    response = await client.get("/author/search", params=params)

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

    # Make API request for author details
    client = get_client()
    try:
        author_response = await client.get(f"/author/{author_id}", params=params)
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
        papers_response = await client.get(f"/author/{author_id}/papers", params=papers_params)
        papers_result = AuthorPapersResult(**papers_response)
        papers = papers_result.data

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

    # Make API request to recommendations endpoint
    client = get_client()
    try:
        response = await client.get(
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

    # Make API request to recommendations endpoint
    client = get_client()
    response = await client.post(
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

    return result.recommendedPapers


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
