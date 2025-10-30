"""
Tests for rate limiting module.
"""

import pytest
import time
from backend.rate_limiter import RateLimiter, get_rate_limiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_initialization(self):
        """RateLimiter should initialize with correct settings."""
        limiter = RateLimiter(max_reviews_per_hour=50)
        assert limiter.max_reviews_per_hour == 50

    def test_check_limit_under_limit(self):
        """Should allow reviews under limit."""
        limiter = RateLimiter(max_reviews_per_hour=5)
        is_allowed, count = limiter.check_limit("install-1")
        assert is_allowed is True
        assert count == 1

    def test_check_limit_multiple_reviews(self):
        """Should track multiple reviews correctly."""
        limiter = RateLimiter(max_reviews_per_hour=5)
        for i in range(3):
            is_allowed, count = limiter.check_limit("install-1")
            assert is_allowed is True
            assert count == i + 1

    def test_check_limit_exceeds_limit(self):
        """Should block reviews exceeding limit."""
        limiter = RateLimiter(max_reviews_per_hour=3)
        # Use up the limit
        for i in range(3):
            limiter.check_limit("install-1")
        # Fourth should be blocked
        is_allowed, count = limiter.check_limit("install-1")
        assert is_allowed is False
        assert count == 3

    def test_separate_installations(self):
        """Different installations should have separate limits."""
        limiter = RateLimiter(max_reviews_per_hour=2)
        # Install 1: use 2 reviews
        for i in range(2):
            limiter.check_limit("install-1")
        # Install 2: should still have capacity
        is_allowed, count = limiter.check_limit("install-2")
        assert is_allowed is True
        assert count == 1

    def test_get_status(self):
        """Should return correct status."""
        limiter = RateLimiter(max_reviews_per_hour=10)
        limiter.check_limit("install-1")
        limiter.check_limit("install-1")

        status = limiter.get_status("install-1")
        assert status["installation_id"] == "install-1"
        assert status["current_count"] == 2
        assert status["limit"] == 10
        assert status["remaining"] == 8

    def test_get_status_no_reviews(self):
        """Should return correct status when no reviews recorded."""
        limiter = RateLimiter(max_reviews_per_hour=10)

        status = limiter.get_status("install-new")
        assert status["current_count"] == 0
        assert status["remaining"] == 10

    def test_reset(self):
        """Should reset limit for installation."""
        limiter = RateLimiter(max_reviews_per_hour=5)
        limiter.check_limit("install-1")
        limiter.check_limit("install-1")

        # Reset
        limiter.reset("install-1")

        # Should be able to use limit again
        is_allowed, count = limiter.check_limit("install-1")
        assert is_allowed is True
        assert count == 1

    def test_cleanup_old_records(self):
        """Should cleanup records outside the window."""
        limiter = RateLimiter(
            max_reviews_per_hour=10,
            cleanup_interval=0,  # Always cleanup
        )
        current_time = time.time()

        # Manually add an old record (more than 1 hour ago)
        if "install-1" not in limiter.records:
            limiter.records["install-1"] = []
        limiter.records["install-1"].append((current_time - 7200, 1))  # 2 hours ago

        # Add recent record
        limiter.records["install-1"].append((current_time, 1))

        # Trigger cleanup
        limiter._cleanup()

        # Old record should be gone
        count = limiter._get_count_in_window("install-1")
        assert count == 1  # Only recent record

    def test_increment_parameter(self):
        """Should handle increment parameter."""
        limiter = RateLimiter(max_reviews_per_hour=10)
        is_allowed, count = limiter.check_limit("install-1", increment=5)
        assert is_allowed is True
        assert count == 5

    def test_increment_exceeds_limit(self):
        """Should block if increment exceeds limit."""
        limiter = RateLimiter(max_reviews_per_hour=10)
        is_allowed, count = limiter.check_limit("install-1", increment=15)
        assert is_allowed is False


class TestGlobalRateLimiter:
    """Tests for global rate limiter singleton."""

    def test_get_rate_limiter(self):
        """get_rate_limiter should return RateLimiter instance."""
        limiter = get_rate_limiter()
        assert isinstance(limiter, RateLimiter)

    def test_global_limiter_singleton(self):
        """Multiple calls should return same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2
