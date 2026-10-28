"""
CogniCompanion — Rate Limiter Middleware
=========================================
Protects the application from brute-force authentication attacks,
credential stuffing, and AI endpoint abuse/DDoS.

Uses an in-memory sliding-window log per client IP address.
(Note: For multi-instance production deployments, configure a shared Redis store).
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiter:
    """Sliding-window in-memory rate limiter."""

    def __init__(self) -> None:
        # key: (client_ip, bucket) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def is_allowed(
        self, client_ip: str, bucket: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Returns (allowed, remaining, retry_after).
        """
        now = time.time()
        cutoff = now - window_seconds
        key = (client_ip, bucket)

        # Evict old entries
        valid_timestamps = [ts for ts in self._history[key] if ts > cutoff]
        self._history[key] = valid_timestamps

        current_count = len(valid_timestamps)
        if current_count >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            return False, 0, retry_after

        self._history[key].append(now)
        remaining = max_requests - (current_count + 1)
        return True, remaining, 0

    def clear(self) -> None:
        self._history.clear()


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        auth_limit: int = 15,
        ai_limit: int = 35,
        general_limit: int = 300,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.auth_limit = auth_limit
        self.ai_limit = ai_limit
        self.general_limit = general_limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Ignore static files and health checks
        if path.startswith("/uploads") or path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        # Determine client IP (handles standard proxies)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Categorize bucket
        if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register"):
            bucket = "auth"
            max_reqs = self.auth_limit
        elif path.startswith("/api/v1/voice"):
            bucket = "ai"
            max_reqs = self.ai_limit
        else:
            bucket = "general"
            max_reqs = self.general_limit

        allowed, remaining, retry_after = rate_limiter.is_allowed(
            client_ip=client_ip,
            bucket=bucket,
            max_requests=max_reqs,
            window_seconds=self.window_seconds,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down and try again.",
                    "bucket": bucket,
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_reqs),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_reqs)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
