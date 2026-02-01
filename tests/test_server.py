"""Unit tests for the Semantic Scholar MCP server tools."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from semantic_scholar_mcp import server
from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import (
    Author,
    AuthorWithPapers,
    Paper,
    PaperWithTldr,
)
from semantic_scholar_mcp.tools import (
    get_author_details,
    get_paper_citations,
    get_paper_details,
    get_paper_references,
    get_recommendations,
    get_related_papers,
    search_authors,
    search_papers,
)
from semantic_scholar_mcp.tools._common import set_client_getter

from .conftest import SAMPLE_AUTHOR_RESPONSE, SAMPLE_PAPER_RESPONSE

# Sample response data
SAMPLE_PAPER_WITH_TLDR: dict[str, Any] = {
    **SAMPLE_PAPER_RESPONSE,
    "tldr": {
        "model": "tldr@v2.0.0",
        "text": "This paper introduces the Transformer architecture...",
    },
}

SAMPLE_CITATION_RESPONSE: dict[str, Any] = {
    "data": [
        {"citingPaper": SAMPLE_PAPER_RESPONSE},
        {
            "citingPaper": {
                "paperId": "abc123",
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "abstract": "We introduce a new language representation model...",
                "year": 2019,
                "citationCount": 80000,
                "authors": [{"authorId": "9999", "name": "Jacob Devlin"}],
                "venue": "NAACL",
                "publicationTypes": ["Conference"],
                "openAccessPdf": None,
                "fieldsOfStudy": ["Computer Science"],
            }
        },
    ]
}

SAMPLE_REFERENCE_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "citedPaper": {
                "paperId": "ref123",
                "title": "Neural Machine Translation by Jointly Learning to Align",
                "abstract": "Neural machine translation...",
                "year": 2014,
                "citationCount": 50000,
                "authors": [{"authorId": "7777", "name": "Dzmitry Bahdanau"}],
                "venue": "ICLR",
                "publicationTypes": ["Conference"],
                "openAccessPdf": None,
                "fieldsOfStudy": ["Computer Science"],
            }
        }
    ]
}

SAMPLE_RECOMMENDATION_RESPONSE: dict[str, Any] = {
    "recommendedPapers": [
        SAMPLE_PAPER_RESPONSE,
        {
            "paperId": "rec123",
            "title": "GPT-4 Technical Report",
            "abstract": "We report the development of GPT-4...",
            "year": 2023,
            "citationCount": 5000,
            "authors": [{"authorId": "8888", "name": "OpenAI"}],
            "venue": "ArXiv",
            "publicationTypes": ["Preprint"],
            "openAccessPdf": {"url": "https://arxiv.org/pdf/2303.08774.pdf"},
            "fieldsOfStudy": ["Computer Science"],
        },
    ]
}


@pytest.fixture(autouse=True)
def reset_client() -> None:
    """Reset the shared client instance before each test."""
    server._client = None


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock client for testing."""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.get_with_retry = AsyncMock()
    mock.post_with_retry = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def mock_client_getter(mock_client: MagicMock) -> Generator[None]:
    """Set mock client for all tests."""
    set_client_getter(lambda: mock_client)
    yield


class TestSearchPapers:
    """Tests for the search_papers tool."""

    @pytest.mark.asyncio
    async def test_search_papers_success_with_results(self, mock_client: MagicMock) -> None:
        """Test search_papers returns papers when results are found."""
        mock_client.get_with_retry.return_value = {
            "total": 2,
            "data": [
                SAMPLE_PAPER_RESPONSE,
                {
                    "paperId": "paper2",
                    "title": "Another Paper",
                    "abstract": "Abstract text",
                    "year": 2020,
                    "citationCount": 100,
                    "authors": [{"authorId": "111", "name": "Author Name"}],
                    "venue": "ICML",
                    "publicationTypes": ["Conference"],
                    "openAccessPdf": None,
                    "fieldsOfStudy": ["Computer Science"],
                },
            ],
        }

        result = await search_papers("attention mechanism")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, Paper) for p in result)
        assert result[0].title == "Attention Is All You Need"
        mock_client.get_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_papers_empty_results(self, mock_client: MagicMock) -> None:
        """Test search_papers returns informative message when no results found."""
        mock_client.get_with_retry.return_value = {"total": 0, "data": []}

        result = await search_papers("xyznonexistentquery123")

        assert isinstance(result, str)
        assert "No papers found" in result
        assert "xyznonexistentquery123" in result

    @pytest.mark.asyncio
    async def test_search_papers_with_filters(self, mock_client: MagicMock) -> None:
        """Test search_papers applies filters correctly."""
        mock_client.get_with_retry.return_value = {"total": 1, "data": [SAMPLE_PAPER_RESPONSE]}

        result = await search_papers(
            "transformers",
            year="2020-2024",
            min_citation_count=100,
            fields_of_study=["Computer Science", "Medicine"],
            limit=50,
        )

        assert isinstance(result, list)
        call_args = mock_client.get_with_retry.call_args
        params = call_args[1]["params"]
        assert params["year"] == "2020-2024"
        assert params["minCitationCount"] == 100
        assert "Computer Science" in params["fieldsOfStudy"]
        assert params["limit"] == 50

    @pytest.mark.asyncio
    async def test_search_papers_limit_validation(self, mock_client: MagicMock) -> None:
        """Test search_papers clamps limit to valid range."""
        mock_client.get_with_retry.return_value = {"total": 1, "data": [SAMPLE_PAPER_RESPONSE]}

        # Test limit below minimum
        await search_papers("test", limit=0)
        call_args = mock_client.get_with_retry.call_args
        assert call_args[1]["params"]["limit"] == 1

        # Test limit above maximum
        await search_papers("test", limit=200)
        call_args = mock_client.get_with_retry.call_args
        assert call_args[1]["params"]["limit"] == 100


class TestGetPaperDetails:
    """Tests for the get_paper_details tool."""

    @pytest.mark.asyncio
    async def test_get_paper_details_valid_id(self, mock_client: MagicMock) -> None:
        """Test get_paper_details returns paper for valid ID."""
        mock_client.get_with_retry.return_value = SAMPLE_PAPER_WITH_TLDR

        result = await get_paper_details("649def34f8be52c8b66281af98ae884c09aef38b")

        assert isinstance(result, PaperWithTldr)
        assert result.title == "Attention Is All You Need"
        assert result.tldr is not None
        assert "Transformer" in result.tldr.text

    @pytest.mark.asyncio
    async def test_get_paper_details_invalid_id(self, mock_client: MagicMock) -> None:
        """Test get_paper_details returns error message for invalid ID."""
        mock_client.get_with_retry.side_effect = NotFoundError("Paper not found")

        result = await get_paper_details("nonexistent-paper-id")

        assert isinstance(result, str)
        assert "not found" in result.lower()
        assert "nonexistent-paper-id" in result

    @pytest.mark.asyncio
    async def test_get_paper_details_doi_format(self, mock_client: MagicMock) -> None:
        """Test get_paper_details works with DOI format."""
        mock_client.get_with_retry.return_value = SAMPLE_PAPER_WITH_TLDR

        result = await get_paper_details("DOI:10.18653/v1/N18-3011")

        assert isinstance(result, PaperWithTldr)
        call_args = mock_client.get_with_retry.call_args
        assert "DOI:10.18653/v1/N18-3011" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_paper_details_arxiv_format(self, mock_client: MagicMock) -> None:
        """Test get_paper_details works with ArXiv format."""
        mock_client.get_with_retry.return_value = SAMPLE_PAPER_WITH_TLDR

        result = await get_paper_details("ARXIV:2106.15928")

        assert isinstance(result, PaperWithTldr)
        call_args = mock_client.get_with_retry.call_args
        assert "ARXIV:2106.15928" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_paper_details_without_tldr(self, mock_client: MagicMock) -> None:
        """Test get_paper_details with include_tldr=False."""
        mock_client.get_with_retry.return_value = SAMPLE_PAPER_RESPONSE

        result = await get_paper_details(
            "649def34f8be52c8b66281af98ae884c09aef38b", include_tldr=False
        )

        assert isinstance(result, PaperWithTldr)
        call_args = mock_client.get_with_retry.call_args
        assert "tldr" not in call_args[1]["params"]["fields"]


class TestGetPaperCitations:
    """Tests for the get_paper_citations tool."""

    @pytest.mark.asyncio
    async def test_get_paper_citations_many_citations(self, mock_client: MagicMock) -> None:
        """Test get_paper_citations returns citing papers for well-cited paper."""
        mock_client.get_with_retry.return_value = SAMPLE_CITATION_RESPONSE

        result = await get_paper_citations("649def34f8be52c8b66281af98ae884c09aef38b")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, Paper) for p in result)
        assert result[0].title == "Attention Is All You Need"
        assert result[1].title == "BERT: Pre-training of Deep Bidirectional Transformers"

    @pytest.mark.asyncio
    async def test_get_paper_citations_few_citations(self, mock_client: MagicMock) -> None:
        """Test get_paper_citations with paper having few citations."""
        mock_client.get_with_retry.return_value = {"data": [{"citingPaper": SAMPLE_PAPER_RESPONSE}]}

        result = await get_paper_citations("paper-with-few-citations")

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_paper_citations_zero_citations(self, mock_client: MagicMock) -> None:
        """Test get_paper_citations returns message for paper with no citations."""
        mock_client.get_with_retry.return_value = {"data": []}

        result = await get_paper_citations("new-paper-no-citations")

        assert isinstance(result, str)
        assert "No citations found" in result

    @pytest.mark.asyncio
    async def test_get_paper_citations_not_found(self, mock_client: MagicMock) -> None:
        """Test get_paper_citations handles not found error."""
        mock_client.get_with_retry.side_effect = NotFoundError("Paper not found")

        result = await get_paper_citations("nonexistent-id")

        assert isinstance(result, str)
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_paper_citations_with_year_filter(self, mock_client: MagicMock) -> None:
        """Test get_paper_citations applies year filter."""
        mock_client.get_with_retry.return_value = SAMPLE_CITATION_RESPONSE

        await get_paper_citations(
            "649def34f8be52c8b66281af98ae884c09aef38b",
            year="2020-2024",
        )

        call_args = mock_client.get_with_retry.call_args
        assert call_args[1]["params"]["year"] == "2020-2024"


class TestGetPaperReferences:
    """Tests for the get_paper_references tool."""

    @pytest.mark.asyncio
    async def test_get_paper_references_many_references(self, mock_client: MagicMock) -> None:
        """Test get_paper_references returns referenced papers."""
        mock_client.get_with_retry.return_value = SAMPLE_REFERENCE_RESPONSE

        result = await get_paper_references("649def34f8be52c8b66281af98ae884c09aef38b")

        assert isinstance(result, list)
        assert len(result) == 1
        assert all(isinstance(p, Paper) for p in result)
        assert result[0].title == "Neural Machine Translation by Jointly Learning to Align"

    @pytest.mark.asyncio
    async def test_get_paper_references_few_references(self, mock_client: MagicMock) -> None:
        """Test get_paper_references with paper having few references."""
        mock_client.get_with_retry.return_value = {"data": [{"citedPaper": SAMPLE_PAPER_RESPONSE}]}

        result = await get_paper_references("paper-with-few-references")

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_paper_references_zero_references(self, mock_client: MagicMock) -> None:
        """Test get_paper_references returns message for paper with no references."""
        mock_client.get_with_retry.return_value = {"data": []}

        result = await get_paper_references("paper-no-references")

        assert isinstance(result, str)
        assert "No references found" in result

    @pytest.mark.asyncio
    async def test_get_paper_references_not_found(self, mock_client: MagicMock) -> None:
        """Test get_paper_references handles not found error."""
        mock_client.get_with_retry.side_effect = NotFoundError("Paper not found")

        result = await get_paper_references("nonexistent-id")

        assert isinstance(result, str)
        assert "not found" in result.lower()


class TestSearchAuthors:
    """Tests for the search_authors tool."""

    @pytest.mark.asyncio
    async def test_search_authors_common_name_multiple_results(
        self, mock_client: MagicMock
    ) -> None:
        """Test search_authors returns multiple authors for common names."""
        mock_client.get_with_retry.return_value = {
            "total": 2,
            "data": [
                SAMPLE_AUTHOR_RESPONSE,
                {
                    "authorId": "5678",
                    "name": "John Smith",
                    "affiliations": ["MIT"],
                    "paperCount": 100,
                    "citationCount": 5000,
                    "hIndex": 15,
                },
            ],
        }

        result = await search_authors("Smith")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(a, Author) for a in result)

    @pytest.mark.asyncio
    async def test_search_authors_unique_name(self, mock_client: MagicMock) -> None:
        """Test search_authors returns single author for unique name."""
        mock_client.get_with_retry.return_value = {
            "total": 1,
            "data": [SAMPLE_AUTHOR_RESPONSE],
        }

        result = await search_authors("Ashish Vaswani")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "Ashish Vaswani"

    @pytest.mark.asyncio
    async def test_search_authors_empty_results(self, mock_client: MagicMock) -> None:
        """Test search_authors returns message when no authors found."""
        mock_client.get_with_retry.return_value = {"total": 0, "data": []}

        result = await search_authors("xyznonexistentauthor123")

        assert isinstance(result, str)
        assert "No authors found" in result
        assert "xyznonexistentauthor123" in result


class TestGetAuthorDetails:
    """Tests for the get_author_details tool."""

    @pytest.mark.asyncio
    async def test_get_author_details_valid_id(self, mock_client: MagicMock) -> None:
        """Test get_author_details returns author for valid ID."""
        mock_client.get_with_retry.side_effect = [
            SAMPLE_AUTHOR_RESPONSE,
            {"data": [SAMPLE_PAPER_RESPONSE]},
        ]

        result = await get_author_details("1234")

        assert isinstance(result, AuthorWithPapers)
        assert result.name == "Ashish Vaswani"
        assert result.papers is not None
        assert len(result.papers) == 1

    @pytest.mark.asyncio
    async def test_get_author_details_invalid_id(self, mock_client: MagicMock) -> None:
        """Test get_author_details returns error message for invalid ID."""
        mock_client.get_with_retry.side_effect = NotFoundError("Author not found")

        result = await get_author_details("nonexistent-author-id")

        assert isinstance(result, str)
        assert "not found" in result.lower()
        assert "nonexistent-author-id" in result

    @pytest.mark.asyncio
    async def test_get_author_details_without_papers(self, mock_client: MagicMock) -> None:
        """Test get_author_details with include_papers=False."""
        mock_client.get_with_retry.return_value = SAMPLE_AUTHOR_RESPONSE

        result = await get_author_details("1234", include_papers=False)

        assert isinstance(result, AuthorWithPapers)
        assert result.papers is None
        # Only one call (author details, no papers)
        assert mock_client.get_with_retry.call_count == 1

    @pytest.mark.asyncio
    async def test_get_author_details_with_papers_limit(self, mock_client: MagicMock) -> None:
        """Test get_author_details respects papers_limit."""
        mock_client.get_with_retry.side_effect = [
            SAMPLE_AUTHOR_RESPONSE,
            {"data": [SAMPLE_PAPER_RESPONSE] * 5},
        ]

        await get_author_details("1234", papers_limit=20)

        # Check the papers call used the limit
        papers_call = mock_client.get_with_retry.call_args_list[1]
        assert papers_call[1]["params"]["limit"] == 20


class TestGetRecommendations:
    """Tests for the get_recommendations tool."""

    @pytest.mark.asyncio
    async def test_get_recommendations_popular_paper(self, mock_client: MagicMock) -> None:
        """Test get_recommendations returns papers for popular paper."""
        mock_client.get_with_retry.return_value = SAMPLE_RECOMMENDATION_RESPONSE

        result = await get_recommendations("649def34f8be52c8b66281af98ae884c09aef38b")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, Paper) for p in result)

    @pytest.mark.asyncio
    async def test_get_recommendations_niche_paper(self, mock_client: MagicMock) -> None:
        """Test get_recommendations for niche paper with fewer recommendations."""
        mock_client.get_with_retry.return_value = {"recommendedPapers": [SAMPLE_PAPER_RESPONSE]}

        result = await get_recommendations("niche-paper-id")

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_recommendations_no_recommendations(self, mock_client: MagicMock) -> None:
        """Test get_recommendations returns message when no recommendations."""
        mock_client.get_with_retry.return_value = {"recommendedPapers": []}

        result = await get_recommendations("paper-no-recs")

        assert isinstance(result, str)
        assert "No recommendations found" in result

    @pytest.mark.asyncio
    async def test_get_recommendations_not_found(self, mock_client: MagicMock) -> None:
        """Test get_recommendations handles not found error."""
        mock_client.get_with_retry.side_effect = NotFoundError("Paper not found")

        result = await get_recommendations("nonexistent-id")

        assert isinstance(result, str)
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_recommendations_with_pool_parameter(self, mock_client: MagicMock) -> None:
        """Test get_recommendations uses pool parameter correctly."""
        mock_client.get_with_retry.return_value = SAMPLE_RECOMMENDATION_RESPONSE

        await get_recommendations("paper-id", from_pool="all-cs")

        call_args = mock_client.get_with_retry.call_args
        assert call_args[1]["params"]["from"] == "all-cs"

    @pytest.mark.asyncio
    async def test_get_recommendations_invalid_pool_defaults_to_recent(
        self, mock_client: MagicMock
    ) -> None:
        """Test get_recommendations defaults to 'recent' for invalid pool."""
        mock_client.get_with_retry.return_value = SAMPLE_RECOMMENDATION_RESPONSE

        await get_recommendations("paper-id", from_pool="invalid-pool")

        call_args = mock_client.get_with_retry.call_args
        assert call_args[1]["params"]["from"] == "recent"


class TestGetRelatedPapers:
    """Tests for the get_related_papers tool."""

    @pytest.mark.asyncio
    async def test_get_related_papers_single_positive(self, mock_client: MagicMock) -> None:
        """Test get_related_papers with single positive paper."""
        mock_client.post_with_retry.return_value = SAMPLE_RECOMMENDATION_RESPONSE

        result = await get_related_papers(["649def34f8be52c8b66281af98ae884c09aef38b"])

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, Paper) for p in result)

    @pytest.mark.asyncio
    async def test_get_related_papers_multiple_positives(self, mock_client: MagicMock) -> None:
        """Test get_related_papers with multiple positive papers."""
        mock_client.post_with_retry.return_value = SAMPLE_RECOMMENDATION_RESPONSE

        result = await get_related_papers(["paper1", "paper2", "paper3"])

        assert isinstance(result, list)
        call_args = mock_client.post_with_retry.call_args
        body = call_args[1]["json_data"]
        assert len(body["positivePaperIds"]) == 3

    @pytest.mark.asyncio
    async def test_get_related_papers_with_negatives(self, mock_client: MagicMock) -> None:
        """Test get_related_papers with positive and negative papers."""
        mock_client.post_with_retry.return_value = SAMPLE_RECOMMENDATION_RESPONSE

        result = await get_related_papers(
            positive_paper_ids=["paper1", "paper2"],
            negative_paper_ids=["paper3", "paper4"],
        )

        assert isinstance(result, list)
        call_args = mock_client.post_with_retry.call_args
        body = call_args[1]["json_data"]
        assert body["positivePaperIds"] == ["paper1", "paper2"]
        assert body["negativePaperIds"] == ["paper3", "paper4"]

    @pytest.mark.asyncio
    async def test_get_related_papers_no_positive_papers(self, mock_client: MagicMock) -> None:
        """Test get_related_papers returns error when no positive papers."""
        result = await get_related_papers([])

        assert isinstance(result, str)
        assert "At least one positive paper ID is required" in result
        mock_client.post_with_retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_related_papers_no_recommendations(self, mock_client: MagicMock) -> None:
        """Test get_related_papers returns message when no recommendations."""
        mock_client.post_with_retry.return_value = {"recommendedPapers": []}

        result = await get_related_papers(["paper1"])

        assert isinstance(result, str)
        assert "No recommendations found" in result

    @pytest.mark.asyncio
    async def test_get_related_papers_with_limit(self, mock_client: MagicMock) -> None:
        """Test get_related_papers respects limit parameter."""
        mock_client.post_with_retry.return_value = SAMPLE_RECOMMENDATION_RESPONSE

        await get_related_papers(["paper1"], limit=25)

        call_args = mock_client.post_with_retry.call_args
        assert call_args[1]["params"]["limit"] == 25
