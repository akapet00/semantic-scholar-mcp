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
    AuthorWithPapers,
    Paper,
)
from semantic_scholar_mcp.tools._common import (
    DEFAULT_AUTHOR_FIELDS,
    DEFAULT_PAPER_FIELDS,
    get_client,
    get_tracker,
)


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
