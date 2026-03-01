"""Unit tests for get_author_top_papers functionality."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import AuthorTopPapers
from semantic_scholar_mcp.tools import get_author_top_papers
from semantic_scholar_mcp.tools._common import set_client_getter


class TestGetAuthorTopPapers:
    """Tests for get_author_top_papers tool."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        mock = MagicMock()
        mock.get_with_retry = AsyncMock()
        return mock

    @pytest.fixture(autouse=True)
    def setup_client(self, mock_client: MagicMock) -> Generator[None]:
        """Set mock client for all tests."""
        set_client_getter(lambda: mock_client)
        yield

    @pytest.fixture
    def mock_tracker(self) -> Generator[MagicMock]:
        """Mock the paper tracker."""
        with patch("semantic_scholar_mcp.tools.authors.get_tracker") as mock:
            tracker = MagicMock()
            mock.return_value = tracker
            yield tracker

    def _make_author_response(
        self,
        author_id: str = "1741101",
        name: str = "Geoffrey Hinton",
        paper_count: int = 500,
        citation_count: int = 500000,
    ) -> dict[str, Any]:
        """Create a mock author response."""
        return {
            "authorId": author_id,
            "name": name,
            "paperCount": paper_count,
            "citationCount": citation_count,
            "hIndex": 150,
        }

    def _make_paper(
        self,
        paper_id: str,
        title: str,
        citation_count: int,
        year: int = 2020,
    ) -> dict[str, Any]:
        """Create a mock paper response."""
        return {
            "paperId": paper_id,
            "title": title,
            "citationCount": citation_count,
            "year": year,
            "authors": [{"authorId": "1741101", "name": "Geoffrey Hinton"}],
        }

    def _make_papers_response(self, papers: list[dict[str, Any]]) -> dict[str, Any]:
        """Create a mock papers response."""
        return {"data": papers}

    @pytest.mark.asyncio
    async def test_single_batch_sorting(
        self, mock_client: MagicMock, mock_tracker: MagicMock
    ) -> None:
        """Test that papers are sorted by citation count when fetched in a single batch."""
        # Papers returned in arbitrary order (as API would return)
        papers = [
            self._make_paper("p1", "Paper 1", citation_count=100),
            self._make_paper("p2", "Paper 2", citation_count=500),  # Highest
            self._make_paper("p3", "Paper 3", citation_count=50),
            self._make_paper("p4", "Paper 4", citation_count=300),
            self._make_paper("p5", "Paper 5", citation_count=200),
        ]

        mock_client.get_with_retry.side_effect = [
            self._make_author_response(),
            self._make_papers_response(papers),
        ]

        result = await get_author_top_papers("1741101", top_n=3)

        assert isinstance(result, AuthorTopPapers)
        assert len(result.top_papers) == 3

        # Verify papers are sorted by citation count (highest first)
        assert result.top_papers[0].paperId == "p2"  # 500 citations
        assert result.top_papers[0].citationCount == 500
        assert result.top_papers[1].paperId == "p4"  # 300 citations
        assert result.top_papers[1].citationCount == 300
        assert result.top_papers[2].paperId == "p5"  # 200 citations
        assert result.top_papers[2].citationCount == 200

    @pytest.mark.asyncio
    async def test_pagination_multiple_batches(
        self, mock_client: MagicMock, mock_tracker: MagicMock
    ) -> None:
        """Test pagination when author has more papers than batch size."""
        # First batch: 1000 papers (simulated by returning exactly batch_size)
        # Create papers with varying citation counts spread across batches
        batch1_papers = [
            self._make_paper(f"batch1_p{i}", f"Batch 1 Paper {i}", citation_count=100 + i)
            for i in range(1000)
        ]
        # Add one high-citation paper in batch 1
        batch1_papers[0] = self._make_paper("top1", "Top Paper 1", citation_count=10000)

        # Second batch: 500 papers (less than batch_size, indicates last page)
        batch2_papers = [
            self._make_paper(f"batch2_p{i}", f"Batch 2 Paper {i}", citation_count=50 + i)
            for i in range(500)
        ]
        # Add high-citation papers in batch 2
        batch2_papers[0] = self._make_paper("top2", "Top Paper 2", citation_count=8000)
        batch2_papers[1] = self._make_paper("top3", "Top Paper 3", citation_count=5000)

        mock_client.get_with_retry.side_effect = [
            self._make_author_response(paper_count=1500),
            self._make_papers_response(batch1_papers),  # First page
            self._make_papers_response(batch2_papers),  # Second page (last)
        ]

        result = await get_author_top_papers("1741101", top_n=5)

        assert isinstance(result, AuthorTopPapers)
        assert result.papers_fetched == 1500  # Total from both batches

        # Verify top papers are sorted correctly across both batches
        assert len(result.top_papers) == 5
        assert result.top_papers[0].paperId == "top1"  # 10000 citations (batch 1)
        assert result.top_papers[0].citationCount == 10000
        assert result.top_papers[1].paperId == "top2"  # 8000 citations (batch 2)
        assert result.top_papers[1].citationCount == 8000
        assert result.top_papers[2].paperId == "top3"  # 5000 citations (batch 2)
        assert result.top_papers[2].citationCount == 5000

        # Verify API was called with correct pagination params
        papers_calls = [
            call for call in mock_client.get_with_retry.call_args_list if "/papers" in call[0][0]
        ]
        assert len(papers_calls) == 2

        # First call should have offset=0
        first_call_params = papers_calls[0][1]["params"]
        assert first_call_params["offset"] == 0
        assert first_call_params["limit"] == 1000

        # Second call should have offset=1000
        second_call_params = papers_calls[1][1]["params"]
        assert second_call_params["offset"] == 1000
        assert second_call_params["limit"] == 1000

    @pytest.mark.asyncio
    async def test_min_citations_filter(
        self, mock_client: MagicMock, mock_tracker: MagicMock
    ) -> None:
        """Test filtering papers by minimum citation count."""
        papers = [
            self._make_paper("p1", "Paper 1", citation_count=1000),
            self._make_paper("p2", "Paper 2", citation_count=500),
            self._make_paper("p3", "Paper 3", citation_count=50),  # Below threshold
            self._make_paper("p4", "Paper 4", citation_count=300),
            self._make_paper("p5", "Paper 5", citation_count=10),  # Below threshold
        ]

        mock_client.get_with_retry.side_effect = [
            self._make_author_response(),
            self._make_papers_response(papers),
        ]

        result = await get_author_top_papers("1741101", top_n=5, min_citations=100)

        assert isinstance(result, AuthorTopPapers)
        # Only 3 papers have >= 100 citations
        assert len(result.top_papers) == 3

        # Verify all returned papers meet the threshold
        for paper in result.top_papers:
            assert (paper.citationCount or 0) >= 100

        # Verify sorting is correct
        assert result.top_papers[0].citationCount == 1000
        assert result.top_papers[1].citationCount == 500
        assert result.top_papers[2].citationCount == 300

    @pytest.mark.asyncio
    async def test_author_not_found(self, mock_client: MagicMock) -> None:
        """Test error handling when author is not found."""
        mock_client.get_with_retry.side_effect = NotFoundError("Author not found")

        result = await get_author_top_papers("invalid_id")

        assert isinstance(result, str)
        assert "not found" in result.lower()
        assert "invalid_id" in result

    @pytest.mark.asyncio
    async def test_handles_none_citation_counts(
        self, mock_client: MagicMock, mock_tracker: MagicMock
    ) -> None:
        """Test that papers with None citation counts are handled correctly."""
        papers = [
            self._make_paper("p1", "Paper 1", citation_count=100),
            {"paperId": "p2", "title": "Paper 2", "citationCount": None},  # None citations
            self._make_paper("p3", "Paper 3", citation_count=200),
        ]

        mock_client.get_with_retry.side_effect = [
            self._make_author_response(),
            self._make_papers_response(papers),
        ]

        result = await get_author_top_papers("1741101", top_n=3)

        assert isinstance(result, AuthorTopPapers)
        assert len(result.top_papers) == 3

        # Paper with None citations should be treated as 0 and sorted last
        assert result.top_papers[0].citationCount == 200
        assert result.top_papers[1].citationCount == 100
        assert result.top_papers[2].citationCount is None

    @pytest.mark.asyncio
    async def test_top_n_validation(self, mock_client: MagicMock, mock_tracker: MagicMock) -> None:
        """Test that top_n is validated to be between 1 and 100."""
        papers = [self._make_paper(f"p{i}", f"Paper {i}", citation_count=i) for i in range(5)]

        # Test with top_n > 100 (should be clamped to 100)
        mock_client.get_with_retry.side_effect = [
            self._make_author_response(),
            self._make_papers_response(papers),
        ]

        result = await get_author_top_papers("1741101", top_n=200)
        assert isinstance(result, AuthorTopPapers)
        # With only 5 papers available, we get 5
        assert len(result.top_papers) == 5

        # Test with top_n < 1 (should be clamped to 1)
        mock_client.get_with_retry.side_effect = [
            self._make_author_response(),
            self._make_papers_response(papers),
        ]

        result = await get_author_top_papers("1741101", top_n=0)
        assert isinstance(result, AuthorTopPapers)
        assert len(result.top_papers) == 1

    @pytest.mark.asyncio
    async def test_empty_papers_list(self, mock_client: MagicMock, mock_tracker: MagicMock) -> None:
        """Test handling of author with no papers."""
        mock_client.get_with_retry.side_effect = [
            self._make_author_response(paper_count=0),
            self._make_papers_response([]),
        ]

        result = await get_author_top_papers("1741101", top_n=5)

        assert isinstance(result, AuthorTopPapers)
        assert len(result.top_papers) == 0
        assert result.papers_fetched == 0

    @pytest.mark.asyncio
    async def test_papers_tracked_for_bibtex(
        self, mock_client: MagicMock, mock_tracker: MagicMock
    ) -> None:
        """Test that returned papers are tracked for BibTeX export."""
        papers = [
            self._make_paper("p1", "Paper 1", citation_count=500),
            self._make_paper("p2", "Paper 2", citation_count=300),
        ]

        mock_client.get_with_retry.side_effect = [
            self._make_author_response(),
            self._make_papers_response(papers),
        ]

        result = await get_author_top_papers("1741101", top_n=2)

        assert isinstance(result, AuthorTopPapers)
        mock_tracker.track_many.assert_called_once()
        tracked_papers, source = mock_tracker.track_many.call_args[0]
        assert len(tracked_papers) == 2
        assert source == "get_author_top_papers"

    @pytest.mark.asyncio
    async def test_no_sort_parameter_in_api_call(
        self, mock_client: MagicMock, mock_tracker: MagicMock
    ) -> None:
        """Verify that the sort parameter is NOT sent to the API."""
        papers = [self._make_paper("p1", "Paper 1", citation_count=100)]

        mock_client.get_with_retry.side_effect = [
            self._make_author_response(),
            self._make_papers_response(papers),
        ]

        await get_author_top_papers("1741101", top_n=5)

        # Find the papers API call
        papers_call = None
        for call in mock_client.get_with_retry.call_args_list:
            if "/papers" in call[0][0]:
                papers_call = call
                break

        assert papers_call is not None
        params = papers_call[1]["params"]

        # Verify sort parameter is NOT present
        assert "sort" not in params
