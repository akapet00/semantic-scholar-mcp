"""BibTeX export functionality for Semantic Scholar papers.

This module provides models and functions for converting paper metadata
to BibTeX format for use in academic writing and citation management.
"""

import re
import unicodedata
from enum import Enum

from pydantic import BaseModel

from semantic_scholar_mcp.models import Paper


class BibTeXEntryType(str, Enum):
    """BibTeX entry types for different publication types."""

    ARTICLE = "article"
    INPROCEEDINGS = "inproceedings"
    BOOK = "book"
    INCOLLECTION = "incollection"
    PHDTHESIS = "phdthesis"
    MASTERSTHESIS = "mastersthesis"
    TECHREPORT = "techreport"
    MISC = "misc"
    UNPUBLISHED = "unpublished"


class BibTeXFieldConfig(BaseModel):
    """Configuration for which fields to include in BibTeX export.

    Attributes:
        include_abstract: Whether to include the abstract field.
        include_url: Whether to include URL field.
        include_doi: Whether to include DOI field.
        include_keywords: Whether to include keywords field.
        max_authors: Maximum number of authors to include (0 = unlimited).
    """

    include_abstract: bool = False
    include_url: bool = True
    include_doi: bool = True
    include_keywords: bool = False
    max_authors: int = 0


class BibTeXExportConfig(BaseModel):
    """Configuration for BibTeX export.

    Attributes:
        fields: Field configuration for the export.
        cite_key_format: Format for generating citation keys.
            Options: "author_year", "author_year_title", "paper_id"
    """

    fields: BibTeXFieldConfig = BibTeXFieldConfig()
    cite_key_format: str = "author_year"


class BibTeXEntry(BaseModel):
    """A single BibTeX entry.

    Attributes:
        entry_type: The BibTeX entry type (article, inproceedings, etc.).
        cite_key: The citation key for this entry.
        fields: Dictionary of BibTeX field names to values.
    """

    entry_type: BibTeXEntryType
    cite_key: str
    fields: dict[str, str]

    def to_bibtex(self) -> str:
        """Convert this entry to BibTeX format string.

        Returns:
            Formatted BibTeX entry as a string.
        """
        lines = [f"@{self.entry_type.value}{{{self.cite_key},"]

        for key, value in self.fields.items():
            # Escape special BibTeX characters
            escaped_value = _escape_bibtex(value)
            lines.append(f"  {key} = {{{escaped_value}}},")

        lines.append("}")
        return "\n".join(lines)


def _escape_bibtex(text: str) -> str:
    """Escape special characters for BibTeX.

    Args:
        text: Text to escape.

    Returns:
        Escaped text safe for BibTeX.
    """
    # IMPORTANT: Order matters to avoid double-escaping.
    # First escape backslashes, then braces, then other special characters.
    # This prevents issues where replacements like \& would have their
    # braces escaped if { and } were processed first.

    # Step 1: Escape existing backslashes first (to avoid escaping our own backslashes)
    text = text.replace("\\", r"\textbackslash{}")

    # Step 2: Escape braces before other replacements that introduce braces
    text = text.replace("{", r"\{")
    text = text.replace("}", r"\}")

    # Step 3: Escape other special LaTeX characters
    # Note: These replacements introduce backslashes and braces, but those
    # are intentional LaTeX commands, not literal characters to escape.
    other_replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for char, replacement in other_replacements:
        text = text.replace(char, replacement)

    return text


def _normalize_for_cite_key(text: str) -> str:
    """Normalize text for use in a citation key.

    Removes accents, special characters, and converts to ASCII.

    Args:
        text: Text to normalize.

    Returns:
        Normalized ASCII text suitable for citation keys.
    """
    # Normalize unicode to decomposed form and remove accents
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Remove non-alphanumeric characters except spaces
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_text)

    # Replace spaces with nothing and convert to lowercase
    return cleaned.replace(" ", "").lower()


def detect_entry_type(paper: Paper) -> BibTeXEntryType:
    """Auto-detect BibTeX entry type from paper publication types.

    Args:
        paper: Paper to analyze.

    Returns:
        Appropriate BibTeXEntryType for the paper.
    """
    publication_types = paper.publicationTypes or []

    # Map publication types to BibTeX entry types
    type_mapping = {
        "JournalArticle": BibTeXEntryType.ARTICLE,
        "Conference": BibTeXEntryType.INPROCEEDINGS,
        "Book": BibTeXEntryType.BOOK,
        "BookSection": BibTeXEntryType.INCOLLECTION,
        "Review": BibTeXEntryType.ARTICLE,
        "Dataset": BibTeXEntryType.MISC,
        "Patent": BibTeXEntryType.MISC,
    }

    for pub_type in publication_types:
        if pub_type in type_mapping:
            return type_mapping[pub_type]

    # Check venue for conference indicators
    venue = (paper.venue or "").lower()
    conference_keywords = [
        "conference",
        "proceedings",
        "symposium",
        "workshop",
        "icml",
        "neurips",
        "nips",
        "iclr",
        "cvpr",
        "iccv",
        "eccv",
        "acl",
        "emnlp",
        "naacl",
        "aaai",
        "ijcai",
    ]
    if any(kw in venue for kw in conference_keywords):
        return BibTeXEntryType.INPROCEEDINGS

    # Check for journal indicators
    journal_keywords = ["journal", "transactions", "letters", "review"]
    if any(kw in venue for kw in journal_keywords):
        return BibTeXEntryType.ARTICLE

    # Check if paper has journal info
    if paper.journal and paper.journal.name:
        return BibTeXEntryType.ARTICLE

    # Default to misc for unknown types
    return BibTeXEntryType.MISC


def generate_cite_key(paper: Paper, format: str = "author_year") -> str:
    """Generate a citation key for a paper.

    Args:
        paper: Paper to generate key for.
        format: Key format - "author_year", "author_year_title", or "paper_id".

    Returns:
        Generated citation key.
    """
    if format == "paper_id":
        return paper.paperId or "unknown"

    # Get first author's last name
    author_part = "unknown"
    if paper.authors and len(paper.authors) > 0:
        first_author = paper.authors[0]
        if first_author.name:
            # Extract last name (last word of name)
            name_parts = first_author.name.split()
            if name_parts:
                author_part = _normalize_for_cite_key(name_parts[-1])

    # Get year
    year_part = str(paper.year) if paper.year else "unknown"

    if format == "author_year":
        return f"{author_part}{year_part}"

    if format == "author_year_title":
        # Get first significant word from title
        title_part = ""
        if paper.title:
            # Skip common words
            stop_words = {"a", "an", "the", "on", "in", "of", "for", "to", "and"}
            words = paper.title.split()
            for word in words:
                normalized = _normalize_for_cite_key(word)
                if normalized and normalized.lower() not in stop_words:
                    title_part = normalized[:10]  # Limit length
                    break
        return f"{author_part}{year_part}{title_part}"

    return f"{author_part}{year_part}"


def paper_to_bibtex_entry(
    paper: Paper,
    config: BibTeXExportConfig | None = None,
) -> BibTeXEntry:
    """Convert a Paper to a BibTeXEntry.

    Args:
        paper: Paper to convert.
        config: Export configuration. Uses defaults if not provided.

    Returns:
        BibTeXEntry representing the paper.
    """
    if config is None:
        config = BibTeXExportConfig()

    entry_type = detect_entry_type(paper)
    cite_key = generate_cite_key(paper, config.cite_key_format)

    fields: dict[str, str] = {}

    # Title
    if paper.title:
        fields["title"] = paper.title

    # Authors
    if paper.authors:
        authors_list = paper.authors
        if config.fields.max_authors > 0:
            authors_list = authors_list[: config.fields.max_authors]
            if len(paper.authors) > config.fields.max_authors:
                # Add "and others" indicator
                author_names = [a.name or "Unknown" for a in authors_list]
                author_names.append("others")
                fields["author"] = " and ".join(author_names)
            else:
                fields["author"] = " and ".join(
                    a.name or "Unknown" for a in authors_list
                )
        else:
            fields["author"] = " and ".join(a.name or "Unknown" for a in authors_list)

    # Year
    if paper.year:
        fields["year"] = str(paper.year)

    # Venue/booktitle/journal based on entry type
    if entry_type == BibTeXEntryType.INPROCEEDINGS:
        if paper.venue:
            fields["booktitle"] = paper.venue
        elif paper.publicationVenue and paper.publicationVenue.name:
            fields["booktitle"] = paper.publicationVenue.name
    elif entry_type == BibTeXEntryType.ARTICLE:
        if paper.journal and paper.journal.name:
            fields["journal"] = paper.journal.name
            if paper.journal.volume:
                fields["volume"] = paper.journal.volume
            if paper.journal.pages:
                fields["pages"] = paper.journal.pages
        elif paper.venue:
            fields["journal"] = paper.venue

    # Abstract (optional)
    if config.fields.include_abstract and paper.abstract:
        fields["abstract"] = paper.abstract

    # DOI (optional)
    if config.fields.include_doi and paper.externalIds and paper.externalIds.DOI:
        fields["doi"] = paper.externalIds.DOI

    # URL (optional)
    if config.fields.include_url:
        if paper.openAccessPdf and paper.openAccessPdf.url:
            fields["url"] = paper.openAccessPdf.url
        elif paper.externalIds and paper.externalIds.DOI:
            fields["url"] = f"https://doi.org/{paper.externalIds.DOI}"

    # Keywords (optional)
    if config.fields.include_keywords and paper.fieldsOfStudy:
        fields["keywords"] = ", ".join(paper.fieldsOfStudy)

    return BibTeXEntry(
        entry_type=entry_type,
        cite_key=cite_key,
        fields=fields,
    )


def export_papers_to_bibtex(
    papers: list[Paper],
    config: BibTeXExportConfig | None = None,
) -> str:
    """Export multiple papers to BibTeX format.

    Args:
        papers: List of papers to export.
        config: Export configuration. Uses defaults if not provided.

    Returns:
        BibTeX formatted string with all papers.
    """
    if config is None:
        config = BibTeXExportConfig()

    entries: list[str] = []
    seen_keys: set[str] = set()

    for paper in papers:
        entry = paper_to_bibtex_entry(paper, config)

        # Handle duplicate citation keys by appending a suffix
        original_key = entry.cite_key
        counter = 1
        while entry.cite_key in seen_keys:
            entry.cite_key = f"{original_key}{chr(ord('a') + counter - 1)}"
            counter += 1
            if counter > 26:
                entry.cite_key = f"{original_key}_{counter}"

        seen_keys.add(entry.cite_key)
        entries.append(entry.to_bibtex())

    return "\n\n".join(entries)
