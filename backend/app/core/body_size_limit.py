"""
CogniCompanion — Request Size Limiter Middleware
=================================================
Mitigates Buffer Overflow, Resource Starvation, and Denial of Service (DoS)
attacks caused by abnormally large payload uploads.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

DEFAULT_MAX_BODY_SIZE = 15 * 1024 * 1024       # 15 MB
UPLOAD_MAX_BODY_SIZE = 25 * 1024 * 1024        # 25 MB for media/audio uploads


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                max_size = (
                    UPLOAD_MAX_BODY_SIZE
                    if "/media" in request.url.path or "/voice" in request.url.path
                    else DEFAULT_MAX_BODY_SIZE
                )
                if length > max_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Payload too large. Maximum allowed size is {max_size // (1024 * 1024)} MB."
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
