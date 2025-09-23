"""Error handling registration for FastAPI.

Provides `register_exception_handlers(app)` referenced by `app.main`.
For tests, we attach a few generic handlers mapping exceptions to JSON responses.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc) or "Internal Server Error",
            },
        )
