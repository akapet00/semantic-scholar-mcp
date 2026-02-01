"""Unit tests for the circuit breaker module."""

import time
from unittest.mock import AsyncMock

import pytest

from semantic_scholar_mcp.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
)


class TestCircuitBreakerState:
    """Tests for circuit breaker state management."""

    def test_circuit_starts_closed(self) -> None:
        """Test that circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failure_threshold(self) -> None:
        """Test that circuit opens after failure_threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))

        # Make 3 failing calls (threshold)
        for _ in range(3):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_recovery_timeout(self) -> None:
        """Test that circuit transitions to HALF_OPEN after recovery_timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))
        success_func = AsyncMock(return_value="success")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Simulate time passing by updating the last_failure_time
        breaker._last_failure_time = time.monotonic() - 1.5  # 1.5 seconds ago

        # Next call should transition to HALF_OPEN and succeed
        result = await breaker.call(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_circuit_closes_on_success_in_half_open(self) -> None:
        """Test that circuit closes on success in HALF_OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.01)
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))
        success_func = AsyncMock(return_value="success")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        breaker._last_failure_time = time.monotonic() - 0.02

        # Successful call should close the circuit
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_reopens_on_failure_in_half_open(self) -> None:
        """Test that circuit reopens on failure in HALF_OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.01)
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        breaker._last_failure_time = time.monotonic() - 0.02

        # Failed call in HALF_OPEN should reopen the circuit
        with pytest.raises(Exception, match="Service error"):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN


class TestHalfOpenCallLimiting:
    """Tests for half-open call limiting behavior."""

    @pytest.mark.asyncio
    async def test_half_open_limits_concurrent_calls(self) -> None:
        """Test that half-open state limits the number of test calls."""
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0.01, half_open_max_calls=1
        )
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout to transition to HALF_OPEN
        breaker._last_failure_time = time.monotonic() - 0.02

        # First call in half-open should be allowed (transitions state)
        # But it will fail because we're using failing_func
        with pytest.raises(Exception, match="Service error"):
            await breaker.call(failing_func)

        # Circuit reopened due to failure
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_rejects_excess_calls(self) -> None:
        """Test that excess calls in half-open state are rejected."""
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0.01, half_open_max_calls=1
        )
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        # Manually set to half-open with 1 call already made
        breaker._state = CircuitState.HALF_OPEN
        breaker._half_open_calls = 1

        # Next call should be rejected since max_calls (1) already made
        with pytest.raises(CircuitOpenError, match="max half-open calls reached"):
            await breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_half_open_calls_reset_on_transition(self) -> None:
        """Test that half-open calls counter resets on state transition."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.01)
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        # Set some half-open calls
        breaker._half_open_calls = 5

        # Wait for recovery timeout
        breaker._last_failure_time = time.monotonic() - 0.02

        # Trigger state transition check by making a call
        with pytest.raises(Exception, match="Service error"):
            await breaker.call(failing_func)

        # After transitioning to half-open and then back to open,
        # we verify the counter was reset during the HALF_OPEN transition
        # (this is implicit - if it wasn't reset, the call would have been rejected)


class TestCircuitOpenError:
    """Tests for CircuitOpenError exception."""

    @pytest.mark.asyncio
    async def test_circuit_open_error_raised_when_circuit_is_open(self) -> None:
        """Test that CircuitOpenError is raised when circuit is OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))
        success_func = AsyncMock(return_value="success")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Subsequent calls should raise CircuitOpenError
        with pytest.raises(CircuitOpenError, match="Circuit breaker is open"):
            await breaker.call(success_func)

        # The success function should not have been called
        success_func.assert_not_called()


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.half_open_max_calls == 1

    def test_custom_values(self) -> None:
        """Test that custom values can be set."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=60.0,
            half_open_max_calls=3,
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 60.0
        assert config.half_open_max_calls == 3


class TestCircuitBreakerReset:
    """Tests for circuit breaker reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_restores_initial_state(self) -> None:
        """Test that reset() restores the circuit breaker to initial state."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config=config)

        failing_func = AsyncMock(side_effect=Exception("Service error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception, match="Service error"):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Reset the circuit
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._last_failure_time == 0.0
        assert breaker._half_open_calls == 0
