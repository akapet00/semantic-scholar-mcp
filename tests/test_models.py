"""Tests for Pydantic model validation in Semantic Scholar MCP server."""

import pytest
from pydantic import ValidationError

from semantic_scholar_mcp.models import (
    Author,
    AuthorConsolidationResult,
    AuthorExternalIds,
    AuthorGroup,
    AuthorPapersResult,
    AuthorSearchResult,
    AuthorTopPapers,
    AuthorWithPapers,
    CitingPaper,
    Journal,
    OpenAccessPdf,
    Paper,
    PaperExternalIds,
    PaperWithTldr,
    PublicationVenue,
    RecommendationResult,
    ReferencePaper,
    SearchResult,
    Tldr,
)


class TestPaperModel:
    """Tests for the Paper model."""

    def test_paper_with_all_fields(self) -> None:
        """Test Paper model with all fields populated."""
        paper = Paper(
            paperId="abc123",
            title="Test Paper",
            abstract="This is a test abstract.",
            year=2023,
            citationCount=100,
            authors=[Author(authorId="auth1", name="John Doe")],
            venue="NeurIPS",
            publicationTypes=["Conference"],
            openAccessPdf=OpenAccessPdf(url="https://example.com/paper.pdf"),
            fieldsOfStudy=["Computer Science", "AI"],
            journal=Journal(name="Test Journal", volume="1", pages="1-10"),
            externalIds=PaperExternalIds(DOI="10.1234/test"),
            publicationDate="2023-01-15",
            publicationVenue=PublicationVenue(name="NeurIPS", type="conference"),
        )
        assert paper.paperId == "abc123"
        assert paper.title == "Test Paper"
        assert paper.abstract == "This is a test abstract."
        assert paper.year == 2023
        assert paper.citationCount == 100
        assert len(paper.authors) == 1
        assert paper.authors[0].name == "John Doe"
        assert paper.venue == "NeurIPS"
        assert paper.publicationTypes == ["Conference"]
        assert paper.openAccessPdf.url == "https://example.com/paper.pdf"
        assert paper.fieldsOfStudy == ["Computer Science", "AI"]
        assert paper.journal.name == "Test Journal"
        assert paper.externalIds.DOI == "10.1234/test"
        assert paper.publicationDate == "2023-01-15"
        assert paper.publicationVenue.name == "NeurIPS"

    def test_paper_with_minimal_fields(self) -> None:
        """Test Paper model with no fields (all optional)."""
        paper = Paper()
        assert paper.paperId is None
        assert paper.title is None
        assert paper.abstract is None
        assert paper.year is None
        assert paper.citationCount is None
        assert paper.authors is None
        assert paper.venue is None
        assert paper.publicationTypes is None
        assert paper.openAccessPdf is None
        assert paper.fieldsOfStudy is None
        assert paper.journal is None
        assert paper.externalIds is None
        assert paper.publicationDate is None
        assert paper.publicationVenue is None

    def test_paper_with_only_required_nested_models(self) -> None:
        """Test Paper with nested models that have their own defaults."""
        paper = Paper(
            paperId="test123",
            authors=[Author(), Author()],
            openAccessPdf=OpenAccessPdf(),
            journal=Journal(),
            externalIds=PaperExternalIds(),
            publicationVenue=PublicationVenue(),
        )
        assert paper.paperId == "test123"
        assert len(paper.authors) == 2
        assert paper.authors[0].authorId is None
        assert paper.openAccessPdf.url is None
        assert paper.journal.name is None
        assert paper.externalIds.DOI is None
        assert paper.publicationVenue.name is None

    def test_paper_serialization_model_dump(self) -> None:
        """Test Paper serialization using model_dump."""
        paper = Paper(
            paperId="abc123",
            title="Test Paper",
            year=2023,
            citationCount=50,
        )
        data = paper.model_dump()
        assert isinstance(data, dict)
        assert data["paperId"] == "abc123"
        assert data["title"] == "Test Paper"
        assert data["year"] == 2023
        assert data["citationCount"] == 50
        assert data["abstract"] is None
        assert data["authors"] is None

    def test_paper_serialization_exclude_none(self) -> None:
        """Test Paper serialization excluding None values."""
        paper = Paper(paperId="abc123", title="Test Paper")
        data = paper.model_dump(exclude_none=True)
        assert "paperId" in data
        assert "title" in data
        assert "abstract" not in data
        assert "year" not in data

    def test_paper_deserialization_model_validate(self) -> None:
        """Test Paper deserialization using model_validate."""
        data = {
            "paperId": "abc123",
            "title": "Test Paper",
            "year": 2023,
            "authors": [{"authorId": "auth1", "name": "Jane Doe"}],
        }
        paper = Paper.model_validate(data)
        assert paper.paperId == "abc123"
        assert paper.title == "Test Paper"
        assert paper.year == 2023
        assert len(paper.authors) == 1
        assert paper.authors[0].name == "Jane Doe"

    def test_paper_deserialization_with_nested_objects(self) -> None:
        """Test Paper deserialization with all nested objects."""
        data = {
            "paperId": "abc123",
            "title": "Test Paper",
            "openAccessPdf": {"url": "https://example.com/paper.pdf", "status": "GREEN"},
            "journal": {"name": "Nature", "volume": "100", "pages": "1-15"},
            "externalIds": {"DOI": "10.1234/test", "ArXiv": "2301.00001"},
            "publicationVenue": {"name": "Nature", "type": "journal", "issn": "1234-5678"},
        }
        paper = Paper.model_validate(data)
        assert paper.openAccessPdf.url == "https://example.com/paper.pdf"
        assert paper.openAccessPdf.status == "GREEN"
        assert paper.journal.name == "Nature"
        assert paper.journal.volume == "100"
        assert paper.externalIds.DOI == "10.1234/test"
        assert paper.externalIds.ArXiv == "2301.00001"
        assert paper.publicationVenue.issn == "1234-5678"

    def test_paper_publication_venue_string_coercion(self) -> None:
        """Test that a plain venue ID string is coerced into a PublicationVenue.

        The Recommendations API sometimes returns publicationVenue as a bare
        UUID string instead of the full venue object.
        """
        data = {
            "paperId": "abc123",
            "publicationVenue": "c7f73dd6-8431-403d-8268-80d666abe1bc",
        }
        paper = Paper.model_validate(data)
        assert isinstance(paper.publicationVenue, PublicationVenue)
        assert paper.publicationVenue.id == "c7f73dd6-8431-403d-8268-80d666abe1bc"
        assert paper.publicationVenue.name is None

    def test_paper_publication_venue_none_still_works(self) -> None:
        """Test that publicationVenue=None is unaffected by the validator."""
        paper = Paper(paperId="abc123", publicationVenue=None)
        assert paper.publicationVenue is None

    def test_paper_publication_venue_dict_still_works(self) -> None:
        """Test that publicationVenue as a dict is unaffected by the validator."""
        data = {
            "paperId": "abc123",
            "publicationVenue": {"id": "venue-id", "name": "NeurIPS", "type": "conference"},
        }
        paper = Paper.model_validate(data)
        assert paper.publicationVenue.name == "NeurIPS"
        assert paper.publicationVenue.type == "conference"

    def test_recommendation_result_with_string_venues(self) -> None:
        """Test RecommendationResult handles papers with string publicationVenue."""
        data = {
            "recommendedPapers": [
                {
                    "paperId": "p1",
                    "title": "Paper 1",
                    "publicationVenue": "c7f73dd6-8431-403d-8268-80d666abe1bc",
                },
                {
                    "paperId": "p2",
                    "title": "Paper 2",
                    "publicationVenue": None,
                },
                {
                    "paperId": "p3",
                    "title": "Paper 3",
                    "publicationVenue": {"id": "venue-id", "name": "ICML"},
                },
            ]
        }
        result = RecommendationResult.model_validate(data)
        assert len(result.recommendedPapers) == 3
        assert result.recommendedPapers[0].publicationVenue.id == "c7f73dd6-8431-403d-8268-80d666abe1bc"
        assert result.recommendedPapers[1].publicationVenue is None
        assert result.recommendedPapers[2].publicationVenue.name == "ICML"


class TestAuthorModel:
    """Tests for the Author model."""

    def test_author_with_all_fields(self) -> None:
        """Test Author model with all fields populated."""
        author = Author(
            authorId="auth123",
            name="John Doe",
            affiliations=["MIT", "Stanford"],
            paperCount=100,
            citationCount=5000,
            hIndex=30,
            aliases=["J. Doe", "John D."],
            homepage="https://johndoe.com",
            externalIds=AuthorExternalIds(ORCID="0000-0001-2345-6789", DBLP="d/JohnDoe"),
        )
        assert author.authorId == "auth123"
        assert author.name == "John Doe"
        assert author.affiliations == ["MIT", "Stanford"]
        assert author.paperCount == 100
        assert author.citationCount == 5000
        assert author.hIndex == 30
        assert author.aliases == ["J. Doe", "John D."]
        assert author.homepage == "https://johndoe.com"
        assert author.externalIds.ORCID == "0000-0001-2345-6789"
        assert author.externalIds.DBLP == "d/JohnDoe"

    def test_author_with_minimal_fields(self) -> None:
        """Test Author model with no fields (all optional)."""
        author = Author()
        assert author.authorId is None
        assert author.name is None
        assert author.affiliations is None
        assert author.paperCount is None
        assert author.citationCount is None
        assert author.hIndex is None
        assert author.aliases is None
        assert author.homepage is None
        assert author.externalIds is None

    def test_author_serialization_model_dump(self) -> None:
        """Test Author serialization using model_dump."""
        author = Author(
            authorId="auth123",
            name="John Doe",
            paperCount=50,
            citationCount=1000,
        )
        data = author.model_dump()
        assert isinstance(data, dict)
        assert data["authorId"] == "auth123"
        assert data["name"] == "John Doe"
        assert data["paperCount"] == 50
        assert data["citationCount"] == 1000
        assert data["affiliations"] is None
        assert data["hIndex"] is None

    def test_author_deserialization_model_validate(self) -> None:
        """Test Author deserialization using model_validate."""
        data = {
            "authorId": "auth123",
            "name": "Jane Doe",
            "affiliations": ["Google"],
            "paperCount": 75,
            "citationCount": 3000,
            "hIndex": 20,
        }
        author = Author.model_validate(data)
        assert author.authorId == "auth123"
        assert author.name == "Jane Doe"
        assert author.affiliations == ["Google"]
        assert author.paperCount == 75
        assert author.citationCount == 3000
        assert author.hIndex == 20

    def test_author_with_external_ids(self) -> None:
        """Test Author with external IDs nested model."""
        author = Author(
            authorId="auth123",
            externalIds=AuthorExternalIds(ORCID="0000-0002-1234-5678"),
        )
        assert author.externalIds.ORCID == "0000-0002-1234-5678"
        assert author.externalIds.DBLP is None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string_values(self) -> None:
        """Test models accept empty strings."""
        paper = Paper(paperId="", title="", abstract="", venue="")
        assert paper.paperId == ""
        assert paper.title == ""
        assert paper.abstract == ""
        assert paper.venue == ""

        author = Author(authorId="", name="", homepage="")
        assert author.authorId == ""
        assert author.name == ""
        assert author.homepage == ""

    def test_none_values_explicit(self) -> None:
        """Test models accept explicit None values."""
        paper = Paper(
            paperId=None,
            title=None,
            year=None,
            citationCount=None,
        )
        assert paper.paperId is None
        assert paper.title is None
        assert paper.year is None
        assert paper.citationCount is None

    def test_missing_optional_fields_in_dict(self) -> None:
        """Test model_validate handles missing optional fields."""
        data = {"paperId": "abc123"}
        paper = Paper.model_validate(data)
        assert paper.paperId == "abc123"
        assert paper.title is None
        assert paper.year is None

    def test_empty_list_values(self) -> None:
        """Test models accept empty lists."""
        paper = Paper(
            authors=[],
            publicationTypes=[],
            fieldsOfStudy=[],
        )
        assert paper.authors == []
        assert paper.publicationTypes == []
        assert paper.fieldsOfStudy == []

        author = Author(affiliations=[], aliases=[])
        assert author.affiliations == []
        assert author.aliases == []

    def test_zero_integer_values(self) -> None:
        """Test models accept zero for integer fields."""
        paper = Paper(year=0, citationCount=0)
        assert paper.year == 0
        assert paper.citationCount == 0

        author = Author(paperCount=0, citationCount=0, hIndex=0)
        assert author.paperCount == 0
        assert author.citationCount == 0
        assert author.hIndex == 0

    def test_negative_integer_values(self) -> None:
        """Test models accept negative integers (no validation constraint)."""
        paper = Paper(year=-1, citationCount=-100)
        assert paper.year == -1
        assert paper.citationCount == -100

    def test_large_integer_values(self) -> None:
        """Test models accept large integers."""
        paper = Paper(citationCount=999999999)
        assert paper.citationCount == 999999999

        author = Author(citationCount=999999999, hIndex=999)
        assert author.citationCount == 999999999
        assert author.hIndex == 999

    def test_special_characters_in_strings(self) -> None:
        """Test models handle special characters in strings."""
        paper = Paper(
            title="Test with special chars: <>&\"'",
            abstract="Unicode: \u00e9\u00e8\u00ea \u4e2d\u6587 \U0001f600",
        )
        assert "<>&\"'" in paper.title
        assert "\u00e9" in paper.abstract
        assert "\U0001f600" in paper.abstract

    def test_author_external_ids_dblp_list(self) -> None:
        """Test AuthorExternalIds accepts list for DBLP field."""
        ext_ids = AuthorExternalIds(DBLP=["d/JohnDoe", "d/JDoe"])
        assert ext_ids.DBLP == ["d/JohnDoe", "d/JDoe"]

    def test_author_external_ids_dblp_string(self) -> None:
        """Test AuthorExternalIds accepts string for DBLP field."""
        ext_ids = AuthorExternalIds(DBLP="d/JohnDoe")
        assert ext_ids.DBLP == "d/JohnDoe"


class TestNestedModels:
    """Tests for nested model structures."""

    def test_paper_external_ids_all_fields(self) -> None:
        """Test PaperExternalIds with all fields."""
        ext_ids = PaperExternalIds(
            DOI="10.1234/test",
            ArXiv="2301.00001",
            MAG="12345",
            ACL="P21-1001",
            PubMed="34567890",
            PubMedCentral="PMC1234567",
            DBLP="conf/neurips/Test2023",
            CorpusId=123456789,
        )
        assert ext_ids.DOI == "10.1234/test"
        assert ext_ids.ArXiv == "2301.00001"
        assert ext_ids.MAG == "12345"
        assert ext_ids.ACL == "P21-1001"
        assert ext_ids.PubMed == "34567890"
        assert ext_ids.PubMedCentral == "PMC1234567"
        assert ext_ids.DBLP == "conf/neurips/Test2023"
        assert ext_ids.CorpusId == 123456789

    def test_journal_model(self) -> None:
        """Test Journal model."""
        journal = Journal(name="Nature", volume="100", pages="1-15")
        assert journal.name == "Nature"
        assert journal.volume == "100"
        assert journal.pages == "1-15"

    def test_publication_venue_model(self) -> None:
        """Test PublicationVenue model."""
        venue = PublicationVenue(
            id="venue123",
            name="NeurIPS",
            type="conference",
            alternate_names=["Neural Information Processing Systems", "NIPS"],
            issn="1234-5678",
            url="https://neurips.cc",
        )
        assert venue.id == "venue123"
        assert venue.name == "NeurIPS"
        assert venue.type == "conference"
        assert len(venue.alternate_names) == 2
        assert venue.issn == "1234-5678"
        assert venue.url == "https://neurips.cc"

    def test_open_access_pdf_model(self) -> None:
        """Test OpenAccessPdf model."""
        pdf = OpenAccessPdf(url="https://arxiv.org/pdf/2301.00001.pdf", status="GREEN")
        assert pdf.url == "https://arxiv.org/pdf/2301.00001.pdf"
        assert pdf.status == "GREEN"

    def test_tldr_model(self) -> None:
        """Test Tldr model."""
        tldr = Tldr(model="tldr@v2.0.0", text="This paper presents a novel approach...")
        assert tldr.model == "tldr@v2.0.0"
        assert tldr.text == "This paper presents a novel approach..."

    def test_paper_with_tldr(self) -> None:
        """Test PaperWithTldr model."""
        paper = PaperWithTldr(
            paperId="abc123",
            title="Test Paper",
            tldr=Tldr(text="A summary of the paper."),
        )
        assert paper.paperId == "abc123"
        assert paper.title == "Test Paper"
        assert paper.tldr.text == "A summary of the paper."


class TestContainerModels:
    """Tests for container/wrapper models."""

    def test_citing_paper_model(self) -> None:
        """Test CitingPaper model requires citingPaper field."""
        citing = CitingPaper(citingPaper=Paper(paperId="cite123", title="Citing Paper"))
        assert citing.citingPaper.paperId == "cite123"

    def test_citing_paper_missing_required_field(self) -> None:
        """Test CitingPaper raises error when citingPaper is missing."""
        with pytest.raises(ValidationError):
            CitingPaper()

    def test_reference_paper_model(self) -> None:
        """Test ReferencePaper model requires citedPaper field."""
        ref = ReferencePaper(citedPaper=Paper(paperId="ref123", title="Reference Paper"))
        assert ref.citedPaper.paperId == "ref123"

    def test_reference_paper_missing_required_field(self) -> None:
        """Test ReferencePaper raises error when citedPaper is missing."""
        with pytest.raises(ValidationError):
            ReferencePaper()

    def test_search_result_defaults(self) -> None:
        """Test SearchResult model has correct defaults."""
        result = SearchResult()
        assert result.total == 0
        assert result.offset == 0
        assert result.next is None
        assert result.data == []

    def test_search_result_with_papers(self) -> None:
        """Test SearchResult with paper data."""
        result = SearchResult(
            total=100,
            offset=10,
            next=20,
            data=[Paper(paperId="p1"), Paper(paperId="p2")],
        )
        assert result.total == 100
        assert result.offset == 10
        assert result.next == 20
        assert len(result.data) == 2

    def test_author_search_result_defaults(self) -> None:
        """Test AuthorSearchResult model has correct defaults."""
        result = AuthorSearchResult()
        assert result.total == 0
        assert result.offset == 0
        assert result.next is None
        assert result.data == []

    def test_author_search_result_with_authors(self) -> None:
        """Test AuthorSearchResult with author data."""
        result = AuthorSearchResult(
            total=50,
            data=[Author(authorId="a1"), Author(authorId="a2")],
        )
        assert result.total == 50
        assert len(result.data) == 2

    def test_recommendation_result_defaults(self) -> None:
        """Test RecommendationResult model has correct defaults."""
        result = RecommendationResult()
        assert result.recommendedPapers == []

    def test_recommendation_result_with_papers(self) -> None:
        """Test RecommendationResult with paper data."""
        result = RecommendationResult(
            recommendedPapers=[Paper(paperId="rec1"), Paper(paperId="rec2")],
        )
        assert len(result.recommendedPapers) == 2

    def test_author_papers_result_defaults(self) -> None:
        """Test AuthorPapersResult model has correct defaults."""
        result = AuthorPapersResult()
        assert result.data == []

    def test_author_papers_result_with_papers(self) -> None:
        """Test AuthorPapersResult with paper data."""
        result = AuthorPapersResult(data=[Paper(paperId="p1")])
        assert len(result.data) == 1


class TestAuthorExtendedModels:
    """Tests for extended author-related models."""

    def test_author_with_papers_model(self) -> None:
        """Test AuthorWithPapers model."""
        author = AuthorWithPapers(
            authorId="auth123",
            name="John Doe",
            affiliations=["MIT"],
            paperCount=50,
            citationCount=5000,
            hIndex=20,
            papers=[Paper(paperId="p1"), Paper(paperId="p2")],
        )
        assert author.authorId == "auth123"
        assert author.name == "John Doe"
        assert len(author.papers) == 2

    def test_author_group_model(self) -> None:
        """Test AuthorGroup model requires all fields."""
        group = AuthorGroup(
            primary_author=Author(authorId="primary", name="John Doe"),
            candidates=[Author(authorId="candidate1")],
            match_reasons=["same_orcid"],
        )
        assert group.primary_author.authorId == "primary"
        assert len(group.candidates) == 1
        assert group.match_reasons == ["same_orcid"]

    def test_author_group_missing_required_field(self) -> None:
        """Test AuthorGroup raises error when required fields are missing."""
        with pytest.raises(ValidationError):
            AuthorGroup(primary_author=Author())

    def test_author_consolidation_result_model(self) -> None:
        """Test AuthorConsolidationResult model."""
        result = AuthorConsolidationResult(
            merged_author=Author(authorId="merged", name="John Doe"),
            source_authors=[Author(authorId="a1"), Author(authorId="a2")],
            match_type="orcid",
            confidence=0.95,
            is_preview=True,
            notes=["h-index cannot be computed for merged profiles"],
        )
        assert result.merged_author.authorId == "merged"
        assert len(result.source_authors) == 2
        assert result.match_type == "orcid"
        assert result.confidence == 0.95
        assert result.is_preview is True
        assert len(result.notes) == 1

    def test_author_consolidation_result_defaults(self) -> None:
        """Test AuthorConsolidationResult default values."""
        result = AuthorConsolidationResult(
            merged_author=Author(),
            source_authors=[],
            match_type="user_confirmed",
        )
        assert result.confidence is None
        assert result.is_preview is True
        assert result.notes is None

    def test_author_top_papers_model(self) -> None:
        """Test AuthorTopPapers model."""
        result = AuthorTopPapers(
            author_id="auth123",
            author_name="John Doe",
            total_papers=100,
            total_citations=50000,
            papers_fetched=10,
            top_papers=[Paper(paperId="p1", citationCount=5000)],
        )
        assert result.author_id == "auth123"
        assert result.author_name == "John Doe"
        assert result.total_papers == 100
        assert result.total_citations == 50000
        assert result.papers_fetched == 10
        assert len(result.top_papers) == 1

    def test_author_top_papers_required_field(self) -> None:
        """Test AuthorTopPapers requires author_id."""
        with pytest.raises(ValidationError):
            AuthorTopPapers()

    def test_author_top_papers_defaults(self) -> None:
        """Test AuthorTopPapers default values."""
        result = AuthorTopPapers(author_id="auth123")
        assert result.author_name is None
        assert result.total_papers is None
        assert result.total_citations is None
        assert result.papers_fetched == 0
        assert result.top_papers == []


class TestModelSerialization:
    """Tests for model serialization and round-trip."""

    def test_paper_round_trip(self) -> None:
        """Test Paper can be serialized and deserialized."""
        original = Paper(
            paperId="abc123",
            title="Test Paper",
            year=2023,
            authors=[Author(authorId="auth1", name="John Doe")],
        )
        data = original.model_dump()
        restored = Paper.model_validate(data)
        assert restored.paperId == original.paperId
        assert restored.title == original.title
        assert restored.year == original.year
        assert restored.authors[0].name == original.authors[0].name

    def test_author_round_trip(self) -> None:
        """Test Author can be serialized and deserialized."""
        original = Author(
            authorId="auth123",
            name="Jane Doe",
            affiliations=["MIT", "Stanford"],
            externalIds=AuthorExternalIds(ORCID="0000-0001-2345-6789"),
        )
        data = original.model_dump()
        restored = Author.model_validate(data)
        assert restored.authorId == original.authorId
        assert restored.name == original.name
        assert restored.affiliations == original.affiliations
        assert restored.externalIds.ORCID == original.externalIds.ORCID

    def test_complex_nested_round_trip(self) -> None:
        """Test complex nested model can be serialized and deserialized."""
        original = PaperWithTldr(
            paperId="abc123",
            title="Complex Paper",
            authors=[
                Author(
                    authorId="auth1",
                    name="John Doe",
                    externalIds=AuthorExternalIds(ORCID="0000-0001-2345-6789"),
                ),
            ],
            openAccessPdf=OpenAccessPdf(url="https://example.com/paper.pdf", status="GREEN"),
            journal=Journal(name="Nature", volume="100", pages="1-15"),
            externalIds=PaperExternalIds(DOI="10.1234/test", ArXiv="2301.00001"),
            publicationVenue=PublicationVenue(
                name="Nature",
                type="journal",
                alternate_names=["Nature Journal"],
            ),
            tldr=Tldr(model="tldr@v2.0.0", text="This paper presents..."),
        )
        data = original.model_dump()
        restored = PaperWithTldr.model_validate(data)
        assert restored.paperId == original.paperId
        assert restored.authors[0].externalIds.ORCID == original.authors[0].externalIds.ORCID
        assert restored.openAccessPdf.status == original.openAccessPdf.status
        assert restored.journal.name == original.journal.name
        assert restored.externalIds.DOI == original.externalIds.DOI
        assert (
            restored.publicationVenue.alternate_names == original.publicationVenue.alternate_names
        )
        assert restored.tldr.text == original.tldr.text

    def test_model_dump_by_alias(self) -> None:
        """Test model_dump preserves field names (no aliases defined)."""
        paper = Paper(paperId="abc123", citationCount=100)
        data = paper.model_dump(by_alias=True)
        assert "paperId" in data
        assert "citationCount" in data

    def test_model_dump_json_compatible(self) -> None:
        """Test model_dump produces JSON-compatible output."""
        import json

        paper = Paper(
            paperId="abc123",
            title="Test",
            authors=[Author(authorId="auth1")],
        )
        data = paper.model_dump()
        json_str = json.dumps(data)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["paperId"] == "abc123"
