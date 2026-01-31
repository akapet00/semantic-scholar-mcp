"""Shared test fixtures for Semantic Scholar MCP server tests."""

from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from semantic_scholar_mcp.client import SemanticScholarClient


@pytest.fixture
def mock_settings_no_api_key() -> Generator[MagicMock]:
    """Mock settings without an API key configured."""
    with patch("semantic_scholar_mcp.client.settings") as mock_settings:
        mock_settings.api_key = None
        mock_settings.has_api_key = False
        mock_settings.graph_api_base_url = "https://api.semanticscholar.org/graph/v1"
        mock_settings.recommendations_api_base_url = (
            "https://api.semanticscholar.org/recommendations/v1"
        )
        yield mock_settings


@pytest.fixture
def mock_settings_with_api_key() -> Generator[MagicMock]:
    """Mock settings with an API key configured."""
    with patch("semantic_scholar_mcp.client.settings") as mock_settings:
        mock_settings.api_key = "test-api-key-12345"
        mock_settings.has_api_key = True
        mock_settings.graph_api_base_url = "https://api.semanticscholar.org/graph/v1"
        mock_settings.recommendations_api_base_url = (
            "https://api.semanticscholar.org/recommendations/v1"
        )
        yield mock_settings


@pytest_asyncio.fixture
async def client(
    mock_settings_no_api_key: MagicMock,
) -> AsyncGenerator[SemanticScholarClient]:
    """Create a SemanticScholarClient instance for testing."""
    async with SemanticScholarClient() as client:
        yield client


@pytest_asyncio.fixture
async def client_with_api_key(
    mock_settings_with_api_key: MagicMock,
) -> AsyncGenerator[SemanticScholarClient]:
    """Create a SemanticScholarClient instance with API key for testing."""
    async with SemanticScholarClient() as client:
        yield client


def create_mock_response(
    status_code: int = 200,
    json_data: dict[str, Any] | None = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Create a mock httpx.Response object.

    Args:
        status_code: HTTP status code.
        json_data: JSON response data.
        text: Response text for error messages.
        headers: Optional response headers.

    Returns:
        Mock httpx.Response object.
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_data or {}
    response.request = MagicMock()
    response.request.method = "GET"
    response.headers = headers or {}
    return response


@pytest.fixture
def mock_httpx_client() -> Generator[AsyncMock]:
    """Create a mock httpx.AsyncClient."""
    with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_class:
        mock_instance = AsyncMock()
        mock_instance.is_closed = False
        mock_instance.aclose = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


# Sample response data for reuse in tests
SAMPLE_PAPER_RESPONSE: dict[str, Any] = {
    "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
    "title": "Attention Is All You Need",
    "abstract": "The dominant sequence transduction models...",
    "year": 2017,
    "citationCount": 100000,
    "authors": [
        {"authorId": "1234", "name": "Ashish Vaswani"},
        {"authorId": "5678", "name": "Noam Shazeer"},
    ],
    "venue": "NeurIPS",
    "publicationTypes": ["Conference"],
    "openAccessPdf": {"url": "https://arxiv.org/pdf/1706.03762.pdf"},
    "fieldsOfStudy": ["Computer Science"],
}

SAMPLE_AUTHOR_RESPONSE: dict[str, Any] = {
    "authorId": "1234",
    "name": "Ashish Vaswani",
    "affiliations": ["Google Brain"],
    "paperCount": 50,
    "citationCount": 150000,
    "hIndex": 25,
}

SAMPLE_SEARCH_RESPONSE: dict[str, Any] = {
    "total": 1,
    "data": [SAMPLE_PAPER_RESPONSE],
}
