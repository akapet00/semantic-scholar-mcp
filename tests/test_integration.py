"""Integration tests using real Semantic Scholar API.

These tests hit the actual API and verify end-to-end functionality.
Run with: uv run pytest tests/test_integration.py -v -m integration
"""

import pytest
import pytest_asyncio

from semantic_scholar_mcp.client import SemanticScholarClient
from semantic_scholar_mcp.paper_tracker import PaperTracker
from semantic_scholar_mcp.tools._common import set_client_getter
from semantic_scholar_mcp.tools.papers import search_papers

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def real_client():
    """Create a real client for integration tests."""
    client = SemanticScholarClient()
    set_client_getter(lambda: client)
    yield client
    await client.close()


@pytest.fixture(autouse=True)
def reset_tracker_integration():
    """Reset tracker between integration tests."""
    PaperTracker.reset_instance()
    yield
    PaperTracker.reset_instance()


class TestSearchIntegration:
    """Integration tests for paper search."""

    @pytest.mark.asyncio
    async def test_search_real_papers(self, real_client: SemanticScholarClient) -> None:
        """Test searching for a known paper returns results."""
        result = await search_papers("attention is all you need", limit=5)

        assert isinstance(result, list)
        assert len(result) > 0
        assert any("attention" in p.title.lower() for p in result)

    @pytest.mark.asyncio
    async def test_search_with_year_filter(self, real_client: SemanticScholarClient) -> None:
        """Test search with year filter."""
        result = await search_papers(
            "transformer neural network",
            year="2020-2024",
            limit=5,
        )

        assert isinstance(result, list)
        if result:  # May be empty for very specific queries
            assert all(2020 <= (p.year or 0) <= 2024 for p in result)
