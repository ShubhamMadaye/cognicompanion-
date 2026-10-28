"""
CogniCompanion — Security Headers Middleware
=============================================
Enforces defense-in-depth HTTP response headers against:
  - Clickjacking (X-Frame-Options: DENY, frame-ancestors 'none')
  - MIME-type sniffing (X-Content-Type-Options: nosniff)
  - XSS attacks (Content-Security-Policy, X-XSS-Protection)
  - Man-in-the-Middle (Strict-Transport-Security in HTTPS/production)
  - Feature access abuse (Permissions-Policy)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 1. Anti-clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # 2. Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 3. Legacy XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Strict referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Device capability restrictions (microphone only for voice assistant, no camera/geolocation)
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"

        # 6. Environment-aware Content Security Policy (compatible with Vite/React frontend)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https:; "
            "media-src 'self' blob: data:; "
            "connect-src 'self' http://localhost:* ws://localhost:* https://*.googleapis.com; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # 7. Environment-aware HSTS (HTTPS only in production to prevent breaking localhost)
        is_https = (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto") == "https"
            or self.settings.APP_ENV.lower() == "production"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
