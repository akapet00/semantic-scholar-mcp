"""Concurrency and thread-safety tests."""

import threading

import pytest

from semantic_scholar_mcp.models import Paper
from semantic_scholar_mcp.paper_tracker import PaperTracker, get_tracker


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset tracker between tests."""
    PaperTracker.reset_instance()
    yield
    PaperTracker.reset_instance()


class TestPaperTrackerConcurrency:
    """Thread-safety tests for paper tracker."""

    def test_concurrent_tracking(self) -> None:
        """Test tracking papers from multiple threads."""
        tracker = get_tracker()
        papers_per_thread = 100
        num_threads = 10

        def track_papers(thread_id: int) -> None:
            for i in range(papers_per_thread):
                paper = Paper(
                    paperId=f"paper-{thread_id}-{i}",
                    title=f"Paper {thread_id}-{i}",
                )
                tracker.track(paper, f"thread-{thread_id}")

        threads = [threading.Thread(target=track_papers, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All papers should be tracked
        assert tracker.count() == papers_per_thread * num_threads

    def test_concurrent_read_write(self) -> None:
        """Test concurrent reads and writes."""
        tracker = get_tracker()

        # Pre-populate with some papers
        for i in range(50):
            paper = Paper(paperId=f"initial-{i}", title=f"Initial {i}")
            tracker.track(paper, "setup")

        errors: list[Exception] = []

        def writer() -> None:
            try:
                for i in range(100):
                    paper = Paper(paperId=f"new-{i}", title=f"New {i}")
                    tracker.track(paper, "writer")
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(100):
                    _ = tracker.get_all_papers()
                    _ = tracker.count()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
