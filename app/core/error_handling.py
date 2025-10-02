"""Error handling registration for FastAPI.

Provides `register_exception_handlers(app)` referenced by `app.main`.
For tests, we attach a few generic handlers mapping exceptions to JSON responses.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.problem import Problem
from app.middleware.correlation_id import get_correlation_id

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = get_correlation_id()
        problem = Problem.from_validation_errors(
            errors=exc.errors(),
            instance=str(request.url),
            trace_id=correlation_id,
            correlation_id=correlation_id,
        )
        headers = {}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return JSONResponse(
            status_code=problem.status or status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=problem.to_dict(),
            headers=headers,
            media_type="application/problem+json",
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        correlation_id = get_correlation_id()
        problem = Problem.from_status(
            status_code=exc.status_code,
            detail=exc.detail if isinstance(exc.detail, str) else None,
            instance=str(request.url),
            trace_id=correlation_id,
            correlation_id=correlation_id,
        )

        # Merge additional detail if provided as dict for RFC compliance
        if isinstance(exc.detail, dict):
            problem_dict = problem.to_dict()
            problem_dict.update(exc.detail)
        else:
            problem_dict = problem.to_dict()

        headers = getattr(exc, "headers", None) or {}
        if correlation_id:
            headers.setdefault("X-Correlation-ID", correlation_id)
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            headers.setdefault("WWW-Authenticate", 'Bearer realm="api"')

        return JSONResponse(
            status_code=problem.status or exc.status_code,
            content=problem_dict,
            headers=headers,
            media_type="application/problem+json",
        )

    # Ensure Starlette raises use the same handler (e.g. 404 from router resolution)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        correlation_id = get_correlation_id()

        # Log the full exception with traceback
        logger.error(
            f"Unhandled exception in {request.method} {request.url.path}: {exc}",
            exc_info=True,
            extra={"correlation_id": correlation_id}
        )

        problem = Problem.from_exception(
            exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            instance=str(request.url),
            trace_id=correlation_id,
            correlation_id=correlation_id,
        )
        headers = {}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem.to_dict(),
            headers=headers,
            media_type="application/problem+json",
        )
