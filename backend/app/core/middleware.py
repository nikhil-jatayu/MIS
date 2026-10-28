from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.errors import error_body

logger = logging.getLogger("app.requests")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds a request id, access logging, security headers and CSRF origin checks."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()

        if request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin and origin not in settings.allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content=error_body(
                        "ORIGIN_NOT_ALLOWED",
                        "Request origin is not allowed",
                        None,
                        request_id,
                    ),
                )

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Request failed",
                extra={"request_id": request_id, "path": request.url.path},
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s -> completed in %.1fms",
                request.method,
                request.url.path,
                duration_ms,
                extra={"request_id": request_id},
            )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
