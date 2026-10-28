from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Expected application error rendered with a stable error envelope."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class BadRequestError(AppError):
    def __init__(self, message: str, code: str = "BAD_REQUEST", details: Any | None = None):
        super().__init__(status.HTTP_400_BAD_REQUEST, code, message, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required", code: str = "UNAUTHORIZED"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, code, message)


class ForbiddenError(AppError):
    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        code: str = "FORBIDDEN",
    ):
        super().__init__(status.HTTP_403_FORBIDDEN, code, message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(status.HTTP_404_NOT_FOUND, code, message)


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "CONFLICT", details: Any | None = None):
        super().__init__(status.HTTP_409_CONFLICT, code, message, details)


class UnprocessableError(AppError):
    def __init__(self, message: str, code: str = "UNPROCESSABLE", details: Any | None = None):
        super().__init__(status.HTTP_422_UNPROCESSABLE_CONTENT, code, message, details)


class RateLimitError(AppError):
    def __init__(self, message: str = "Too many attempts. Please try again later."):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMITED", message)


class PayloadTooLargeError(AppError):
    def __init__(self, message: str = "The uploaded file is too large"):
        super().__init__(413, "FILE_TOO_LARGE", message)


class UnsupportedMediaTypeError(AppError):
    def __init__(self, message: str = "This file type is not allowed"):
        super().__init__(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_FILE_TYPE", message)


def error_body(
    code: str,
    message: str,
    details: Any | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    if request_id:
        body["error"]["request_id"] = request_id
    return body


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details, _request_id(request)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = []
        for item in exc.errors():
            details.append(
                {
                    "field": ".".join(str(part) for part in item.get("loc", []) if part != "body"),
                    "message": item.get("msg", "Invalid value"),
                    "type": item.get("type"),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_body(
                "VALIDATION_ERROR",
                "The submitted data is invalid",
                details,
                _request_id(request),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail) if exc.detail else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, message, None, _request_id(request)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled application error",
            extra={"request_id": _request_id(request), "path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                None,
                _request_id(request),
            ),
        )
