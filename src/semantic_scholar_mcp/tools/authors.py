"""Author-related MCP tools.

This module provides tools for searching, fetching details, finding duplicates,
and consolidating author records through the Semantic Scholar API.
"""

from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import (
    Author,
    AuthorConsolidationResult,
    AuthorGroup,
    AuthorPapersResult,
    AuthorSearchResult,
    AuthorTopPapers,
    AuthorWithPapers,
    Paper,
)
from semantic_scholar_mcp.tools._common import (
    COMPACT_PAPER_FIELDS,
    DEFAULT_AUTHOR_FIELDS,
    DEFAULT_PAPER_FIELDS,
    get_client,
    get_tracker,
    sort_by_citations,
)


def _normalize_dblp(dblp: str | list[str] | None) -> str | None:
    """Normalize DBLP field to a string.

    The Semantic Scholar API may return DBLP as either a string or a list of strings.
    This function normalizes it to a single string for consistent handling.

    Args:
        dblp: DBLP value from the API (string, list of strings, or None).

    Returns:
        The first DBLP value as a string, or None if not available.
    """
    if dblp is None:
        return None
    if isinstance(dblp, list):
        return dblp[0] if dblp else None
    return dblp


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
    if not result.data:
        return (
            f"No authors found matching '{query}'. Try using the author's full name, "
            "a different spelling, or check for any accents or special characters."
        )

    # Return authors
    return [Author(**author.model_dump()) for author in result.data]


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
        papers_response = await client.get_with_retry(
            f"/author/{author_id}/papers", params=papers_params
        )
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
        except NotFoundError:
            # Name not found is expected, continue with other names
            continue
        # Let other exceptions (RateLimitError, ServerError, etc.) propagate

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
        # Skip authors without authorId - can't deduplicate them reliably
        if not author.authorId:
            continue
        if author.authorId in seen_author_ids:
            continue
        seen_author_ids.add(author.authorId)

        if match_by_orcid and author.externalIds and author.externalIds.ORCID:
            orcid = author.externalIds.ORCID
            if orcid not in orcid_groups:
                orcid_groups[orcid] = []
            orcid_groups[orcid].append(author)

        if match_by_dblp and author.externalIds and author.externalIds.DBLP:
            dblp = _normalize_dblp(author.externalIds.DBLP)
            if dblp is not None:
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
            sorted_authors = sort_by_citations(authors)
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
            sorted_authors = sort_by_citations(remaining)
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
    dblps = [
        _normalize_dblp(a.externalIds.DBLP) for a in authors if a.externalIds and a.externalIds.DBLP
    ]
    dblps = [d for d in dblps if d is not None]  # Filter out None values
    if match_type == "user_confirmed" and len(dblps) >= 2 and len(set(dblps)) == 1:
        match_type = "dblp"
        confidence = 0.95

    # Sort by citation count to determine primary
    sorted_authors = sort_by_citations(authors)
    primary = sorted_authors[0]

    # Merge author records
    merged_affiliations: list[str] = []
    merged_aliases: list[str] = []

    for author in authors:
        if author.affiliations:
            for aff in author.affiliations:
                if aff not in merged_affiliations:
                    merged_affiliations.append(aff)
        if author.name and author.name not in merged_aliases:
            merged_aliases.append(author.name)

    # Remove primary name from aliases
    if primary.name and primary.name in merged_aliases:
        merged_aliases.remove(primary.name)

    # Sum paper and citation counts
    total_papers = sum(a.paperCount or 0 for a in authors)
    total_citations = sum(a.citationCount or 0 for a in authors)

    # Build notes for the merged record
    notes: list[str] = []

    # h-index cannot be computed for merged profiles - collect source h-indices
    source_hindices = [str(a.hIndex) for a in authors if a.hIndex is not None]
    if source_hindices:
        notes.append(
            "Note: h-index is not set for merged profiles because it cannot be "
            "accurately computed from multiple author records. The source authors' "
            f"h-indices are: {', '.join(source_hindices)}."
        )
    else:
        notes.append(
            "Note: h-index is not set for merged profiles because it cannot be "
            "accurately computed from multiple author records."
        )

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
        hIndex=None,  # Cannot be computed for merged profiles
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
        notes=notes if notes else None,
    )

    return result


async def get_author_top_papers(
    author_id: str,
    top_n: int = 5,
    min_citations: int | None = None,
) -> AuthorTopPapers | str:
    """Get an author's most cited papers.

    Fetches the author's papers and returns the top N by citation count.
    This is more efficient than get_author_details when you just need to find
    an author's most influential work, as it returns a smaller response focused
    on high-impact papers.

    Args:
        author_id: The Semantic Scholar author ID (e.g., "1741101").
        top_n: Number of top papers to return (default 5, max 100).
        min_citations: Optional minimum citation count filter. Papers with
            fewer citations will be excluded from results.

    Returns:
        AuthorTopPapers containing:
        - author_id: The Semantic Scholar author ID
        - author_name: The author's name
        - total_papers: Total number of papers by this author
        - total_citations: Total citation count across all papers
        - papers_fetched: Number of papers fetched to find top N
        - top_papers: The top N papers sorted by citation count (highest first)

        Returns an error message if the author is not found.

    Examples:
        >>> get_author_top_papers("1741101")  # Get top 5 papers
        >>> get_author_top_papers("1741101", top_n=10)  # Get top 10 papers
        >>> get_author_top_papers("1741101", min_citations=100)  # Only papers with 100+ citations
    """
    # Validate top_n
    top_n = max(1, min(100, top_n))

    # Fetch author details first
    client = get_client()
    params: dict[str, str] = {"fields": DEFAULT_AUTHOR_FIELDS}

    try:
        author_response = await client.get_with_retry(f"/author/{author_id}", params=params)
    except NotFoundError:
        return (
            f"Author not found with ID '{author_id}'. Please verify the author ID is "
            "correct. You can find author IDs by using the search_authors tool."
        )

    author = Author(**author_response)

    # Fetch all papers and sort client-side (API doesn't support sorting on this endpoint)
    # The /author/{author_id}/papers endpoint does not support the `sort` parameter,
    # so we need to fetch all papers and sort them ourselves.
    all_papers: list[Paper] = []
    offset = 0
    batch_size = 1000  # API max per request

    while True:
        papers_params: dict[str, str | int] = {
            "fields": COMPACT_PAPER_FIELDS,
            "limit": batch_size,
            "offset": offset,
        }
        papers_response = await client.get_with_retry(
            f"/author/{author_id}/papers", params=papers_params
        )
        papers_result = AuthorPapersResult(**papers_response)
        all_papers.extend(papers_result.data)

        # Stop if we got fewer papers than requested (no more pages)
        if len(papers_result.data) < batch_size:
            break
        offset += batch_size

    # Sort by citation count (highest first) - API doesn't support server-side sorting
    papers = sort_by_citations(all_papers)

    # Apply min_citations filter if specified (client-side filtering)
    if min_citations is not None:
        papers = [p for p in papers if (p.citationCount or 0) >= min_citations]

    # Take top N
    top_papers = papers[:top_n]

    # Track papers for BibTeX export
    if top_papers:
        tracker = get_tracker()
        tracker.track_many(top_papers, "get_author_top_papers")

    return AuthorTopPapers(
        author_id=author_id,
        author_name=author.name,
        total_papers=author.paperCount,
        total_citations=author.citationCount,
        papers_fetched=len(all_papers),
        top_papers=top_papers,
    )
