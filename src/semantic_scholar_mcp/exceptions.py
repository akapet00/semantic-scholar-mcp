"""Custom exceptions for Semantic Scholar MCP server."""


class SemanticScholarError(Exception):
    """Base exception for Semantic Scholar API errors."""

    pass


class RateLimitError(SemanticScholarError):
    """Raised when API rate limit is exceeded (HTTP 429).

    The Semantic Scholar API allows 5,000 requests per 5 minutes for
    unauthenticated requests, or higher limits with an API key.

    Attributes:
        retry_after: Optional number of seconds to wait before retrying,
            extracted from the Retry-After response header.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        """Initialize RateLimitError.

        Args:
            message: Error message describing the rate limit.
            retry_after: Optional seconds to wait before retrying.
        """
        super().__init__(message)
        self.retry_after = retry_after


class NotFoundError(SemanticScholarError):
    """Raised when a requested resource is not found (HTTP 404).

    This can occur when a paper ID, author ID, or other identifier
    does not exist in the Semantic Scholar database.
    """

    pass


class ValidationError(SemanticScholarError):
    """Raised when input validation fails.

    This can occur when required parameters are missing or have
    invalid values.
    """

    pass


class ServerError(SemanticScholarError):
    """Raised when the Semantic Scholar API returns a 5xx server error.

    This typically indicates a temporary issue with the API servers.
    These errors are often transient and may succeed on retry.

    Attributes:
        status_code: The HTTP status code (5xx) returned by the server.
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize ServerError.

        Args:
            message: Error message describing the server error.
            status_code: The HTTP status code (e.g., 500, 502, 503).
        """
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(SemanticScholarError):
    """Raised when API key authentication fails.

    This indicates the API key is invalid, expired, or lacks required permissions.
    """

    pass


class ConnectionError(SemanticScholarError):
    """Raised when unable to connect to the Semantic Scholar API.

    This may indicate network issues, DNS failures, or API unavailability.
    """

    pass
