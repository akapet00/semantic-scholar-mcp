"""Unit tests for the Semantic Scholar HTTP client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from semantic_scholar_mcp.client import SemanticScholarClient
from semantic_scholar_mcp.exceptions import (
    NotFoundError,
    RateLimitError,
    SemanticScholarError,
)

from .conftest import (
    SAMPLE_PAPER_RESPONSE,
    SAMPLE_SEARCH_RESPONSE,
    create_mock_response,
)


class TestSemanticScholarClientGet:
    """Tests for the GET request method."""

    @pytest.mark.asyncio
    async def test_successful_get_request_returns_parsed_response(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that a successful GET request returns parsed JSON response."""
        expected_data = SAMPLE_SEARCH_RESPONSE

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data=expected_data)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                result = await client.get("/paper/search", params={"query": "attention"})

            assert result == expected_data
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_request_uses_graph_api_base_url_by_default(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that GET requests use the Graph API base URL by default."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data={})
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.get("/paper/search")

            called_url = mock_client.get.call_args[0][0]
            assert called_url.startswith("https://api.semanticscholar.org/graph/v1")

    @pytest.mark.asyncio
    async def test_get_request_uses_recommendations_api_when_specified(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that GET requests use Recommendations API when specified."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data={})
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.get("/papers/forpaper/12345", use_recommendations_api=True)

            called_url = mock_client.get.call_args[0][0]
            assert called_url.startswith("https://api.semanticscholar.org/recommendations/v1")


class TestSemanticScholarClientPost:
    """Tests for the POST request method."""

    @pytest.mark.asyncio
    async def test_successful_post_request_returns_parsed_response(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that a successful POST request returns parsed JSON response."""
        expected_data = {"recommendedPapers": [SAMPLE_PAPER_RESPONSE]}
        request_body = {"positivePaperIds": ["12345"], "negativePaperIds": []}

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data=expected_data)
            mock_response.request.method = "POST"
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                result = await client.post(
                    "/papers/", json_data=request_body, use_recommendations_api=True
                )

            assert result == expected_data
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["json"] == request_body

    @pytest.mark.asyncio
    async def test_post_request_includes_query_params(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that POST requests include query parameters."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data={})
            mock_response.request.method = "POST"
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.post(
                    "/papers/",
                    json_data={"positivePaperIds": ["123"]},
                    params={"limit": 10},
                    use_recommendations_api=True,
                )

            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["params"] == {"limit": 10}


class TestRateLimitError:
    """Tests for HTTP 429 rate limit handling."""

    @pytest.mark.asyncio
    async def test_http_429_raises_rate_limit_error_with_informative_message(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that HTTP 429 raises RateLimitError with helpful message."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=429, text="Rate limit exceeded")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(RateLimitError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "Rate limit exceeded" in error_message
            assert "5,000 requests" in error_message
            assert "API key" in error_message


class TestNotFoundError:
    """Tests for HTTP 404 not found handling."""

    @pytest.mark.asyncio
    async def test_http_404_raises_not_found_error_with_clear_message(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that HTTP 404 raises NotFoundError with clear message."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=404, text="Not found")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(NotFoundError) as exc_info:
                    await client.get("/paper/nonexistent-id")

            error_message = str(exc_info.value)
            assert "not found" in error_message.lower()
            assert "/paper/nonexistent-id" in error_message


class TestTimeoutHandling:
    """Tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_raises_appropriate_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that timeout errors are raised appropriately."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(httpx.TimeoutException):
                    await client.get("/paper/search")

    @pytest.mark.asyncio
    async def test_client_uses_configured_timeout(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that the client uses the configured timeout value."""
        custom_timeout = 60.0

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient(timeout=custom_timeout) as client:
                # Trigger client creation by accessing the internal client
                await client._get_client()

            # Verify timeout was passed to AsyncClient
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs["timeout"].connect == custom_timeout


class TestApiKeyHeader:
    """Tests for API key header handling."""

    @pytest.mark.asyncio
    async def test_api_key_header_included_when_configured(
        self, mock_settings_with_api_key: MagicMock
    ) -> None:
        """Test that x-api-key header is included when API key is configured."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data={})
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.get("/paper/search")

            # Verify headers were passed to AsyncClient
            call_kwargs = mock_client_class.call_args[1]
            headers = call_kwargs["headers"]
            assert "x-api-key" in headers
            assert headers["x-api-key"] == "test-api-key-12345"

    @pytest.mark.asyncio
    async def test_api_key_header_not_included_when_not_configured(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that x-api-key header is not included when API key is not set."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data={})
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.get("/paper/search")

            call_kwargs = mock_client_class.call_args[1]
            headers = call_kwargs["headers"]
            assert "x-api-key" not in headers


class TestOtherHttpErrors:
    """Tests for other HTTP error handling."""

    @pytest.mark.asyncio
    async def test_http_500_raises_semantic_scholar_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that HTTP 500 raises SemanticScholarError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=500, text="Internal server error")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(SemanticScholarError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "500" in error_message

    @pytest.mark.asyncio
    async def test_http_400_raises_semantic_scholar_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that HTTP 400 raises SemanticScholarError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=400, text="Bad request")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(SemanticScholarError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "400" in error_message


class TestClientContextManager:
    """Tests for the async context manager functionality."""

    @pytest.mark.asyncio
    async def test_client_closes_on_context_exit(self, mock_settings_no_api_key: MagicMock) -> None:
        """Test that client is properly closed when exiting context."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                # Trigger client creation
                await client._get_client()

            # Verify aclose was called
            mock_client.aclose.assert_called_once()
