"""One error envelope for every non-2xx response.

    {"error": {"code": "not_found", "message": "Product 42 not found", "details": null}}

``code`` is a stable machine-readable string the frontend can switch on;
``message`` is for humans; ``details`` carries field-level validation info.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("pricematch")


class ApiError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: Any = None, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(ApiError):
    status_code = 404
    code = "not_found"


class ServiceUnavailableError(ApiError):
    status_code = 503
    code = "service_unavailable"


def error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
    503: "service_unavailable",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(p) for p in err.get("loc", ()) if p not in ("query", "path", "body")),
                "in": err.get("loc", ("",))[0],
                "message": err.get("msg"),
                "type": err.get("type"),
            }
            for err in exc.errors()
        ]
        return error_response(422, "validation_error", "Request validation failed", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else code.replace("_", " ")
        return error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error", exc_info=exc)
        return error_response(500, "internal_error", "Internal server error")
