"""Rate limiting for API calls.

This module provides rate limiting functionality to prevent abuse
and comply with API rate limits from external services.
"""

import time
import threading
from typing import Optional

from .constants import DEFAULT_RATE_LIMIT, BURST_RATE_LIMIT
from .logging_config import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter using token bucket algorithm.

    This implementation allows burst traffic up to the rate limit
    while enforcing an average rate over time.

    Attributes:
        calls_per_minute: Maximum calls allowed per minute
        burst_limit: Maximum calls allowed in 10 seconds
    """

    def __init__(
        self,
        calls_per_minute: int = DEFAULT_RATE_LIMIT,
        burst_limit: int = BURST_RATE_LIMIT
    ):
        """Initialize rate limiter.

        Args:
            calls_per_minute: Maximum API calls per minute (default 60)
            burst_limit: Maximum calls in 10 second window (default 10)
        """
        self.calls_per_minute = calls_per_minute
        self.burst_limit = burst_limit
        self.call_times: list[float] = []
        self.lock = threading.Lock()

        logger.debug(
            f"Rate limiter initialized: {calls_per_minute} calls/min, "
            f"burst limit {burst_limit}/10s"
        )

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded.

        This method blocks until it's safe to make another API call.
        Uses both per-minute and burst rate limits.

        Raises:
            RuntimeError: If rate limiting parameters are invalid
        """
        with self.lock:
            now = time.time()

            # Remove calls older than 1 minute for per-minute limit
            self.call_times = [t for t in self.call_times if now - t < 60]

            # Check burst limit (calls in last 10 seconds)
            recent_calls = [t for t in self.call_times if now - t < 10]

            # Wait if we've exceeded per-minute limit
            if len(self.call_times) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.call_times[0])
                if sleep_time > 0:
                    logger.debug(
                        f"Rate limit reached ({len(self.call_times)}/{self.calls_per_minute}), "
                        f"waiting {sleep_time:.2f}s"
                    )
                    time.sleep(sleep_time)
                    # Re-clean after sleeping
                    now = time.time()
                    self.call_times = [t for t in self.call_times if now - t < 60]

            # Wait if we've exceeded burst limit
            if len(recent_calls) >= self.burst_limit:
                sleep_time = 10 - (now - recent_calls[0])
                if sleep_time > 0:
                    logger.debug(
                        f"Burst limit reached ({len(recent_calls)}/{self.burst_limit}), "
                        f"waiting {sleep_time:.2f}s"
                    )
                    time.sleep(sleep_time)

            # Record this call
            self.call_times.append(time.time())

    def get_current_rate(self) -> tuple[int, int]:
        """Get current call rate.

        Returns:
            Tuple of (calls in last minute, calls in last 10 seconds)
        """
        with self.lock:
            now = time.time()
            minute_calls = len([t for t in self.call_times if now - t < 60])
            burst_calls = len([t for t in self.call_times if now - t < 10])
            return minute_calls, burst_calls

    def reset(self) -> None:
        """Reset rate limiter state.

        Useful for testing or when switching API endpoints.
        """
        with self.lock:
            self.call_times.clear()
            logger.debug("Rate limiter reset")


class RateLimiterManager:
    """Global manager for multiple rate limiters.

    Maintains separate rate limiters for different API endpoints
    to avoid one service affecting another.
    """

    def __init__(self):
        """Initialize rate limiter manager."""
        self._limiters: dict[str, RateLimiter] = {}
        self.lock = threading.Lock()

    def get_limiter(
        self,
        name: str,
        calls_per_minute: Optional[int] = None,
        burst_limit: Optional[int] = None
    ) -> RateLimiter:
        """Get or create a rate limiter for a named endpoint.

        Args:
            name: Identifier for the endpoint (e.g., 'nws', 'airnow', 'noaa')
            calls_per_minute: Optional custom rate limit
            burst_limit: Optional custom burst limit

        Returns:
            RateLimiter instance for the named endpoint
        """
        with self.lock:
            if name not in self._limiters:
                kwargs = {}
                if calls_per_minute is not None:
                    kwargs['calls_per_minute'] = calls_per_minute
                if burst_limit is not None:
                    kwargs['burst_limit'] = burst_limit

                self._limiters[name] = RateLimiter(**kwargs)
                logger.debug(f"Created rate limiter for '{name}'")

            return self._limiters[name]

    def reset_all(self) -> None:
        """Reset all rate limiters."""
        with self.lock:
            for limiter in self._limiters.values():
                limiter.reset()
            logger.debug("All rate limiters reset")


# Global instance
_rate_limiter_manager = RateLimiterManager()


def get_rate_limiter(
    name: str,
    calls_per_minute: Optional[int] = None,
    burst_limit: Optional[int] = None
) -> RateLimiter:
    """Get a rate limiter for a named endpoint.

    This is the main public API for accessing rate limiters.

    Args:
        name: Identifier for the endpoint (e.g., 'nws', 'airnow')
        calls_per_minute: Optional custom rate limit (default 60)
        burst_limit: Optional custom burst limit (default 10)

    Returns:
        RateLimiter instance

    Example:
        >>> limiter = get_rate_limiter('nws')
        >>> limiter.wait_if_needed()
        >>> # Make API call
    """
    return _rate_limiter_manager.get_limiter(name, calls_per_minute, burst_limit)
