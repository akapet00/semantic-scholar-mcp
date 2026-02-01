"""Circuit breaker pattern for API resilience."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from semantic_scholar_mcp.logging_config import get_logger

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
]

logger = get_logger("circuit_breaker")

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast, not making requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        recovery_timeout: Seconds before testing recovery.
        half_open_max_calls: Number of test calls in half-open state.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent hammering a failing service.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service considered down, requests fail immediately
    - HALF_OPEN: Testing if service recovered

    Attributes:
        config: CircuitBreakerConfig with behavior settings.
    """

    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _state: CircuitState = field(init=False, default=CircuitState.CLOSED)
    _failure_count: int = field(init=False, default=0)
    _last_failure_time: float = field(init=False, default=0.0)
    _half_open_calls: int = field(init=False, default=0)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    async def call[T](
        self,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func.

        Raises:
            CircuitOpenError: If circuit is open.
            Exception: Any exception from func (also recorded as failure).
        """
        async with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                raise CircuitOpenError("Circuit breaker is open. Service appears to be down.")

            # Track and limit calls in half-open state
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitOpenError(
                        "Circuit breaker: max half-open calls reached, waiting for result"
                    )
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception:
            await self._record_failure()
            raise

    def _check_state_transition(self) -> None:
        """Check if state should transition based on time."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.config.recovery_timeout:
                logger.info("Circuit breaker transitioning to HALF_OPEN after %.1fs", elapsed)
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker: test call succeeded, closing circuit")
                self._state = CircuitState.CLOSED
            self._failure_count = 0

    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker: test call failed, reopening circuit")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.config.failure_threshold:
                logger.warning(
                    "Circuit breaker: %d failures, opening circuit",
                    self._failure_count,
                )
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker to initial state (for testing)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
