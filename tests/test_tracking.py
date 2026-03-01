"""Unit tests for tracking-related MCP tools (list, clear, export)."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from semantic_scholar_mcp.models import Author, Paper
from semantic_scholar_mcp.paper_tracker import PaperTracker
from semantic_scholar_mcp.tools import clear_tracked_papers, export_bibtex, list_tracked_papers
from semantic_scholar_mcp.tools._common import set_client_getter


def _make_paper(paper_id: str, title: str, year: int = 2020, author_name: str = "Smith") -> Paper:
    """Create a paper for testing."""
    return Paper(
        paperId=paper_id,
        title=title,
        year=year,
        authors=[Author(authorId="a1", name=author_name)],
    )


class TestListTrackedPapers:
    """Tests for list_tracked_papers tool."""

    @pytest.mark.asyncio
    async def test_no_papers_returns_message(self) -> None:
        """Test that no tracked papers returns an informative message."""
        result = await list_tracked_papers()

        assert isinstance(result, str)
        assert "No papers tracked" in result

    @pytest.mark.asyncio
    async def test_no_papers_with_source_tool_returns_message(self) -> None:
        """Test that no papers from a specific tool returns an informative message."""
        result = await list_tracked_papers(source_tool="search_papers")

        assert isinstance(result, str)
        assert "No papers tracked from 'search_papers'" in result

    @pytest.mark.asyncio
    async def test_returns_all_tracked_papers(self) -> None:
        """Test that all tracked papers are returned."""
        tracker = PaperTracker.get_instance()
        p1 = _make_paper("p1", "Paper 1")
        p2 = _make_paper("p2", "Paper 2")
        tracker.track(p1, "search_papers")
        tracker.track(p2, "get_paper_details")

        result = await list_tracked_papers()

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_papers_filtered_by_tool(self) -> None:
        """Test that papers are filtered by source tool."""
        tracker = PaperTracker.get_instance()
        p1 = _make_paper("p1", "Paper 1")
        p2 = _make_paper("p2", "Paper 2")
        tracker.track(p1, "search_papers")
        tracker.track(p2, "get_paper_details")

        result = await list_tracked_papers(source_tool="search_papers")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].paperId == "p1"


class TestClearTrackedPapers:
    """Tests for clear_tracked_papers tool."""

    @pytest.mark.asyncio
    async def test_clears_papers_with_count(self) -> None:
        """Test that clearing returns the count of cleared papers."""
        tracker = PaperTracker.get_instance()
        tracker.track(_make_paper("p1", "Paper 1"), "search_papers")
        tracker.track(_make_paper("p2", "Paper 2"), "search_papers")

        result = await clear_tracked_papers()

        assert "Cleared 2 tracked papers" in result
        assert tracker.count() == 0

    @pytest.mark.asyncio
    async def test_clears_empty_tracker(self) -> None:
        """Test that clearing an empty tracker returns zero count."""
        result = await clear_tracked_papers()

        assert "Cleared 0 tracked papers" in result


class TestExportBibtex:
    """Tests for export_bibtex tool."""

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

    @pytest.mark.asyncio
    async def test_export_tracked_papers(self) -> None:
        """Test exporting tracked papers to BibTeX."""
        tracker = PaperTracker.get_instance()
        tracker.track(_make_paper("p1", "Test Paper", 2020), "search_papers")

        result = await export_bibtex()

        assert isinstance(result, str)
        assert "@" in result
        assert "Test Paper" in result

    @pytest.mark.asyncio
    async def test_no_papers_returns_message(self) -> None:
        """Test that no tracked papers returns an informative message."""
        result = await export_bibtex()

        assert isinstance(result, str)
        assert "No papers tracked" in result

    @pytest.mark.asyncio
    async def test_specific_paper_ids_from_tracker(self) -> None:
        """Test exporting specific paper IDs that are already tracked."""
        tracker = PaperTracker.get_instance()
        tracker.track(_make_paper("p1", "Paper One", 2020), "search_papers")
        tracker.track(_make_paper("p2", "Paper Two", 2021), "search_papers")

        result = await export_bibtex(paper_ids=["p1"])

        assert isinstance(result, str)
        assert "Paper One" in result
        assert "Paper Two" not in result

    @pytest.mark.asyncio
    async def test_untracked_paper_ids_fetch_from_api(self, mock_client: MagicMock) -> None:
        """Test that untracked paper IDs are fetched from the API."""
        mock_client.get_with_retry.return_value = {
            "paperId": "remote1",
            "title": "Remote Paper",
            "year": 2022,
            "authors": [{"authorId": "a1", "name": "Author"}],
        }

        result = await export_bibtex(paper_ids=["remote1"])

        assert isinstance(result, str)
        assert "Remote Paper" in result
        mock_client.get_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found_paper_ids_handled(self, mock_client: MagicMock) -> None:
        """Test that not-found paper IDs are handled gracefully."""
        from semantic_scholar_mcp.exceptions import NotFoundError

        mock_client.get_with_retry.side_effect = NotFoundError("Not found")

        result = await export_bibtex(paper_ids=["nonexistent"])

        assert isinstance(result, str)
        assert "No papers found" in result

    @pytest.mark.asyncio
    async def test_custom_config_options(self) -> None:
        """Test export with custom configuration options."""
        tracker = PaperTracker.get_instance()
        paper = _make_paper("p1", "Config Paper", 2020)
        paper.abstract = "This is the abstract."
        tracker.track(paper, "search_papers")

        result = await export_bibtex(
            include_abstract=True,
            cite_key_format="paper_id",
        )

        assert isinstance(result, str)
        assert "abstract = {This is the abstract.}" in result
        assert "@misc{p1," in result

    @pytest.mark.asyncio
    async def test_write_to_file(self, tmp_path: Any) -> None:
        """Test writing BibTeX output to a file."""
        tracker = PaperTracker.get_instance()
        tracker.track(_make_paper("p1", "File Paper", 2020), "search_papers")

        output_file = str(tmp_path / "references.bib")
        result = await export_bibtex(file_path=output_file)

        assert "Successfully exported" in result
        assert os.path.exists(output_file)
        with open(output_file) as f:
            content = f.read()
        assert "File Paper" in content

    @pytest.mark.asyncio
    async def test_file_write_error(self) -> None:
        """Test handling of file write errors."""
        tracker = PaperTracker.get_instance()
        tracker.track(_make_paper("p1", "Error Paper", 2020), "search_papers")

        result = await export_bibtex(file_path="/nonexistent/directory/file.bib")

        assert isinstance(result, str)
        assert "Error writing to file" in result
