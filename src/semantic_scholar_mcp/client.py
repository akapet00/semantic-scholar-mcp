"""Async HTTP client for Semantic Scholar API."""

import logging
from typing import Any

import httpx

from semantic_scholar_mcp.cache import get_cache
from semantic_scholar_mcp.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
)
from semantic_scholar_mcp.config import settings
from semantic_scholar_mcp.exceptions import (
    APIConnectionError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SemanticScholarError,
    ServerError,
)
from semantic_scholar_mcp.rate_limiter import (
    RetryConfig,
    TokenBucket,
    create_rate_limiter,
    with_retry,
)

logger = logging.getLogger(__name__)


def _is_circuit_breaker_error(error: Exception) -> bool:
    """Check if an error should trip the circuit breaker.

    Only connection errors, timeouts, and server errors (5xx) should trip the
    circuit breaker. Client errors like 404 (NotFoundError) and 429 (RateLimitError)
    indicate the API is working but rejecting specific requests, so they should
    not contribute to circuit breaker failures.

    Args:
        error: The exception to check.

    Returns:
        True if the error should count as a circuit breaker failure.
    """
    # Connection/timeout errors should trip circuit breaker
    if isinstance(error, (httpx.ConnectError, httpx.TimeoutException)):
        return True

    # Server errors (5xx) should trip circuit breaker
    if isinstance(error, ServerError):
        return True

    # Our custom APIConnectionError (wrapped from httpx errors) should trip circuit breaker
    if isinstance(error, APIConnectionError):
        return True

    # Rate limit (429) and not found (404) should NOT trip circuit breaker
    # These indicate the API is working, just rejecting specific requests
    if isinstance(error, (RateLimitError, NotFoundError)):
        return False

    # Other errors (authentication, validation, etc.) should not trip circuit breaker
    return False


class _NonCircuitBreakerResult:
    """Wrapper for exceptions that should not trip the circuit breaker.

    This is used to signal that the API responded (circuit should not trip),
    but the response was an error that should still be raised to the caller.
    """

    def __init__(self, exception: Exception) -> None:
        self.exception = exception


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

    # Endpoints that are read-only despite using POST (cacheable)
    CACHEABLE_POST_ENDPOINTS: frozenset[str] = frozenset(
        [
            "/recommendations/v1/papers/",
            "/recommendations/v1/papers",
        ]
    )

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
        self._rate_limiter: TokenBucket = create_rate_limiter(settings.has_api_key)
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=settings.circuit_failure_threshold,
                recovery_timeout=settings.circuit_recovery_timeout,
            )
        )

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

    def _is_cacheable_post(self, endpoint: str) -> bool:
        """Check if POST endpoint should be cached.

        Some POST endpoints are read-only (like recommendations) and can be
        safely cached based on the request body.

        Args:
            endpoint: The API endpoint path.

        Returns:
            True if the endpoint is cacheable.
        """
        return any(endpoint.startswith(prefix) for prefix in self.CACHEABLE_POST_ENDPOINTS)

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
            AuthenticationError: If API key is invalid (HTTP 401/403).
            ServerError: If server returns 5xx error.
            SemanticScholarError: For other HTTP errors.
        """
        logger.info(
            "API response: method=%s endpoint=%s status=%d",
            response.request.method,
            endpoint,
            response.status_code,
        )

        # Success
        if response.status_code < 400:
            return response.json()

        # Rate limit exceeded
        if response.status_code == 429:
            retry_after: float | None = None
            retry_after_header = response.headers.get("Retry-After")
            if retry_after_header is not None:
                try:
                    retry_after = float(retry_after_header)
                except ValueError:
                    pass

            raise RateLimitError(
                f"Rate limit exceeded for {endpoint}. "
                "Consider using an API key for higher limits. "
                "See: https://www.semanticscholar.org/product/api#api-key",
                retry_after=retry_after,
            )

        # Authentication errors
        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"Authentication failed for {endpoint}. "
                "Please verify your API key is valid and has the required permissions."
            )

        # Not found
        if response.status_code == 404:
            raise NotFoundError(
                f"Resource not found: {endpoint}. "
                "For DOIs, use format 'DOI:10.xxxx/xxxxx'. "
                "For ArXiv IDs, use format 'ARXIV:xxxx.xxxxx'."
            )

        # Server errors (5xx) - these are retriable
        if 500 <= response.status_code < 600:
            raise ServerError(
                f"Semantic Scholar API server error ({response.status_code}) for {endpoint}. "
                "This is usually temporary. Please try again.",
                status_code=response.status_code,
            )

        # Other client errors (4xx)
        raise SemanticScholarError(
            f"API error ({response.status_code}) for {endpoint}: {response.text}"
        )

    async def _do_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        use_recommendations_api: bool,
    ) -> Any:
        """Internal GET request logic (called by circuit breaker).

        Args:
            endpoint: API endpoint path.
            params: Optional query parameters.
            use_recommendations_api: If True, use Recommendations API base URL.

        Returns:
            Parsed JSON response data, or _NonCircuitBreakerResult wrapping
            an exception that should not trip the circuit breaker.

        Raises:
            APIConnectionError: If connection fails or times out.
            ServerError: If server returns 5xx error.
        """
        base_url = (
            self.recommendations_api_base_url
            if use_recommendations_api
            else self.graph_api_base_url
        )
        url = f"{base_url}{endpoint}"

        logger.info("API request: method=GET endpoint=%s params=%s", endpoint, params)

        # Acquire rate limit token before making request
        wait_time = await self._rate_limiter.acquire()
        if wait_time > 0:
            logger.debug("Rate limiter: waited %.2fs before request", wait_time)

        client = await self._get_client()
        try:
            response = await client.get(url, params=params)
        except httpx.ConnectError as e:
            raise APIConnectionError(f"Failed to connect to Semantic Scholar API: {e}") from e
        except httpx.TimeoutException as e:
            raise APIConnectionError(f"Request timed out: {e}") from e

        try:
            return await self._handle_response(response, endpoint)
        except Exception as e:
            # Only let circuit-breaker-worthy errors propagate as exceptions
            # Other errors (404, 429, etc.) are wrapped to prevent circuit breaker from tripping
            if _is_circuit_breaker_error(e):
                raise
            return _NonCircuitBreakerResult(e)

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
            APIConnectionError: If connection fails or times out.
            SemanticScholarError: For other API errors.
        """
        # Check cache first (before circuit breaker)
        cache = get_cache()
        cached = cache.get(endpoint, params)
        if cached is not None:
            return cached

        # Use circuit breaker for the actual request
        try:
            result = await self._circuit_breaker.call(
                self._do_get, endpoint, params, use_recommendations_api
            )
        except CircuitOpenError:
            raise APIConnectionError(
                "Service temporarily unavailable. The circuit breaker is open "
                "due to repeated failures."
            ) from None

        # Unwrap non-circuit-breaker errors and raise them
        if isinstance(result, _NonCircuitBreakerResult):
            raise result.exception

        # Cache successful response
        cache.set(endpoint, params, result)
        return result

    async def _do_post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None,
        params: dict[str, Any] | None,
        use_recommendations_api: bool,
    ) -> Any:
        """Internal POST request logic (called by circuit breaker).

        Args:
            endpoint: API endpoint path.
            json_data: JSON body data to send.
            params: Optional query parameters.
            use_recommendations_api: If True, use Recommendations API base URL.

        Returns:
            Parsed JSON response data, or _NonCircuitBreakerResult wrapping
            an exception that should not trip the circuit breaker.

        Raises:
            APIConnectionError: If connection fails or times out.
            ServerError: If server returns 5xx error.
        """
        base_url = (
            self.recommendations_api_base_url
            if use_recommendations_api
            else self.graph_api_base_url
        )
        url = f"{base_url}{endpoint}"

        logger.info("API request: method=POST endpoint=%s params=%s", endpoint, params)

        # Acquire rate limit token before making request
        wait_time = await self._rate_limiter.acquire()
        if wait_time > 0:
            logger.debug("Rate limiter: waited %.2fs before request", wait_time)

        client = await self._get_client()
        try:
            response = await client.post(url, json=json_data, params=params)
        except httpx.ConnectError as e:
            raise APIConnectionError(f"Failed to connect to Semantic Scholar API: {e}") from e
        except httpx.TimeoutException as e:
            raise APIConnectionError(f"Request timed out: {e}") from e

        try:
            return await self._handle_response(response, endpoint)
        except Exception as e:
            # Only let circuit-breaker-worthy errors propagate as exceptions
            # Other errors (404, 429, etc.) are wrapped to prevent circuit breaker from tripping
            if _is_circuit_breaker_error(e):
                raise
            return _NonCircuitBreakerResult(e)

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
            APIConnectionError: If connection fails or times out.
            SemanticScholarError: For other API errors.
        """
        # Check cache for cacheable POST endpoints
        cache = get_cache()
        is_cacheable = self._is_cacheable_post(endpoint)
        if is_cacheable:
            # Include json_data in cache key for POST requests
            cache_params = {"_body": json_data, **(params or {})}
            cached = cache.get(endpoint, cache_params)
            if cached is not None:
                return cached

        # Use circuit breaker for the actual request
        try:
            result = await self._circuit_breaker.call(
                self._do_post, endpoint, json_data, params, use_recommendations_api
            )
        except CircuitOpenError:
            raise APIConnectionError(
                "Service temporarily unavailable. The circuit breaker is open "
                "due to repeated failures."
            ) from None

        # Unwrap non-circuit-breaker errors and raise them
        if isinstance(result, _NonCircuitBreakerResult):
            raise result.exception

        # Cache cacheable POST responses
        if is_cacheable:
            cache_params = {"_body": json_data, **(params or {})}
            cache.set(endpoint, cache_params, result)

        return result

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
