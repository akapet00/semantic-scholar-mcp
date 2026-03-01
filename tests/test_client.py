"""Unit tests for the Semantic Scholar HTTP client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from semantic_scholar_mcp.client import SemanticScholarClient
from semantic_scholar_mcp.exceptions import (
    APIConnectionError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SemanticScholarError,
    ServerError,
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
            assert "/paper/search" in error_message
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


class TestAPIConnectionErrorHandling:
    """Tests for connection error handling."""

    @pytest.mark.asyncio
    async def test_timeout_raises_connection_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that timeout errors are wrapped in APIConnectionError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(APIConnectionError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "timed out" in error_message.lower()

    @pytest.mark.asyncio
    async def test_connect_error_raises_connection_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that connection errors are wrapped in APIConnectionError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(APIConnectionError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "Failed to connect" in error_message

    @pytest.mark.asyncio
    async def test_post_timeout_raises_connection_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that POST timeout errors are wrapped in APIConnectionError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(APIConnectionError) as exc_info:
                    await client.post("/papers/", json_data={"positivePaperIds": ["123"]})

            error_message = str(exc_info.value)
            assert "timed out" in error_message.lower()

    @pytest.mark.asyncio
    async def test_post_connect_error_raises_connection_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that POST connection errors are wrapped in APIConnectionError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(APIConnectionError) as exc_info:
                    await client.post("/papers/", json_data={"positivePaperIds": ["123"]})

            error_message = str(exc_info.value)
            assert "Failed to connect" in error_message

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


class TestAuthenticationError:
    """Tests for HTTP 401/403 authentication error handling."""

    @pytest.mark.asyncio
    async def test_http_401_raises_authentication_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that HTTP 401 raises AuthenticationError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=401, text="Unauthorized")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(AuthenticationError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "Authentication failed" in error_message
            assert "/paper/search" in error_message
            assert "API key" in error_message

    @pytest.mark.asyncio
    async def test_http_403_raises_authentication_error(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that HTTP 403 raises AuthenticationError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=403, text="Forbidden")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(AuthenticationError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "Authentication failed" in error_message


class TestOtherHttpErrors:
    """Tests for other HTTP error handling."""

    @pytest.mark.asyncio
    async def test_http_500_raises_server_error(self, mock_settings_no_api_key: MagicMock) -> None:
        """Test that HTTP 500 raises ServerError."""
        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=500, text="Internal server error")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                with pytest.raises(ServerError) as exc_info:
                    await client.get("/paper/search")

            error_message = str(exc_info.value)
            assert "500" in error_message
            assert "/paper/search" in error_message
            assert exc_info.value.status_code == 500

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


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration with the client."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_consecutive_failures(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that circuit opens after N consecutive connection errors."""
        # Configure circuit breaker with low threshold for testing
        mock_settings_no_api_key.circuit_failure_threshold = 3
        mock_settings_no_api_key.circuit_recovery_timeout = 30.0

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            # Simulate connection errors
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                # Make requests until circuit opens
                for _i in range(3):
                    with pytest.raises(APIConnectionError):
                        await client.get("/paper/search")

                # Next request should fail fast due to open circuit
                with pytest.raises(APIConnectionError) as exc_info:
                    await client.get("/paper/search")

                # Verify it's a circuit breaker error, not a connection error
                assert "circuit breaker" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_circuit_rejects_when_open(self, mock_settings_no_api_key: MagicMock) -> None:
        """Test that requests fail fast when circuit is open."""
        mock_settings_no_api_key.circuit_failure_threshold = 2
        mock_settings_no_api_key.circuit_recovery_timeout = 60.0  # Long timeout

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                # Trip the circuit breaker
                for _ in range(2):
                    with pytest.raises(APIConnectionError):
                        await client.get("/paper/search")

                # Verify subsequent requests fail fast
                call_count_before = mock_client.get.call_count

                with pytest.raises(APIConnectionError) as exc_info:
                    await client.get("/paper/search")

                # No new network call should have been made
                assert mock_client.get.call_count == call_count_before
                assert "circuit breaker" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that circuit transitions to half-open after recovery timeout."""
        mock_settings_no_api_key.circuit_failure_threshold = 2
        mock_settings_no_api_key.circuit_recovery_timeout = 0.1  # Short timeout for testing

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            # First fail, then succeed
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                # Trip the circuit breaker
                for _ in range(2):
                    with pytest.raises(APIConnectionError):
                        await client.get("/paper/search")

                # Wait for recovery timeout
                import asyncio

                await asyncio.sleep(0.15)

                # Circuit should now be half-open and allow a test call
                # The call will fail but it proves we got past the open state
                call_count_before = mock_client.get.call_count

                with pytest.raises(APIConnectionError):
                    await client.get("/paper/search")

                # A new network call should have been made
                assert mock_client.get.call_count > call_count_before

    @pytest.mark.asyncio
    async def test_circuit_closes_on_successful_half_open(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that circuit closes after successful half-open call."""
        mock_settings_no_api_key.circuit_failure_threshold = 2
        mock_settings_no_api_key.circuit_recovery_timeout = 0.1  # Short timeout for testing

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            # Start with failures, then succeed
            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise httpx.ConnectError("Connection refused")
                # Return success after half-open
                return create_mock_response(status_code=200, json_data={"data": "test"})

            mock_client.get = AsyncMock(side_effect=side_effect)

            async with SemanticScholarClient() as client:
                # Trip the circuit breaker
                for _ in range(2):
                    with pytest.raises(APIConnectionError):
                        await client.get("/paper/search")

                # Wait for recovery timeout
                import asyncio

                await asyncio.sleep(0.15)

                # Successful half-open call should close the circuit
                result = await client.get("/paper/search")
                assert result == {"data": "test"}

                # Subsequent calls should work normally
                result2 = await client.get("/paper/search")
                assert result2 == {"data": "test"}

    @pytest.mark.asyncio
    async def test_rate_limit_does_not_trip_circuit(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that 429 rate limit errors do not trip the circuit breaker."""
        mock_settings_no_api_key.circuit_failure_threshold = 2
        mock_settings_no_api_key.circuit_recovery_timeout = 30.0

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            # Simulate rate limit responses
            mock_response = create_mock_response(status_code=429, text="Rate limit exceeded")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                # Make multiple rate-limited requests
                for _ in range(5):
                    with pytest.raises(RateLimitError):
                        await client.get("/paper/search")

                # Circuit should still be closed - verify by checking that
                # subsequent requests still hit the network
                call_count_before = mock_client.get.call_count

                with pytest.raises(RateLimitError):
                    await client.get("/paper/search")

                # A network call should have been made (circuit not open)
                assert mock_client.get.call_count == call_count_before + 1

    @pytest.mark.asyncio
    async def test_not_found_does_not_trip_circuit(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that 404 not found errors do not trip the circuit breaker."""
        mock_settings_no_api_key.circuit_failure_threshold = 2
        mock_settings_no_api_key.circuit_recovery_timeout = 30.0

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            # Simulate 404 responses
            mock_response = create_mock_response(status_code=404, text="Not found")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                # Make multiple not-found requests
                for _ in range(5):
                    with pytest.raises(NotFoundError):
                        await client.get("/paper/nonexistent")

                # Circuit should still be closed - verify by checking that
                # subsequent requests still hit the network
                call_count_before = mock_client.get.call_count

                with pytest.raises(NotFoundError):
                    await client.get("/paper/nonexistent")

                # A network call should have been made (circuit not open)
                assert mock_client.get.call_count == call_count_before + 1


class TestLargeResponseLogging:
    """Tests for large response size logging."""

    @pytest.mark.asyncio
    async def test_logs_warning_for_large_response(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that a warning is logged when response exceeds threshold."""
        # Set threshold to 100 bytes for testing
        mock_settings_no_api_key.large_response_threshold = 100

        # Create a response with content larger than threshold
        large_data = {"data": "x" * 200}  # More than 100 bytes when serialized

        with (
            patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class,
            patch("semantic_scholar_mcp.client.logger") as mock_logger,
        ):
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data=large_data)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.get("/paper/search")

            # Verify warning was logged
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0]
            assert "Large API response" in call_args[0]
            assert "/paper/search" in call_args[1]

    @pytest.mark.asyncio
    async def test_no_warning_for_small_response(self, mock_settings_no_api_key: MagicMock) -> None:
        """Test that no warning is logged when response is below threshold."""
        # Set threshold to 50000 bytes (default)
        mock_settings_no_api_key.large_response_threshold = 50000

        # Create a small response
        small_data = {"data": "small"}

        with (
            patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class,
            patch("semantic_scholar_mcp.client.logger") as mock_logger,
        ):
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data=small_data)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.get("/paper/search")

            # Verify no large response warning was logged
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if "Large API response" in str(call)
            ]
            assert len(warning_calls) == 0

    @pytest.mark.asyncio
    async def test_logs_correct_response_size(self, mock_settings_no_api_key: MagicMock) -> None:
        """Test that the logged size matches actual response content size."""
        # Set threshold to 10 bytes for testing
        mock_settings_no_api_key.large_response_threshold = 10

        # Create response with known content size
        known_content = b'{"test": "data"}'  # 16 bytes

        with (
            patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class,
            patch("semantic_scholar_mcp.client.logger") as mock_logger,
        ):
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(
                status_code=200, json_data={"test": "data"}, content=known_content
            )
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.get("/paper/search")

            # Verify the logged size matches (16 bytes)
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0]
            assert call_args[2] == 16  # response_size argument

    @pytest.mark.asyncio
    async def test_logs_warning_for_large_post_response(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test that a warning is logged for large POST responses."""
        # Set threshold to 100 bytes for testing
        mock_settings_no_api_key.large_response_threshold = 100

        # Create a response with content larger than threshold
        large_data = {"recommendedPapers": [{"paperId": "x" * 200}]}

        with (
            patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class,
            patch("semantic_scholar_mcp.client.logger") as mock_logger,
        ):
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data=large_data)
            mock_response.request.method = "POST"
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                await client.post("/papers/", json_data={"positivePaperIds": ["123"]}, params=None)

            # Verify warning was logged
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0]
            assert "Large API response" in call_args[0]


class TestPostCaching:
    """Tests for POST request caching."""

    @pytest.mark.asyncio
    async def test_non_cacheable_post_not_cached(self, mock_settings_no_api_key: MagicMock) -> None:
        """Test that non-cacheable POST endpoints are not cached."""
        expected_data = {"data": [SAMPLE_PAPER_RESPONSE]}
        request_body = {"ids": ["12345"]}

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data=expected_data)
            mock_response.request.method = "POST"
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                result1 = await client.post("/paper/batch", json_data=request_body)
                result2 = await client.post("/paper/batch", json_data=request_body)

            assert result1 == expected_data
            assert result2 == expected_data
            # Both calls should hit the API (no caching for this endpoint)
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_post_circuit_breaker_open(self, mock_settings_no_api_key: MagicMock) -> None:
        """Test that POST requests fail fast when circuit breaker is open."""
        mock_settings_no_api_key.circuit_failure_threshold = 2
        mock_settings_no_api_key.circuit_recovery_timeout = 60.0

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                # Trip the circuit breaker with POST
                for _ in range(2):
                    with pytest.raises(APIConnectionError):
                        await client.post("/papers/", json_data={"positivePaperIds": ["123"]})

                # Next POST should fail fast
                with pytest.raises(APIConnectionError) as exc_info:
                    await client.post("/papers/", json_data={"positivePaperIds": ["123"]})

                assert "circuit breaker" in str(exc_info.value).lower()


class TestRetryMethods:
    """Tests for retry wrapper methods."""

    @pytest.mark.asyncio
    async def test_get_with_retry_auto_retry_disabled(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test get_with_retry falls back to get() when auto-retry is disabled."""
        mock_settings_no_api_key.enable_auto_retry = False

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data={"data": "test"})
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                result = await client.get_with_retry("/paper/search")

            assert result == {"data": "test"}
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_with_retry_auto_retry_disabled(
        self, mock_settings_no_api_key: MagicMock
    ) -> None:
        """Test post_with_retry falls back to post() when auto-retry is disabled."""
        mock_settings_no_api_key.enable_auto_retry = False

        with patch("semantic_scholar_mcp.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            mock_response = create_mock_response(status_code=200, json_data={"data": "test"})
            mock_response.request.method = "POST"
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with SemanticScholarClient() as client:
                result = await client.post_with_retry(
                    "/papers/", json_data={"positivePaperIds": ["123"]}
                )

            assert result == {"data": "test"}
            mock_client.post.assert_called_once()
