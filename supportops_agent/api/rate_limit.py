"""Rate limiting middleware for FastAPI."""

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter using sliding window."""

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per client
        """
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        window_start = now - 60  # Last 60 seconds

        # Clean old requests
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id] if req_time > window_start
        ]

        # Check limit
        if len(self._requests[client_id]) >= self.requests_per_minute:
            return False

        # Record request
        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - 60

        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id] if req_time > window_start
        ]

        return max(0, self.requests_per_minute - len(self._requests[client_id]))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rate_limiter = RateLimiter(requests_per_minute)

    async def dispatch(self, request: Request, call_next: Callable):
        """Check rate limit before processing request."""
        # Get client identifier (IP address)
        client_id = request.client.host if request.client else "unknown"

        if not self.rate_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.rate_limiter.requests_per_minute} requests per minute.",
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        remaining = self.rate_limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
