"""
Rate limiter for Claude API calls using token bucket algorithm.

Prevents hitting API rate limits while maximizing throughput.
Configurable via environment variables:
- CLAUDE_REQUESTS_PER_MINUTE (default: 50)
- CLAUDE_TOKENS_PER_MINUTE (default: 100000)
- CLAUDE_MAX_CONCURRENT (default: 10)
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import time
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 50
    tokens_per_minute: int = 100000
    max_concurrent: int = 10
    retry_after_seconds: int = 60
    backoff_multiplier: float = 1.5
    max_backoff_seconds: int = 300

    @classmethod
    def from_env(cls) -> 'RateLimitConfig':
        """Create config from environment variables."""
        return cls(
            requests_per_minute=int(os.environ.get("CLAUDE_REQUESTS_PER_MINUTE", "50")),
            tokens_per_minute=int(os.environ.get("CLAUDE_TOKENS_PER_MINUTE", "100000")),
            max_concurrent=int(os.environ.get("CLAUDE_MAX_CONCURRENT", "10")),
            retry_after_seconds=int(os.environ.get("CLAUDE_RETRY_AFTER_SECONDS", "60")),
            backoff_multiplier=float(os.environ.get("CLAUDE_BACKOFF_MULTIPLIER", "1.5")),
            max_backoff_seconds=int(os.environ.get("CLAUDE_MAX_BACKOFF_SECONDS", "300"))
        )


class TokenBucket:
    """
    Token bucket rate limiter.
    Allows bursting while maintaining average rate.
    """

    def __init__(self, rate: float, capacity: float):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()

    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def acquire(self, tokens: float = 1, blocking: bool = True, timeout: float = None) -> bool:
        """
        Attempt to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire
            blocking: If True, wait for tokens; if False, return immediately
            timeout: Maximum time to wait (if blocking)

        Returns:
            True if tokens acquired, False otherwise
        """
        start_time = time.time()

        while True:
            with self.lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                if not blocking:
                    return False

                # Calculate wait time for tokens to become available
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False
                wait_time = min(wait_time, timeout - elapsed)

            # Wait a bit before trying again
            time.sleep(min(wait_time, 0.1))

    def try_acquire(self, tokens: float = 1) -> bool:
        """Non-blocking attempt to acquire tokens."""
        return self.acquire(tokens, blocking=False)

    def available(self) -> float:
        """Get current available tokens."""
        with self.lock:
            self._refill()
            return self.tokens

    def time_until_available(self, tokens: float) -> float:
        """Get time in seconds until specified tokens are available."""
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                return 0
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.rate


class RateLimiter:
    """
    Composite rate limiter for Claude API.
    Manages both request rate and token rate limits.
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig.from_env()

        # Request rate bucket (requests per minute)
        self.request_bucket = TokenBucket(
            rate=self.config.requests_per_minute / 60.0,
            capacity=self.config.requests_per_minute
        )

        # Token rate bucket (tokens per minute)
        self.token_bucket = TokenBucket(
            rate=self.config.tokens_per_minute / 60.0,
            capacity=self.config.tokens_per_minute
        )

        # Concurrent request semaphore
        self.concurrent_semaphore = threading.Semaphore(self.config.max_concurrent)
        self.concurrent_count = 0
        self.concurrent_lock = threading.Lock()

        # Backoff tracking
        self.backoff_until: Optional[datetime] = None
        self.consecutive_errors = 0
        self.total_requests = 0
        self.total_tokens_used = 0
        self.rate_limit_hits = 0
        self.lock = threading.Lock()

        logger.info(f"Rate limiter initialized: {self.config.requests_per_minute} req/min, "
                   f"{self.config.tokens_per_minute} tokens/min, "
                   f"{self.config.max_concurrent} concurrent")

    def acquire(self, estimated_tokens: int = 1000, timeout: float = 300) -> bool:
        """
        Acquire permission to make an API request.

        Args:
            estimated_tokens: Estimated tokens for this request
            timeout: Maximum time to wait

        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()

        # Check backoff
        with self.lock:
            if self.backoff_until and datetime.utcnow() < self.backoff_until:
                wait_time = (self.backoff_until - datetime.utcnow()).total_seconds()
                if wait_time > timeout:
                    logger.warning(f"Backoff period ({wait_time:.1f}s) exceeds timeout ({timeout}s)")
                    return False
                logger.info(f"Rate limit backoff: waiting {wait_time:.1f}s")
                time.sleep(wait_time)

        remaining_timeout = timeout - (time.time() - start_time)
        if remaining_timeout <= 0:
            return False

        # Acquire concurrent slot
        if not self.concurrent_semaphore.acquire(timeout=remaining_timeout):
            logger.warning("Timeout waiting for concurrent slot")
            return False

        with self.concurrent_lock:
            self.concurrent_count += 1

        remaining_timeout = timeout - (time.time() - start_time)
        if remaining_timeout <= 0:
            self._release_concurrent()
            return False

        # Acquire request token
        if not self.request_bucket.acquire(1, blocking=True, timeout=remaining_timeout):
            logger.warning("Timeout waiting for request rate limit")
            self._release_concurrent()
            return False

        remaining_timeout = timeout - (time.time() - start_time)
        if remaining_timeout <= 0:
            self._release_concurrent()
            return False

        # Acquire token budget
        if not self.token_bucket.acquire(estimated_tokens, blocking=True, timeout=remaining_timeout):
            logger.warning("Timeout waiting for token rate limit")
            self._release_concurrent()
            return False

        with self.lock:
            self.total_requests += 1

        return True

    def _release_concurrent(self):
        """Release concurrent slot."""
        with self.concurrent_lock:
            self.concurrent_count -= 1
        self.concurrent_semaphore.release()

    def release(self, actual_tokens: int = 0):
        """
        Release concurrent request slot after request completes.

        Args:
            actual_tokens: Actual tokens used (for tracking)
        """
        self._release_concurrent()

        if actual_tokens > 0:
            with self.lock:
                self.total_tokens_used += actual_tokens

    def report_success(self):
        """Report successful request - reset error tracking."""
        with self.lock:
            self.consecutive_errors = 0

    def report_rate_limit_error(self, retry_after: int = None):
        """Report 429 rate limit error - trigger backoff."""
        with self.lock:
            self.consecutive_errors += 1
            self.rate_limit_hits += 1

            # Calculate backoff time
            if retry_after:
                backoff_seconds = retry_after
            else:
                backoff_seconds = self.config.retry_after_seconds * (
                    self.config.backoff_multiplier ** (self.consecutive_errors - 1)
                )

            # Cap backoff
            backoff_seconds = min(backoff_seconds, self.config.max_backoff_seconds)

            self.backoff_until = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            logger.warning(f"Rate limit hit #{self.rate_limit_hits}. "
                          f"Backing off for {backoff_seconds:.1f}s "
                          f"(consecutive errors: {self.consecutive_errors})")

    def report_error(self):
        """Report other error - increment error count but don't trigger full backoff."""
        with self.lock:
            self.consecutive_errors += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        with self.lock:
            in_backoff = self.backoff_until and datetime.utcnow() < self.backoff_until
            backoff_remaining = 0
            if in_backoff:
                backoff_remaining = (self.backoff_until - datetime.utcnow()).total_seconds()

            return {
                'request_tokens_available': self.request_bucket.available(),
                'api_tokens_available': self.token_bucket.available(),
                'concurrent_available': self.config.max_concurrent - self.concurrent_count,
                'concurrent_in_use': self.concurrent_count,
                'consecutive_errors': self.consecutive_errors,
                'in_backoff': in_backoff,
                'backoff_remaining_seconds': backoff_remaining,
                'total_requests': self.total_requests,
                'total_tokens_used': self.total_tokens_used,
                'rate_limit_hits': self.rate_limit_hits,
                'config': {
                    'requests_per_minute': self.config.requests_per_minute,
                    'tokens_per_minute': self.config.tokens_per_minute,
                    'max_concurrent': self.config.max_concurrent
                }
            }

    def wait_for_capacity(self, estimated_tokens: int = 1000) -> float:
        """
        Get estimated wait time for capacity.

        Returns:
            Estimated seconds until capacity is available
        """
        request_wait = self.request_bucket.time_until_available(1)
        token_wait = self.token_bucket.time_until_available(estimated_tokens)

        # Check backoff
        backoff_wait = 0
        with self.lock:
            if self.backoff_until and datetime.utcnow() < self.backoff_until:
                backoff_wait = (self.backoff_until - datetime.utcnow()).total_seconds()

        return max(request_wait, token_wait, backoff_wait)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter(config: RateLimitConfig = None) -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    with _rate_limiter_lock:
        if _rate_limiter is None:
            _rate_limiter = RateLimiter(config)
        return _rate_limiter


def reset_rate_limiter(config: RateLimitConfig = None):
    """Reset the global rate limiter (useful for testing)."""
    global _rate_limiter
    with _rate_limiter_lock:
        _rate_limiter = RateLimiter(config) if config else None


class RateLimitedContext:
    """
    Context manager for rate-limited API calls.

    Usage:
        with RateLimitedContext(estimated_tokens=2000) as ctx:
            if ctx.acquired:
                result = make_api_call()
                ctx.report_tokens(result.usage.total_tokens)
    """

    def __init__(self, estimated_tokens: int = 1000, timeout: float = 300):
        self.estimated_tokens = estimated_tokens
        self.timeout = timeout
        self.rate_limiter = get_rate_limiter()
        self.acquired = False
        self.actual_tokens = 0

    def __enter__(self) -> 'RateLimitedContext':
        self.acquired = self.rate_limiter.acquire(
            estimated_tokens=self.estimated_tokens,
            timeout=self.timeout
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.rate_limiter.release(self.actual_tokens)

            if exc_type is None:
                self.rate_limiter.report_success()
            elif '429' in str(exc_val) or 'rate limit' in str(exc_val).lower():
                self.rate_limiter.report_rate_limit_error()
            else:
                self.rate_limiter.report_error()

        return False  # Don't suppress exceptions

    def report_tokens(self, tokens: int):
        """Report actual tokens used."""
        self.actual_tokens = tokens
