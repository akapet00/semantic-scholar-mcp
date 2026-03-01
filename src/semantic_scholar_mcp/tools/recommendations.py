"""Recommendation-related MCP tools.

This module provides tools for finding similar papers and recommendations
through the Semantic Scholar API.
"""

from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import (
    Paper,
    RecommendationResult,
)
from semantic_scholar_mcp.tools._common import (
    DEFAULT_PAPER_FIELDS,
    get_client,
    get_tracker,
    paper_not_found_message,
)


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
    # Validate limit
    limit = max(1, min(100, limit))

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
        return paper_not_found_message(paper_id)

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
    # Validate limit
    limit = max(1, min(100, limit))

    # Validate that at least one positive paper ID is provided
    if not positive_paper_ids:
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
    try:
        response = await client.post_with_retry(
            "/papers/",
            json_data=body,
            params=params,
            use_recommendations_api=True,
        )
    except NotFoundError:
        return paper_not_found_message(", ".join(positive_paper_ids))

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
