"""Unit tests for the rate limiter module."""

from unittest.mock import AsyncMock, patch

import pytest

from semantic_scholar_mcp.exceptions import RateLimitError
from semantic_scholar_mcp.rate_limiter import (
    RateLimiter,
    RetryConfig,
    TokenBucket,
    create_rate_limiter,
    with_retry,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = RetryConfig()
        assert config.max_retries == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == 0.1

    def test_custom_values(self) -> None:
        """Test that custom values can be set."""
        config = RetryConfig(
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=0.2,
        )
        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter == 0.2


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_calculate_delay_exponential_backoff(self) -> None:
        """Test that delay increases exponentially with each attempt."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=0.0)
        limiter = RateLimiter(config=config)

        # Without jitter, delays should be predictable
        assert limiter.calculate_delay(0) == 1.0  # 1 * 2^0 = 1
        assert limiter.calculate_delay(1) == 2.0  # 1 * 2^1 = 2
        assert limiter.calculate_delay(2) == 4.0  # 1 * 2^2 = 4
        assert limiter.calculate_delay(3) == 8.0  # 1 * 2^3 = 8

    def test_calculate_delay_respects_max_delay(self) -> None:
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=0.0,
        )
        limiter = RateLimiter(config=config)

        # Delay should be capped at max_delay
        assert limiter.calculate_delay(0) == 1.0
        assert limiter.calculate_delay(2) == 4.0
        assert limiter.calculate_delay(3) == 5.0  # Would be 8, capped at 5
        assert limiter.calculate_delay(10) == 5.0  # Would be 1024, capped at 5

    def test_calculate_delay_uses_retry_after_when_provided(self) -> None:
        """Test that Retry-After value is used when provided."""
        config = RetryConfig(base_delay=1.0, jitter=0.0)
        limiter = RateLimiter(config=config)

        # Should use Retry-After value instead of calculated delay
        assert limiter.calculate_delay(0, retry_after=10.0) == 10.0
        assert limiter.calculate_delay(5, retry_after=30.0) == 30.0

    def test_calculate_delay_with_jitter(self) -> None:
        """Test that jitter adds randomness to delay."""
        config = RetryConfig(base_delay=1.0, jitter=0.5, exponential_base=2.0)
        limiter = RateLimiter(config=config)

        # With jitter, delay should be between base and base*(1+jitter)
        delays = [limiter.calculate_delay(0) for _ in range(100)]

        # All delays should be at least the base delay
        assert all(d >= 1.0 for d in delays)

        # All delays should be at most base * (1 + jitter)
        assert all(d <= 1.5 for d in delays)

        # With 100 samples, there should be some variance
        assert len(set(delays)) > 1

    def test_should_retry_returns_true_within_limit(self) -> None:
        """Test that should_retry returns True within retry limit."""
        config = RetryConfig(max_retries=3)
        limiter = RateLimiter(config=config)

        assert limiter.should_retry(0) is True
        assert limiter.should_retry(1) is True
        assert limiter.should_retry(2) is True

    def test_should_retry_returns_false_at_limit(self) -> None:
        """Test that should_retry returns False at retry limit."""
        config = RetryConfig(max_retries=3)
        limiter = RateLimiter(config=config)

        assert limiter.should_retry(3) is False
        assert limiter.should_retry(4) is False
        assert limiter.should_retry(100) is False


class TestWithRetry:
    """Tests for with_retry function."""

    @pytest.mark.asyncio
    async def test_successful_call_returns_immediately(self) -> None:
        """Test that successful calls return without retry."""
        mock_func = AsyncMock(return_value="success")

        result = await with_retry(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_error(self) -> None:
        """Test that RateLimitError triggers retry."""
        mock_func = AsyncMock(side_effect=[RateLimitError("Rate limited"), "success"])
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)

        with patch("semantic_scholar_mcp.rate_limiter.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(mock_func, config=config)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        """Test that error is raised after max retries exhausted."""
        error = RateLimitError("Rate limited")
        mock_func = AsyncMock(side_effect=error)
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=0.0)

        with (
            patch("semantic_scholar_mcp.rate_limiter.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(RateLimitError),
        ):
            await with_retry(mock_func, config=config)

        # Initial call + 2 retries = 3 total calls
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_uses_retry_after_from_error(self) -> None:
        """Test that Retry-After from error is used for delay."""
        error_with_retry_after = RateLimitError("Rate limited", retry_after=5.0)
        mock_func = AsyncMock(side_effect=[error_with_retry_after, "success"])
        config = RetryConfig(max_retries=3, base_delay=1.0, jitter=0.0)

        with patch(
            "semantic_scholar_mcp.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            result = await with_retry(mock_func, config=config)

        assert result == "success"
        # Should have slept for approximately 5.0 seconds
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert sleep_duration == 5.0

    @pytest.mark.asyncio
    async def test_non_rate_limit_errors_propagate(self) -> None:
        """Test that non-RateLimitError exceptions propagate immediately."""
        mock_func = AsyncMock(side_effect=ValueError("Some other error"))
        config = RetryConfig(max_retries=3)

        with pytest.raises(ValueError, match="Some other error"):
            await with_retry(mock_func, config=config)

        # Should not retry on non-rate-limit errors
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_default_config_when_not_provided(self) -> None:
        """Test that default config is used when not provided."""
        mock_func = AsyncMock(return_value="success")

        result = await with_retry(mock_func)

        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs_correctly(self) -> None:
        """Test that arguments are passed correctly to the function."""
        mock_func = AsyncMock(return_value="success")

        await with_retry(mock_func, "arg1", "arg2", key1="val1", key2="val2")

        mock_func.assert_called_once_with("arg1", "arg2", key1="val1", key2="val2")


class TestRateLimitErrorRetryAfter:
    """Tests for RateLimitError with retry_after parameter."""

    def test_rate_limit_error_stores_retry_after(self) -> None:
        """Test that RateLimitError stores retry_after value."""
        error = RateLimitError("Rate limited", retry_after=30.0)
        assert error.retry_after == 30.0

    def test_rate_limit_error_retry_after_defaults_to_none(self) -> None:
        """Test that retry_after defaults to None."""
        error = RateLimitError("Rate limited")
        assert error.retry_after is None

    def test_rate_limit_error_message(self) -> None:
        """Test that error message is preserved."""
        error = RateLimitError("Custom message", retry_after=10.0)
        assert str(error) == "Custom message"


class TestTokenBucket:
    """Tests for TokenBucket class."""

    @pytest.mark.asyncio
    async def test_acquire_returns_zero_when_tokens_available(self) -> None:
        """Test that acquire() returns 0 when tokens are available."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        # Bucket starts full, so acquire should return 0
        wait_time = await bucket.acquire(1.0)
        assert wait_time == 0.0

        # Can acquire multiple tokens if available
        wait_time = await bucket.acquire(5.0)
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_acquire_waits_when_tokens_unavailable(self) -> None:
        """Test that acquire() waits when tokens are unavailable."""
        bucket = TokenBucket(rate=10.0, capacity=2.0)

        # Use all tokens
        await bucket.acquire(2.0)

        # Mock sleep to avoid actual waiting
        with patch(
            "semantic_scholar_mcp.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            wait_time = await bucket.acquire(1.0)

            # Should have waited (1 token / 10 tokens per second = 0.1 seconds)
            assert wait_time > 0
            mock_sleep.assert_called_once()
            assert mock_sleep.call_args[0][0] == pytest.approx(0.1, rel=0.01)

    @pytest.mark.asyncio
    async def test_token_replenishment_over_time(self) -> None:
        """Test that tokens are replenished based on elapsed time."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        # Use all tokens
        await bucket.acquire(10.0)

        # Simulate time passing by manually updating last_update
        import time

        bucket._last_update = time.monotonic() - 0.5  # 0.5 seconds ago

        # Should now have ~5 tokens (10 rate * 0.5 seconds)
        # Acquiring 5 tokens should not need to wait
        with patch(
            "semantic_scholar_mcp.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            wait_time = await bucket.acquire(5.0)

            # Should not have waited since tokens replenished
            assert wait_time == 0.0
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_capacity_limits_token_accumulation(self) -> None:
        """Test that tokens don't exceed capacity."""
        bucket = TokenBucket(rate=10.0, capacity=5.0)

        # Simulate a long time passing
        import time

        bucket._last_update = time.monotonic() - 100.0  # 100 seconds ago

        # Even with long time passed, should only have capacity (5) tokens
        # Acquiring 5 should work, acquiring more should wait
        await bucket.acquire(5.0)

        # Now bucket should be empty, acquire should wait
        with patch(
            "semantic_scholar_mcp.rate_limiter.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await bucket.acquire(1.0)
            mock_sleep.assert_called_once()


class TestCreateRateLimiter:
    """Tests for create_rate_limiter factory function."""

    def test_with_api_key_returns_strict_bucket(self) -> None:
        """Test that with API key returns 1 req/sec bucket."""
        bucket = create_rate_limiter(has_api_key=True)

        assert isinstance(bucket, TokenBucket)
        assert bucket.rate == 1.0
        assert bucket.capacity == 1.0

    def test_without_api_key_returns_permissive_bucket(self) -> None:
        """Test that without API key returns more permissive bucket."""
        bucket = create_rate_limiter(has_api_key=False)

        assert isinstance(bucket, TokenBucket)
        assert bucket.rate == 10.0
        assert bucket.capacity == 20.0
