"""Session-based paper tracking for Semantic Scholar MCP.

This module provides a singleton tracker that keeps track of papers
retrieved during a session, enabling features like BibTeX export of
all papers from a research session.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from semantic_scholar_mcp.logging_config import get_logger
from semantic_scholar_mcp.models import Paper

logger = get_logger("paper_tracker")


@dataclass
class TrackedPaper:
    """A paper with tracking metadata.

    Attributes:
        paper: The paper object.
        source_tool: Name of the tool that retrieved this paper.
        tracked_at: Timestamp when the paper was tracked.
    """

    paper: Paper
    source_tool: str
    tracked_at: datetime = field(default_factory=datetime.now)


class PaperTracker:
    """Singleton tracker for papers retrieved during a session.

    This class maintains a session-scoped collection of papers that
    have been retrieved through various MCP tools. It enables users
    to export all papers from their research session to BibTeX format.

    Thread-safe implementation using double-checked locking pattern.

    Usage:
        tracker = PaperTracker.get_instance()
        tracker.track(paper, "search_papers")
        all_papers = tracker.get_all_papers()
        tracker.clear()
    """

    _instance: ClassVar["PaperTracker | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Initialize the paper tracker."""
        self._papers: dict[str, TrackedPaper] = {}
        self._papers_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "PaperTracker":
        """Get the singleton instance of PaperTracker (thread-safe).

        Returns:
            The singleton PaperTracker instance.
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = PaperTracker()
        assert cls._instance is not None
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        with cls._lock:
            cls._instance = None

    def track(self, paper: Paper, source_tool: str) -> None:
        """Track a paper from a specific tool (thread-safe).

        If the paper has already been tracked, updates the source tool
        and timestamp.

        Args:
            paper: The paper to track.
            source_tool: Name of the tool that retrieved this paper.
        """
        if paper.paperId:
            with self._papers_lock:
                self._papers[paper.paperId] = TrackedPaper(
                    paper=paper,
                    source_tool=source_tool,
                )
                logger.debug("Tracking paper: %s (source: %s)", paper.paperId, source_tool)

    def track_many(self, papers: list[Paper], source_tool: str) -> None:
        """Track multiple papers from a specific tool.

        Args:
            papers: List of papers to track.
            source_tool: Name of the tool that retrieved these papers.
        """
        logger.debug("Tracking %d papers (source: %s)", len(papers), source_tool)
        for paper in papers:
            self.track(paper, source_tool)

    def get_all_papers(self) -> list[Paper]:
        """Get all tracked papers (thread-safe).

        Returns:
            List of all tracked papers, sorted by tracking time.
        """
        with self._papers_lock:
            sorted_tracked = sorted(
                self._papers.values(),
                key=lambda tp: tp.tracked_at,
            )
            return [tp.paper for tp in sorted_tracked]

    def get_papers_by_tool(self, tool_name: str) -> list[Paper]:
        """Get papers tracked from a specific tool (thread-safe).

        Args:
            tool_name: Name of the tool to filter by.

        Returns:
            List of papers from the specified tool.
        """
        with self._papers_lock:
            matching = [tp for tp in self._papers.values() if tp.source_tool == tool_name]
            sorted_tracked = sorted(matching, key=lambda tp: tp.tracked_at)
            return [tp.paper for tp in sorted_tracked]

    def get_papers_by_ids(self, paper_ids: list[str]) -> list[Paper]:
        """Get specific papers by their IDs (thread-safe).

        Args:
            paper_ids: List of paper IDs to retrieve.

        Returns:
            List of papers with the specified IDs (in order requested).
        """
        with self._papers_lock:
            papers = []
            for paper_id in paper_ids:
                if paper_id in self._papers:
                    papers.append(self._papers[paper_id].paper)
            return papers

    def get_tracked_paper(self, paper_id: str) -> TrackedPaper | None:
        """Get a tracked paper with its metadata (thread-safe).

        Args:
            paper_id: The paper ID to look up.

        Returns:
            TrackedPaper if found, None otherwise.
        """
        with self._papers_lock:
            return self._papers.get(paper_id)

    def is_tracked(self, paper_id: str) -> bool:
        """Check if a paper is tracked (thread-safe).

        Args:
            paper_id: The paper ID to check.

        Returns:
            True if the paper is tracked, False otherwise.
        """
        with self._papers_lock:
            return paper_id in self._papers

    def count(self) -> int:
        """Get the number of tracked papers (thread-safe).

        Returns:
            Count of tracked papers.
        """
        with self._papers_lock:
            return len(self._papers)

    def clear(self) -> None:
        """Clear all tracked papers (thread-safe)."""
        with self._papers_lock:
            count = len(self._papers)
            self._papers.clear()
            logger.info("Cleared %d tracked papers", count)

    def get_tool_summary(self) -> dict[str, int]:
        """Get a summary of papers by source tool (thread-safe).

        Returns:
            Dictionary mapping tool names to paper counts.
        """
        with self._papers_lock:
            summary: dict[str, int] = {}
            for tracked in self._papers.values():
                tool = tracked.source_tool
                summary[tool] = summary.get(tool, 0) + 1
            return summary


# Convenience function to get the tracker instance
def get_tracker() -> PaperTracker:
    """Get the global paper tracker instance.

    Returns:
        The singleton PaperTracker instance.
    """
    return PaperTracker.get_instance()
