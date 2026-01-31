"""Unit tests for the BibTeX export module."""

import pytest

from semantic_scholar_mcp.bibtex import (
    BibTeXEntry,
    BibTeXEntryType,
    BibTeXExportConfig,
    BibTeXFieldConfig,
    detect_entry_type,
    export_papers_to_bibtex,
    generate_cite_key,
    paper_to_bibtex_entry,
)
from semantic_scholar_mcp.models import (
    Author,
    Journal,
    OpenAccessPdf,
    Paper,
    PaperExternalIds,
    PublicationVenue,
)


class TestBibTeXEntryType:
    """Tests for BibTeXEntryType enum."""

    def test_entry_types_exist(self) -> None:
        """Test that all expected entry types are defined."""
        assert BibTeXEntryType.ARTICLE.value == "article"
        assert BibTeXEntryType.INPROCEEDINGS.value == "inproceedings"
        assert BibTeXEntryType.BOOK.value == "book"
        assert BibTeXEntryType.MISC.value == "misc"


class TestBibTeXFieldConfig:
    """Tests for BibTeXFieldConfig model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = BibTeXFieldConfig()
        assert config.include_abstract is False
        assert config.include_url is True
        assert config.include_doi is True
        assert config.include_keywords is False
        assert config.max_authors == 0

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = BibTeXFieldConfig(
            include_abstract=True,
            include_url=False,
            max_authors=5,
        )
        assert config.include_abstract is True
        assert config.include_url is False
        assert config.max_authors == 5


class TestBibTeXEntry:
    """Tests for BibTeXEntry model."""

    def test_to_bibtex_basic(self) -> None:
        """Test basic BibTeX output generation."""
        entry = BibTeXEntry(
            entry_type=BibTeXEntryType.ARTICLE,
            cite_key="vaswani2017",
            fields={
                "title": "Attention Is All You Need",
                "author": "Vaswani, Ashish",
                "year": "2017",
            },
        )

        bibtex = entry.to_bibtex()

        assert "@article{vaswani2017," in bibtex
        assert "title = {Attention Is All You Need}," in bibtex
        assert "author = {Vaswani, Ashish}," in bibtex
        assert "year = {2017}," in bibtex
        assert bibtex.endswith("}")

    def test_to_bibtex_escapes_special_characters(self) -> None:
        """Test that special LaTeX characters are escaped."""
        entry = BibTeXEntry(
            entry_type=BibTeXEntryType.ARTICLE,
            cite_key="test2020",
            fields={
                "title": "Test & Demo: 100% Success",
            },
        )

        bibtex = entry.to_bibtex()

        assert r"Test \& Demo: 100\% Success" in bibtex


class TestDetectEntryType:
    """Tests for detect_entry_type function."""

    def test_journal_article_detection(self) -> None:
        """Test detection of journal articles."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            publicationTypes=["JournalArticle"],
        )

        entry_type = detect_entry_type(paper)

        assert entry_type == BibTeXEntryType.ARTICLE

    def test_conference_detection(self) -> None:
        """Test detection of conference papers."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            publicationTypes=["Conference"],
        )

        entry_type = detect_entry_type(paper)

        assert entry_type == BibTeXEntryType.INPROCEEDINGS

    def test_book_detection(self) -> None:
        """Test detection of books."""
        paper = Paper(
            paperId="123",
            title="Test Book",
            publicationTypes=["Book"],
        )

        entry_type = detect_entry_type(paper)

        assert entry_type == BibTeXEntryType.BOOK

    def test_conference_venue_detection(self) -> None:
        """Test detection based on venue name."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            venue="NeurIPS 2020",
        )

        entry_type = detect_entry_type(paper)

        assert entry_type == BibTeXEntryType.INPROCEEDINGS

    def test_journal_venue_detection(self) -> None:
        """Test detection based on journal venue."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            venue="Journal of Machine Learning",
        )

        entry_type = detect_entry_type(paper)

        assert entry_type == BibTeXEntryType.ARTICLE

    def test_journal_info_detection(self) -> None:
        """Test detection based on journal field."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            journal=Journal(name="Nature"),
        )

        entry_type = detect_entry_type(paper)

        assert entry_type == BibTeXEntryType.ARTICLE

    def test_unknown_defaults_to_misc(self) -> None:
        """Test that unknown types default to misc."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
        )

        entry_type = detect_entry_type(paper)

        assert entry_type == BibTeXEntryType.MISC


class TestGenerateCiteKey:
    """Tests for generate_cite_key function."""

    def test_author_year_format(self) -> None:
        """Test author_year citation key format."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            authors=[Author(authorId="1", name="John Smith")],
        )

        key = generate_cite_key(paper, "author_year")

        assert key == "smith2020"

    def test_author_year_title_format(self) -> None:
        """Test author_year_title citation key format."""
        paper = Paper(
            paperId="123",
            title="Attention Is All You Need",
            year=2017,
            authors=[Author(authorId="1", name="Ashish Vaswani")],
        )

        key = generate_cite_key(paper, "author_year_title")

        assert key == "vaswani2017attention"

    def test_paper_id_format(self) -> None:
        """Test paper_id citation key format."""
        paper = Paper(
            paperId="abc123def456",
            title="Test Paper",
            year=2020,
            authors=[Author(authorId="1", name="John Smith")],
        )

        key = generate_cite_key(paper, "paper_id")

        assert key == "abc123def456"

    def test_handles_missing_author(self) -> None:
        """Test handling of paper with no authors."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
        )

        key = generate_cite_key(paper, "author_year")

        assert key == "unknown2020"

    def test_handles_missing_year(self) -> None:
        """Test handling of paper with no year."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            authors=[Author(authorId="1", name="John Smith")],
        )

        key = generate_cite_key(paper, "author_year")

        assert key == "smithunknown"

    def test_normalizes_accented_characters(self) -> None:
        """Test that accented characters are normalized."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            authors=[Author(authorId="1", name="José García")],
        )

        key = generate_cite_key(paper, "author_year")

        assert key == "garcia2020"


class TestPaperToBibtexEntry:
    """Tests for paper_to_bibtex_entry function."""

    def test_basic_paper_conversion(self) -> None:
        """Test conversion of a basic paper."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            authors=[
                Author(authorId="1", name="John Smith"),
                Author(authorId="2", name="Jane Doe"),
            ],
            venue="Test Conference",
        )

        entry = paper_to_bibtex_entry(paper)

        assert entry.cite_key == "smith2020"
        assert entry.fields["title"] == "Test Paper"
        assert entry.fields["year"] == "2020"
        assert "John Smith" in entry.fields["author"]
        assert "Jane Doe" in entry.fields["author"]

    def test_includes_doi_by_default(self) -> None:
        """Test that DOI is included by default."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            externalIds=PaperExternalIds(DOI="10.1234/test"),
        )

        entry = paper_to_bibtex_entry(paper)

        assert entry.fields["doi"] == "10.1234/test"

    def test_excludes_doi_when_configured(self) -> None:
        """Test that DOI is excluded when configured."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            externalIds=PaperExternalIds(DOI="10.1234/test"),
        )
        config = BibTeXExportConfig(
            fields=BibTeXFieldConfig(include_doi=False),
        )

        entry = paper_to_bibtex_entry(paper, config)

        assert "doi" not in entry.fields

    def test_includes_abstract_when_configured(self) -> None:
        """Test that abstract is included when configured."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            abstract="This is the abstract.",
        )
        config = BibTeXExportConfig(
            fields=BibTeXFieldConfig(include_abstract=True),
        )

        entry = paper_to_bibtex_entry(paper, config)

        assert entry.fields["abstract"] == "This is the abstract."

    def test_excludes_abstract_by_default(self) -> None:
        """Test that abstract is excluded by default."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            abstract="This is the abstract.",
        )

        entry = paper_to_bibtex_entry(paper)

        assert "abstract" not in entry.fields

    def test_includes_url_from_open_access_pdf(self) -> None:
        """Test that URL is included from open access PDF."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            openAccessPdf=OpenAccessPdf(url="https://arxiv.org/pdf/1234.pdf"),
        )

        entry = paper_to_bibtex_entry(paper)

        assert entry.fields["url"] == "https://arxiv.org/pdf/1234.pdf"

    def test_includes_journal_info(self) -> None:
        """Test that journal information is included."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            publicationTypes=["JournalArticle"],
            journal=Journal(name="Nature", volume="580", pages="1-10"),
        )

        entry = paper_to_bibtex_entry(paper)

        assert entry.entry_type == BibTeXEntryType.ARTICLE
        assert entry.fields["journal"] == "Nature"
        assert entry.fields["volume"] == "580"
        assert entry.fields["pages"] == "1-10"

    def test_limits_authors_when_configured(self) -> None:
        """Test that author count is limited when configured."""
        paper = Paper(
            paperId="123",
            title="Test Paper",
            year=2020,
            authors=[
                Author(authorId=str(i), name=f"Author {i}")
                for i in range(10)
            ],
        )
        config = BibTeXExportConfig(
            fields=BibTeXFieldConfig(max_authors=3),
        )

        entry = paper_to_bibtex_entry(paper, config)

        assert "Author 0" in entry.fields["author"]
        assert "Author 2" in entry.fields["author"]
        assert "others" in entry.fields["author"]
        assert "Author 5" not in entry.fields["author"]


class TestExportPapersToBibtex:
    """Tests for export_papers_to_bibtex function."""

    def test_exports_multiple_papers(self) -> None:
        """Test export of multiple papers."""
        papers = [
            Paper(
                paperId="123",
                title="First Paper",
                year=2020,
                authors=[Author(authorId="1", name="John Smith")],
            ),
            Paper(
                paperId="456",
                title="Second Paper",
                year=2021,
                authors=[Author(authorId="2", name="Jane Doe")],
            ),
        ]

        bibtex = export_papers_to_bibtex(papers)

        assert "@" in bibtex
        assert "First Paper" in bibtex
        assert "Second Paper" in bibtex
        assert bibtex.count("@") == 2

    def test_handles_duplicate_cite_keys(self) -> None:
        """Test that duplicate citation keys are handled."""
        papers = [
            Paper(
                paperId="123",
                title="First Paper",
                year=2020,
                authors=[Author(authorId="1", name="John Smith")],
            ),
            Paper(
                paperId="456",
                title="Second Paper",
                year=2020,
                authors=[Author(authorId="1", name="John Smith")],
            ),
        ]

        bibtex = export_papers_to_bibtex(papers)

        # Both papers should have unique keys
        assert "smith2020," in bibtex
        assert "smith2020a," in bibtex

    def test_empty_list_returns_empty_string(self) -> None:
        """Test that empty list returns empty string."""
        bibtex = export_papers_to_bibtex([])

        assert bibtex == ""

    def test_respects_config(self) -> None:
        """Test that export respects configuration."""
        papers = [
            Paper(
                paperId="123",
                title="Test Paper",
                year=2020,
                abstract="Test abstract",
                authors=[Author(authorId="1", name="John Smith")],
            ),
        ]
        config = BibTeXExportConfig(
            fields=BibTeXFieldConfig(include_abstract=True),
            cite_key_format="paper_id",
        )

        bibtex = export_papers_to_bibtex(papers, config)

        assert "@misc{123," in bibtex
        assert "abstract = {Test abstract}" in bibtex
