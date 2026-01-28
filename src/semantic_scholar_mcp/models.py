"""Pydantic models for Semantic Scholar API responses."""

from pydantic import BaseModel


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
    """

    authorId: str | None = None
    name: str | None = None
    affiliations: list[str] | None = None
    paperCount: int | None = None
    citationCount: int | None = None
    hIndex: int | None = None


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
