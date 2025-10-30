"""
Rate limiting module for REV2.
Implements per-installation rate limiting to prevent abuse.
"""

import time
import os
from typing import Dict, Tuple, Any


class RateLimiter:
    """
    Simple in-memory rate limiter for per-installation webhook processing.
    Can be extended to use Redis for distributed systems.
    """

    def __init__(
        self,
        max_reviews_per_hour: int = 100,
        cleanup_interval: int = 3600,
    ):
        """
        Initialize rate limiter.

        Args:
            max_reviews_per_hour: Maximum reviews allowed per hour per installation
            cleanup_interval: Cleanup interval in seconds (default: 1 hour)
        """
        self.max_reviews_per_hour = max_reviews_per_hour
        self.cleanup_interval = cleanup_interval

        # Format: {installation_id: [(timestamp1, count1), (timestamp2, count2), ...]}
        self.records: Dict[str, list] = {}
        self.last_cleanup = time.time()

    def _cleanup(self):
        """Remove old records outside the 1-hour window."""
        current_time = time.time()

        # Only cleanup if interval has passed
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        one_hour_ago = current_time - 3600

        for installation_id in list(self.records.keys()):
            # Keep only records from the last hour
            self.records[installation_id] = [
                (timestamp, count)
                for timestamp, count in self.records[installation_id]
                if timestamp > one_hour_ago
            ]

            # Remove installation if no records left
            if not self.records[installation_id]:
                del self.records[installation_id]

        self.last_cleanup = current_time

    def _get_count_in_window(self, installation_id: str) -> int:
        """Get total review count for installation in the last hour."""
        if installation_id not in self.records:
            return 0

        current_time = time.time()
        one_hour_ago = current_time - 3600

        total = 0
        for timestamp, count in self.records[installation_id]:
            if timestamp > one_hour_ago:
                total += count

        return total

    def check_limit(
        self, installation_id: str, increment: int = 1
    ) -> Tuple[bool, int]:
        """
        Check if installation has exceeded rate limit.

        Args:
            installation_id: GitHub installation ID
            increment: Number of reviews to increment (default: 1)

        Returns:
            Tuple of (is_allowed: bool, current_count: int)
            - is_allowed: True if under limit, False if exceeded
            - current_count: Current count in window
        """
        self._cleanup()

        current_time = time.time()
        current_count = self._get_count_in_window(installation_id)

        if current_count + increment > self.max_reviews_per_hour:
            # Exceeded limit
            return False, current_count

        # Under limit, increment
        if installation_id not in self.records:
            self.records[installation_id] = []

        self.records[installation_id].append((current_time, increment))

        return True, current_count + increment

    def get_status(self, installation_id: str) -> Dict[str, any]:
        """
        Get rate limit status for installation.

        Args:
            installation_id: GitHub installation ID

        Returns:
            Dict with current count, limit, and remaining
        """
        self._cleanup()

        current_count = self._get_count_in_window(installation_id)
        remaining = max(0, self.max_reviews_per_hour - current_count)

        return {
            "installation_id": installation_id,
            "current_count": current_count,
            "limit": self.max_reviews_per_hour,
            "remaining": remaining,
            "window_seconds": 3600,
        }

    def reset(self, installation_id: str):
        """Reset rate limit for installation (for testing or manual reset)."""
        if installation_id in self.records:
            del self.records[installation_id]


# Global rate limiter instance
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        max_reviews = int(os.getenv("RATE_LIMIT_REVIEWS_PER_HOUR", 100))
        _rate_limiter = RateLimiter(max_reviews_per_hour=max_reviews)
    return _rate_limiter
