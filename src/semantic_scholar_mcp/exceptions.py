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
