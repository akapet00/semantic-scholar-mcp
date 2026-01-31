"""Rate limiter with exponential backoff for Semantic Scholar API.

Semantic Scholar requires exponential backoff for all API requests.
Rate limits:
- Unauthenticated: 5,000 requests per 5 minutes (shared pool)
- With API Key (search/batch/recommendations): 1 request per second
- With API Key (other endpoints): 10 requests per second
"""

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from semantic_scholar_mcp.exceptions import RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay in seconds between retries.
        exponential_base: Base for exponential backoff calculation.
        jitter: Random jitter factor (0.0 to 1.0) to add to delays.
    """

    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1


@dataclass
class RateLimiter:
    """Rate limiter with exponential backoff calculation.

    Provides methods to calculate delays for retry attempts following
    exponential backoff with optional jitter.

    Attributes:
        config: RetryConfig with backoff parameters.
    """

    config: RetryConfig = field(default_factory=RetryConfig)

    def calculate_delay(
        self,
        attempt: int,
        retry_after: float | None = None,
    ) -> float:
        """Calculate delay for a retry attempt.

        Uses exponential backoff with jitter, respecting any Retry-After
        header value from the server.

        Args:
            attempt: The current retry attempt number (0-indexed).
            retry_after: Optional Retry-After value from server response.

        Returns:
            Delay in seconds before the next retry attempt.
        """
        if retry_after is not None and retry_after > 0:
            # Use server-specified delay with jitter
            jitter_amount = retry_after * self.config.jitter * random.random()
            return retry_after + jitter_amount

        # Calculate exponential backoff
        exponential_delay = self.config.base_delay * (self.config.exponential_base**attempt)

        # Apply max delay cap
        delay = min(exponential_delay, self.config.max_delay)

        # Add jitter
        jitter_amount = delay * self.config.jitter * random.random()
        return delay + jitter_amount

    def should_retry(self, attempt: int) -> bool:
        """Check if another retry attempt should be made.

        Args:
            attempt: The current retry attempt number (0-indexed).

        Returns:
            True if more retries are allowed, False otherwise.
        """
        return attempt < self.config.max_retries


async def with_retry(
    func: Callable[..., Any],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an async function with automatic retry on rate limit errors.

    Wraps an async API call with exponential backoff retry logic. When a
    RateLimitError is encountered, the function will wait and retry up to
    the configured maximum number of attempts.

    Args:
        func: Async function to execute.
        *args: Positional arguments to pass to the function.
        config: Optional RetryConfig for customizing retry behavior.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of the function call.

    Raises:
        RateLimitError: If all retry attempts are exhausted.
        Exception: Any other exception raised by the function.

    Example:
        >>> result = await with_retry(client.get, "/paper/search", params={"query": "test"})
    """
    if config is None:
        config = RetryConfig()

    rate_limiter = RateLimiter(config=config)
    last_error: RateLimitError | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except RateLimitError as e:
            last_error = e

            if not rate_limiter.should_retry(attempt):
                logger.warning(
                    "Rate limit exceeded after %d attempts, giving up",
                    attempt + 1,
                )
                raise

            delay = rate_limiter.calculate_delay(attempt, e.retry_after)
            logger.info(
                "Rate limit hit, retrying in %.2f seconds (attempt %d/%d)",
                delay,
                attempt + 1,
                config.max_retries,
            )
            await asyncio.sleep(delay)

    # This should not be reached, but just in case
    if last_error is not None:
        raise last_error
    raise RuntimeError("Unexpected state in retry loop")
