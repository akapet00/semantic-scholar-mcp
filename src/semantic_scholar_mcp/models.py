"""Pydantic models for Semantic Scholar API responses."""

from pydantic import BaseModel, field_validator


class AuthorExternalIds(BaseModel):
    """External identifiers for an author.

    Attributes:
        ORCID: Open Researcher and Contributor ID.
        DBLP: DBLP computer science bibliography ID (can be a string or list of strings).
    """

    ORCID: str | None = None
    DBLP: str | list[str] | None = None


class PaperExternalIds(BaseModel):
    """External identifiers for a paper.

    Attributes:
        DOI: Digital Object Identifier.
        ArXiv: ArXiv preprint ID.
        MAG: Microsoft Academic Graph ID.
        ACL: ACL Anthology ID.
        PubMed: PubMed ID.
        PubMedCentral: PubMed Central ID.
        DBLP: DBLP bibliography ID.
        CorpusId: Semantic Scholar Corpus ID.
    """

    DOI: str | None = None
    ArXiv: str | None = None
    MAG: str | None = None
    ACL: str | None = None
    PubMed: str | None = None
    PubMedCentral: str | None = None
    DBLP: str | None = None
    CorpusId: int | None = None


class Journal(BaseModel):
    """Journal publication information.

    Attributes:
        name: Journal name.
        volume: Volume number.
        pages: Page range (e.g., "1-10").
    """

    name: str | None = None
    volume: str | None = None
    pages: str | None = None


class PublicationVenue(BaseModel):
    """Publication venue information.

    Attributes:
        id: Venue ID.
        name: Venue name.
        type: Venue type (e.g., "journal", "conference").
        alternate_names: Alternative names for the venue.
        issn: ISSN for journals.
        url: URL to the venue.
    """

    id: str | None = None
    name: str | None = None
    type: str | None = None
    alternate_names: list[str] | None = None
    issn: str | None = None
    url: str | None = None


class OpenAccessPdf(BaseModel):
    """Open access PDF information for a paper.

    Attributes:
        url: URL to the open access PDF.
        status: Status of the open access PDF (e.g., "GREEN", "GOLD").
    """

    url: str | None = None
    status: str | None = None


class Author(BaseModel):
    """Author information from Semantic Scholar.

    Attributes:
        authorId: Unique identifier for the author.
        name: Author's name.
        affiliations: List of author's institutional affiliations.
        paperCount: Total number of papers by this author.
        citationCount: Total citation count across all papers.
        hIndex: Author's h-index.
        aliases: Alternative names for the author.
        homepage: Author's homepage URL.
        externalIds: External identifiers (ORCID, DBLP).
    """

    authorId: str | None = None
    name: str | None = None
    affiliations: list[str] | None = None
    paperCount: int | None = None
    citationCount: int | None = None
    hIndex: int | None = None
    aliases: list[str] | None = None
    homepage: str | None = None
    externalIds: AuthorExternalIds | None = None


class Tldr(BaseModel):
    """TL;DR summary of a paper.

    Attributes:
        model: Model used to generate the summary.
        text: The summary text.
    """

    model: str | None = None
    text: str | None = None


class Paper(BaseModel):
    """Paper information from Semantic Scholar.

    Attributes:
        paperId: Unique identifier for the paper.
        title: Paper title.
        abstract: Paper abstract.
        year: Publication year.
        citationCount: Number of citations.
        authors: List of authors.
        venue: Publication venue (journal, conference, etc.).
        publicationTypes: Types of publication (e.g., "JournalArticle").
        openAccessPdf: Open access PDF information.
        fieldsOfStudy: List of fields of study.
        journal: Journal publication information.
        externalIds: External identifiers (DOI, ArXiv, etc.).
        publicationDate: Publication date in YYYY-MM-DD format.
        publicationVenue: Detailed publication venue information.
    """

    paperId: str | None = None
    title: str | None = None
    abstract: str | None = None
    year: int | None = None
    citationCount: int | None = None
    authors: list[Author] | None = None
    venue: str | None = None
    publicationTypes: list[str] | None = None
    openAccessPdf: OpenAccessPdf | None = None
    fieldsOfStudy: list[str] | None = None
    journal: Journal | None = None
    externalIds: PaperExternalIds | None = None
    publicationDate: str | None = None
    publicationVenue: PublicationVenue | None = None

    @field_validator("publicationVenue", mode="before")
    @classmethod
    def coerce_publication_venue(cls, v: object) -> object:
        """Coerce plain venue ID strings into PublicationVenue objects.

        The Semantic Scholar Recommendations API sometimes returns
        ``publicationVenue`` as a bare UUID string (e.g.
        ``"c7f73dd6-8431-403d-8268-80d666abe1bc"``) instead of the full
        venue object.  Without this validator, Pydantic rejects the string
        and ``get_recommendations`` / ``get_related_papers`` always fail
        with a validation error.
        """
        if isinstance(v, str):
            return PublicationVenue(id=v)
        return v


class PaperWithTldr(Paper):
    """Paper with TL;DR summary.

    Extends Paper model with an optional tldr field containing
    an AI-generated summary of the paper.

    Attributes:
        tldr: TL;DR summary of the paper.
    """

    tldr: Tldr | None = None


class CitingPaper(BaseModel):
    """Citation response containing the citing paper.

    Used in citation list responses where each item contains
    metadata about a paper that cites the queried paper.

    Attributes:
        citingPaper: The paper that cites the queried paper.
    """

    citingPaper: Paper


class ReferencePaper(BaseModel):
    """Reference response containing the cited paper.

    Used in reference list responses where each item contains
    metadata about a paper that is cited by the queried paper.

    Attributes:
        citedPaper: The paper that is cited by the queried paper.
    """

    citedPaper: Paper


class SearchResult(BaseModel):
    """Search result response from the API.

    Attributes:
        total: Total number of matching results.
        offset: Offset of the current page.
        next: Offset for the next page of results.
        data: List of papers or authors matching the search.
    """

    total: int = 0
    offset: int = 0
    next: int | None = None
    data: list[Paper] | list[Author] = []


class AuthorSearchResult(BaseModel):
    """Author search result response from the API.

    Attributes:
        total: Total number of matching results.
        offset: Offset of the current page.
        next: Offset for the next page of results.
        data: List of authors matching the search.
    """

    total: int = 0
    offset: int = 0
    next: int | None = None
    data: list[Author] = []


class RecommendationResult(BaseModel):
    """Recommendation response from the API.

    Attributes:
        recommendedPapers: List of recommended papers.
    """

    recommendedPapers: list[Paper] = []


class AuthorPapersResult(BaseModel):
    """Author papers response from the API.

    Attributes:
        data: List of papers by the author.
    """

    data: list[Paper] = []


class AuthorWithPapers(BaseModel):
    """Author information with their papers.

    Combines author metadata with their publication list.

    Attributes:
        authorId: Unique identifier for the author.
        name: Author's name.
        affiliations: List of author's institutional affiliations.
        paperCount: Total number of papers by this author.
        citationCount: Total citation count across all papers.
        hIndex: Author's h-index.
        papers: List of papers by the author.
    """

    authorId: str | None = None
    name: str | None = None
    affiliations: list[str] | None = None
    paperCount: int | None = None
    citationCount: int | None = None
    hIndex: int | None = None
    papers: list[Paper] | None = None


class AuthorGroup(BaseModel):
    """Group of potentially duplicate author records.

    Used for author consolidation to show authors that may represent
    the same person based on matching external IDs.

    Attributes:
        primary_author: The main author record (usually highest citation count).
        candidates: Other author records that may be duplicates.
        match_reasons: Reasons why these authors are grouped together.
    """

    primary_author: Author
    candidates: list[Author]
    match_reasons: list[str]


class AuthorConsolidationResult(BaseModel):
    """Result of author consolidation operation.

    Attributes:
        merged_author: The consolidated author record.
        source_authors: Original author records that were merged.
        match_type: Type of match that led to consolidation
            ("orcid", "dblp", "user_confirmed").
        confidence: Confidence score for the match (0.0 to 1.0).
        is_preview: Whether this is a preview (True) or confirmed merge (False).
        notes: Explanatory notes about the merged record (e.g., why certain
            fields like h-index cannot be computed for merged profiles).
    """

    merged_author: Author
    source_authors: list[Author]
    match_type: str
    confidence: float | None = None
    is_preview: bool = True
    notes: list[str] | None = None


class AuthorTopPapers(BaseModel):
    """Result of fetching an author's most cited papers.

    Provides a summary of an author's most influential work by citation count,
    which is more efficient than fetching all papers when you just need the
    most impactful publications.

    Attributes:
        author_id: The Semantic Scholar author ID.
        author_name: The author's name.
        total_papers: Total number of papers by this author.
        total_citations: Total citation count across all papers.
        papers_fetched: Number of papers fetched to find top N.
        top_papers: The top N papers sorted by citation count (highest first).
    """

    author_id: str
    author_name: str | None = None
    total_papers: int | None = None
    total_citations: int | None = None
    papers_fetched: int = 0
    top_papers: list[Paper] = []
