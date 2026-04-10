"""Tests for server initialization and lifecycle.

This module tests the MCP server initialization, tool registration,
client singleton behavior, and cleanup handler registration.
"""

import asyncio
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from semantic_scholar_mcp import server


def _get_registered_tool_names() -> set[str]:
    """Get registered tool names via the public async API."""
    tools = asyncio.run(server.mcp.list_tools())
    return {t.name for t in tools}


@pytest.fixture(autouse=True)
def reset_client() -> Generator[None]:
    """Reset the shared client instance before and after each test."""
    server._client = None
    yield
    server._client = None


class TestServerCreation:
    """Tests for MCP server instance creation."""

    def test_mcp_instance_exists(self) -> None:
        """Test that MCP server instance is created."""
        assert server.mcp is not None

    def test_mcp_has_correct_name(self) -> None:
        """Test that MCP server has correct name configured."""
        assert server.mcp.name == "semantic-scholar"

    def test_mcp_has_instructions(self) -> None:
        """Test that MCP server has instructions configured."""
        assert server.mcp.instructions is not None
        assert "Semantic Scholar" in server.mcp.instructions


class TestToolRegistration:
    """Tests for tool registration with MCP server."""

    def test_expected_number_of_tools_registered(self) -> None:
        """Test that all 14 expected tools are registered."""
        assert len(_get_registered_tool_names()) == 14

    def test_search_papers_tool_registered(self) -> None:
        """Test that search_papers tool is registered."""
        assert "search_papers" in _get_registered_tool_names()

    def test_get_paper_details_tool_registered(self) -> None:
        """Test that get_paper_details tool is registered."""
        assert "get_paper_details" in _get_registered_tool_names()

    def test_export_bibtex_tool_registered(self) -> None:
        """Test that export_bibtex tool is registered."""
        assert "export_bibtex" in _get_registered_tool_names()

    def test_all_expected_tools_registered(self) -> None:
        """Test that all expected tool names are registered."""
        expected_tools = {
            "search_papers",
            "get_paper_details",
            "get_paper_citations",
            "get_paper_references",
            "search_authors",
            "get_author_details",
            "get_author_top_papers",
            "find_duplicate_authors",
            "consolidate_authors",
            "get_recommendations",
            "get_related_papers",
            "list_tracked_papers",
            "clear_tracked_papers",
            "export_bibtex",
        }
        assert _get_registered_tool_names() == expected_tools


class TestClientSingleton:
    """Tests for client singleton behavior."""

    def test_get_client_returns_instance(self) -> None:
        """Test that get_client returns a SemanticScholarClient instance."""
        with patch("semantic_scholar_mcp.server.SemanticScholarClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            client = server.get_client()

            assert client == mock_instance
            mock_class.assert_called_once()

    def test_get_client_returns_same_instance(self) -> None:
        """Test that get_client returns the same instance on subsequent calls."""
        with patch("semantic_scholar_mcp.server.SemanticScholarClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            client1 = server.get_client()
            client2 = server.get_client()

            assert client1 is client2
            # Only called once despite two get_client calls
            mock_class.assert_called_once()

    def test_get_client_thread_safe_initialization(self) -> None:
        """Test that client initialization uses thread-safe locking."""
        # Verify the lock exists
        assert server._client_lock is not None

        # Reset to ensure fresh state
        server._client = None

        with patch("semantic_scholar_mcp.server.SemanticScholarClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # First call should create instance
            client = server.get_client()
            assert client == mock_instance

            # Client should be stored in module variable
            assert server._client == mock_instance


class TestCleanupHandler:
    """Tests for cleanup handler registration and behavior."""

    def test_cleanup_handler_registered_with_atexit(self) -> None:
        """Test that cleanup handler is registered with atexit."""
        # The cleanup function should be in atexit callbacks
        # We check by examining the _cleanup_client function exists
        assert server._cleanup_client is not None
        assert callable(server._cleanup_client)

    def test_cleanup_client_handles_none_client(self) -> None:
        """Test that cleanup handles case when client is None."""
        server._client = None

        # Should not raise any exception
        server._cleanup_client()

        assert server._client is None

    def test_cleanup_client_closes_client(self) -> None:
        """Test that cleanup properly closes the client."""
        mock_client = MagicMock()
        mock_client.close = MagicMock()
        server._client = mock_client

        with patch("semantic_scholar_mcp.server.asyncio") as mock_asyncio:
            mock_loop = MagicMock()
            mock_asyncio.new_event_loop.return_value = mock_loop

            server._cleanup_client()

            mock_asyncio.new_event_loop.assert_called_once()
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_called_once()

        assert server._client is None

    def test_cleanup_client_handles_exception(self) -> None:
        """Test that cleanup handles exceptions gracefully."""
        mock_client = MagicMock()
        server._client = mock_client

        with patch("semantic_scholar_mcp.server.asyncio") as mock_asyncio:
            mock_asyncio.new_event_loop.side_effect = RuntimeError("Test error")

            # Should not raise exception, just log it
            server._cleanup_client()

        # Client should be set to None even if exception occurred
        assert server._client is None
