"""Unit tests for the paper tracker module."""

import pytest

from semantic_scholar_mcp.models import Author, Paper
from semantic_scholar_mcp.paper_tracker import (
    PaperTracker,
    TrackedPaper,
    get_tracker,
)


@pytest.fixture(autouse=True)
def reset_tracker() -> None:
    """Reset the tracker singleton before each test."""
    PaperTracker.reset_instance()


class TestPaperTracker:
    """Tests for PaperTracker class."""

    def test_singleton_pattern(self) -> None:
        """Test that get_instance returns the same instance."""
        tracker1 = PaperTracker.get_instance()
        tracker2 = PaperTracker.get_instance()

        assert tracker1 is tracker2

    def test_reset_instance_creates_new_instance(self) -> None:
        """Test that reset_instance creates a fresh instance."""
        tracker1 = PaperTracker.get_instance()
        tracker1.track(Paper(paperId="123", title="Test"), "test")

        PaperTracker.reset_instance()
        tracker2 = PaperTracker.get_instance()

        assert tracker2.count() == 0

    def test_track_paper(self) -> None:
        """Test tracking a single paper."""
        tracker = PaperTracker.get_instance()
        paper = Paper(paperId="123", title="Test Paper", year=2020)

        tracker.track(paper, "search_papers")

        assert tracker.count() == 1
        assert tracker.is_tracked("123")

    def test_track_paper_updates_existing(self) -> None:
        """Test that tracking same paper updates source tool."""
        tracker = PaperTracker.get_instance()
        paper = Paper(paperId="123", title="Test Paper", year=2020)

        tracker.track(paper, "search_papers")
        tracker.track(paper, "get_paper_details")

        assert tracker.count() == 1
        tracked = tracker.get_tracked_paper("123")
        assert tracked is not None
        assert tracked.source_tool == "get_paper_details"

    def test_track_paper_without_id_is_ignored(self) -> None:
        """Test that papers without IDs are not tracked."""
        tracker = PaperTracker.get_instance()
        paper = Paper(title="Test Paper")

        tracker.track(paper, "search_papers")

        assert tracker.count() == 0

    def test_track_many_papers(self) -> None:
        """Test tracking multiple papers at once."""
        tracker = PaperTracker.get_instance()
        papers = [
            Paper(paperId="123", title="Paper 1"),
            Paper(paperId="456", title="Paper 2"),
            Paper(paperId="789", title="Paper 3"),
        ]

        tracker.track_many(papers, "search_papers")

        assert tracker.count() == 3
        assert tracker.is_tracked("123")
        assert tracker.is_tracked("456")
        assert tracker.is_tracked("789")

    def test_get_all_papers(self) -> None:
        """Test getting all tracked papers."""
        tracker = PaperTracker.get_instance()
        papers = [
            Paper(paperId="123", title="Paper 1"),
            Paper(paperId="456", title="Paper 2"),
        ]
        tracker.track_many(papers, "search_papers")

        result = tracker.get_all_papers()

        assert len(result) == 2
        paper_ids = [p.paperId for p in result]
        assert "123" in paper_ids
        assert "456" in paper_ids

    def test_get_papers_by_tool(self) -> None:
        """Test filtering papers by source tool."""
        tracker = PaperTracker.get_instance()
        tracker.track(Paper(paperId="123", title="Paper 1"), "search_papers")
        tracker.track(Paper(paperId="456", title="Paper 2"), "get_recommendations")
        tracker.track(Paper(paperId="789", title="Paper 3"), "search_papers")

        search_papers = tracker.get_papers_by_tool("search_papers")
        rec_papers = tracker.get_papers_by_tool("get_recommendations")

        assert len(search_papers) == 2
        assert len(rec_papers) == 1
        assert rec_papers[0].paperId == "456"

    def test_get_papers_by_ids(self) -> None:
        """Test getting specific papers by IDs."""
        tracker = PaperTracker.get_instance()
        tracker.track_many(
            [
                Paper(paperId="123", title="Paper 1"),
                Paper(paperId="456", title="Paper 2"),
                Paper(paperId="789", title="Paper 3"),
            ],
            "test",
        )

        result = tracker.get_papers_by_ids(["123", "789"])

        assert len(result) == 2
        paper_ids = [p.paperId for p in result]
        assert "123" in paper_ids
        assert "789" in paper_ids
        assert "456" not in paper_ids

    def test_get_papers_by_ids_preserves_order(self) -> None:
        """Test that get_papers_by_ids returns papers in requested order."""
        tracker = PaperTracker.get_instance()
        tracker.track_many(
            [
                Paper(paperId="123", title="Paper 1"),
                Paper(paperId="456", title="Paper 2"),
                Paper(paperId="789", title="Paper 3"),
            ],
            "test",
        )

        result = tracker.get_papers_by_ids(["789", "123"])

        assert len(result) == 2
        assert result[0].paperId == "789"
        assert result[1].paperId == "123"

    def test_get_papers_by_ids_handles_missing(self) -> None:
        """Test that get_papers_by_ids handles missing IDs."""
        tracker = PaperTracker.get_instance()
        tracker.track(Paper(paperId="123", title="Paper 1"), "test")

        result = tracker.get_papers_by_ids(["123", "nonexistent"])

        assert len(result) == 1
        assert result[0].paperId == "123"

    def test_get_tracked_paper(self) -> None:
        """Test getting tracked paper metadata."""
        tracker = PaperTracker.get_instance()
        paper = Paper(paperId="123", title="Test Paper")
        tracker.track(paper, "search_papers")

        tracked = tracker.get_tracked_paper("123")

        assert tracked is not None
        assert tracked.paper.paperId == "123"
        assert tracked.source_tool == "search_papers"
        assert tracked.tracked_at is not None

    def test_get_tracked_paper_returns_none_for_missing(self) -> None:
        """Test that get_tracked_paper returns None for missing paper."""
        tracker = PaperTracker.get_instance()

        tracked = tracker.get_tracked_paper("nonexistent")

        assert tracked is None

    def test_is_tracked(self) -> None:
        """Test checking if a paper is tracked."""
        tracker = PaperTracker.get_instance()
        tracker.track(Paper(paperId="123", title="Test"), "test")

        assert tracker.is_tracked("123") is True
        assert tracker.is_tracked("456") is False

    def test_count(self) -> None:
        """Test counting tracked papers."""
        tracker = PaperTracker.get_instance()

        assert tracker.count() == 0

        tracker.track(Paper(paperId="123", title="Test"), "test")
        assert tracker.count() == 1

        tracker.track(Paper(paperId="456", title="Test 2"), "test")
        assert tracker.count() == 2

    def test_clear(self) -> None:
        """Test clearing all tracked papers."""
        tracker = PaperTracker.get_instance()
        tracker.track_many(
            [
                Paper(paperId="123", title="Paper 1"),
                Paper(paperId="456", title="Paper 2"),
            ],
            "test",
        )

        tracker.clear()

        assert tracker.count() == 0
        assert tracker.is_tracked("123") is False

    def test_get_tool_summary(self) -> None:
        """Test getting summary of papers by tool."""
        tracker = PaperTracker.get_instance()
        tracker.track(Paper(paperId="1", title="P1"), "search_papers")
        tracker.track(Paper(paperId="2", title="P2"), "search_papers")
        tracker.track(Paper(paperId="3", title="P3"), "get_recommendations")
        tracker.track(Paper(paperId="4", title="P4"), "get_paper_details")

        summary = tracker.get_tool_summary()

        assert summary == {
            "search_papers": 2,
            "get_recommendations": 1,
            "get_paper_details": 1,
        }


class TestTrackedPaper:
    """Tests for TrackedPaper dataclass."""

    def test_tracked_paper_creation(self) -> None:
        """Test creating a TrackedPaper."""
        paper = Paper(paperId="123", title="Test Paper")
        tracked = TrackedPaper(paper=paper, source_tool="search_papers")

        assert tracked.paper.paperId == "123"
        assert tracked.source_tool == "search_papers"
        assert tracked.tracked_at is not None


class TestGetTracker:
    """Tests for get_tracker convenience function."""

    def test_get_tracker_returns_singleton(self) -> None:
        """Test that get_tracker returns the singleton instance."""
        tracker1 = get_tracker()
        tracker2 = get_tracker()

        assert tracker1 is tracker2
        assert tracker1 is PaperTracker.get_instance()
