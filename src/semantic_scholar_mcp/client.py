"""Async HTTP client for Semantic Scholar API."""

import logging
from typing import Any

import httpx

from semantic_scholar_mcp.config import settings
from semantic_scholar_mcp.exceptions import NotFoundError, RateLimitError, SemanticScholarError
from semantic_scholar_mcp.rate_limiter import RetryConfig, with_retry

logger = logging.getLogger(__name__)


class SemanticScholarClient:
    """Async HTTP client for communicating with the Semantic Scholar API.

    This client handles requests to both the Graph API and Recommendations API,
    with support for optional API key authentication, timeout handling, and
    appropriate error handling for rate limits and not found responses.

    Attributes:
        graph_api_base_url: Base URL for the Graph API.
        recommendations_api_base_url: Base URL for the Recommendations API.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        graph_api_base_url: str | None = None,
        recommendations_api_base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Semantic Scholar client.

        Args:
            graph_api_base_url: Base URL for Graph API. Defaults to settings value.
            recommendations_api_base_url: Base URL for Recommendations API.
                Defaults to settings value.
            timeout: Request timeout in seconds. Defaults to 30.
        """
        self.graph_api_base_url = graph_api_base_url or settings.graph_api_base_url
        self.recommendations_api_base_url = (
            recommendations_api_base_url or settings.recommendations_api_base_url
        )
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers including API key if configured.

        Returns:
            Dictionary of HTTP headers.
        """
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if settings.has_api_key and settings.api_key:
            headers["x-api-key"] = settings.api_key
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client.

        Returns:
            The httpx AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._get_headers(),
                timeout=httpx.Timeout(self.timeout),
                verify=not settings.disable_ssl_verify,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _handle_response(self, response: httpx.Response, endpoint: str) -> Any:
        """Handle HTTP response and raise appropriate exceptions.

        Args:
            response: The HTTP response object.
            endpoint: The endpoint that was called (for logging).

        Returns:
            Parsed JSON response data.

        Raises:
            RateLimitError: If rate limit is exceeded (HTTP 429).
            NotFoundError: If resource is not found (HTTP 404).
            SemanticScholarError: For other HTTP errors.
        """
        logger.info(
            "API response: method=%s endpoint=%s status=%d",
            response.request.method,
            endpoint,
            response.status_code,
        )

        if response.status_code == 429:
            # Extract Retry-After header if present
            retry_after: float | None = None
            retry_after_header = response.headers.get("Retry-After")
            if retry_after_header is not None:
                try:
                    retry_after = float(retry_after_header)
                except ValueError:
                    pass

            raise RateLimitError(
                "Rate limit exceeded. The Semantic Scholar API allows 5,000 requests "
                "per 5 minutes for unauthenticated requests. Consider using an API key "
                "for higher limits, or wait before retrying.",
                retry_after=retry_after,
            )

        if response.status_code == 404:
            raise NotFoundError(
                f"Resource not found: {endpoint}. The requested paper, author, or "
                "other resource does not exist in the Semantic Scholar database. "
                "Please verify the ID is correct."
            )

        if response.status_code >= 400:
            raise SemanticScholarError(
                f"API request failed with status {response.status_code}: {response.text}"
            )

        return response.json()

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        use_recommendations_api: bool = False,
    ) -> Any:
        """Make a GET request to the Semantic Scholar API.

        Args:
            endpoint: API endpoint path (e.g., "/paper/search").
            params: Optional query parameters.
            use_recommendations_api: If True, use Recommendations API base URL.
                Defaults to False (uses Graph API).

        Returns:
            Parsed JSON response data.

        Raises:
            RateLimitError: If rate limit is exceeded.
            NotFoundError: If resource is not found.
            SemanticScholarError: For other API errors.
        """
        base_url = (
            self.recommendations_api_base_url
            if use_recommendations_api
            else self.graph_api_base_url
        )
        url = f"{base_url}{endpoint}"

        logger.info("API request: method=GET endpoint=%s params=%s", endpoint, params)

        client = await self._get_client()
        response = await client.get(url, params=params)
        return await self._handle_response(response, endpoint)

    async def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        use_recommendations_api: bool = False,
    ) -> Any:
        """Make a POST request to the Semantic Scholar API.

        Args:
            endpoint: API endpoint path.
            json_data: JSON body data to send.
            params: Optional query parameters.
            use_recommendations_api: If True, use Recommendations API base URL.
                Defaults to False (uses Graph API).

        Returns:
            Parsed JSON response data.

        Raises:
            RateLimitError: If rate limit is exceeded.
            NotFoundError: If resource is not found.
            SemanticScholarError: For other API errors.
        """
        base_url = (
            self.recommendations_api_base_url
            if use_recommendations_api
            else self.graph_api_base_url
        )
        url = f"{base_url}{endpoint}"

        logger.info("API request: method=POST endpoint=%s params=%s", endpoint, params)

        client = await self._get_client()
        response = await client.post(url, json=json_data, params=params)
        return await self._handle_response(response, endpoint)

    def _get_retry_config(self) -> RetryConfig:
        """Get retry configuration from settings.

        Returns:
            RetryConfig with values from environment settings.
        """
        return RetryConfig(
            max_retries=settings.retry_max_attempts,
            base_delay=settings.retry_base_delay,
            max_delay=settings.retry_max_delay,
        )

    async def get_with_retry(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        use_recommendations_api: bool = False,
    ) -> Any:
        """Make a GET request with automatic retry on rate limit errors.

        This method wraps the standard GET request with exponential backoff
        retry logic. If auto-retry is disabled in settings, it behaves
        identically to the regular get() method.

        Args:
            endpoint: API endpoint path (e.g., "/paper/search").
            params: Optional query parameters.
            use_recommendations_api: If True, use Recommendations API base URL.
                Defaults to False (uses Graph API).

        Returns:
            Parsed JSON response data.

        Raises:
            RateLimitError: If rate limit is exceeded and all retries fail.
            NotFoundError: If resource is not found.
            SemanticScholarError: For other API errors.
        """
        if not settings.enable_auto_retry:
            return await self.get(endpoint, params, use_recommendations_api)

        return await with_retry(
            self.get,
            endpoint,
            params,
            use_recommendations_api,
            config=self._get_retry_config(),
        )

    async def post_with_retry(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        use_recommendations_api: bool = False,
    ) -> Any:
        """Make a POST request with automatic retry on rate limit errors.

        This method wraps the standard POST request with exponential backoff
        retry logic. If auto-retry is disabled in settings, it behaves
        identically to the regular post() method.

        Args:
            endpoint: API endpoint path.
            json_data: JSON body data to send.
            params: Optional query parameters.
            use_recommendations_api: If True, use Recommendations API base URL.
                Defaults to False (uses Graph API).

        Returns:
            Parsed JSON response data.

        Raises:
            RateLimitError: If rate limit is exceeded and all retries fail.
            NotFoundError: If resource is not found.
            SemanticScholarError: For other API errors.
        """
        if not settings.enable_auto_retry:
            return await self.post(endpoint, json_data, params, use_recommendations_api)

        return await with_retry(
            self.post,
            endpoint,
            json_data,
            params,
            use_recommendations_api,
            config=self._get_retry_config(),
        )

    async def __aenter__(self) -> "SemanticScholarClient":
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager and close client."""
        await self.close()
