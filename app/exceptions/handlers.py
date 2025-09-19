"""
Exception handlers for FastAPI application.

This module provides exception handlers that convert various types of exceptions
into RFC 9457 Problem Details responses.
"""
import logging
from typing import Any, Dict, Optional, Type, TypeVar

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import (
    Problem,
    ValidationProblem,
    UnauthorizedProblem,
    ForbiddenProblem,
    NotFoundProblem,
    ConflictProblem,
    TooManyRequestsProblem,
    InternalServerErrorProblem,
)

logger = logging.getLogger(__name__)

# Type variable for generic problem type
ProblemTypeT = TypeVar("ProblemTypeT", bound=Problem)

# Default base URL for problem types
DEFAULT_PROBLEM_BASE_URL = "https://example.com/probs/"


def create_problem_response(
    problem: Problem,
    status_code: int,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """Create a JSON response for a problem.

    Args:
        problem: The problem details object
        status_code: The HTTP status code
        headers: Additional headers to include in the response

    Returns:
        JSONResponse: The problem details response
    """
    if headers is None:
        headers = {}

    # Set the Content-Type header for problem details
    headers["Content-Type"] = "application/problem+json"

    # Convert the problem to a dictionary and remove None values
    problem_dict = problem.model_dump(
        exclude_none=True, by_alias=True, exclude_unset=True
    )

    return JSONResponse(
        status_code=status_code,
        content=problem_dict,
        headers=headers,
    )


def create_problem(
    problem_type: Type[ProblemTypeT],
    detail: str,
    status_code: int,
    instance: Optional[str] = None,
    **kwargs: Any,
) -> JSONResponse:
    """Create a problem response from a problem type.

    Args:
        problem_type: The problem type class
        detail: A human-readable explanation of the problem
        status_code: The HTTP status code
        instance: A URI reference that identifies the specific occurrence of the problem
        **kwargs: Additional fields to include in the problem

    Returns:
        JSONResponse: The problem details response
    """
    problem = problem_type(
        detail=detail,
        instance=instance,
        **kwargs,
    )
    
    # Ensure status is set correctly
    problem.status = status_code
    
    return create_problem_response(problem, status_code=status_code)


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle HTTP exceptions and convert them to problem details.

    Args:
        request: The request that caused the exception
        exc: The HTTP exception

    Returns:
        JSONResponse: The problem details response
    """
    # Get the problem type based on the status code
    problem_type: Type[Problem]
    
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        problem_type = ValidationProblem
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        problem_type = UnauthorizedProblem
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        problem_type = ForbiddenProblem
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        problem_type = NotFoundProblem
    elif exc.status_code == status.HTTP_409_CONFLICT:
        problem_type = ConflictProblem
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        problem_type = TooManyRequestsProblem
    elif exc.status_code >= 500:
        problem_type = InternalServerErrorProblem
    else:
        # Default to base Problem for other status codes
        problem_type = Problem

    # Create the problem response
    return create_problem(
        problem_type=problem_type,
        detail=exc.detail if hasattr(exc, "detail") else str(exc),
        status_code=exc.status_code,
        instance=request.url.path,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors and convert them to problem details.

    Args:
        request: The request that caused the exception
        exc: The validation exception

    Returns:
        JSONResponse: The problem details response with validation errors
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        # Get the location of the error (body, query, path, etc.)
        loc = ".".join(str(loc) for loc in error["loc"])
        
        # Create a structured error object
        error_info = {
            "field": loc,
            "message": error["msg"],
            "type": error["type"],
        }
        
        # Add context if available
        if "ctx" in error:
            error_info["context"] = error["ctx"]
            
        errors.append(error_info)

    # Create a validation problem
    problem = ValidationProblem(
        detail="One or more validation errors occurred",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        instance=request.url.path,
        errors=errors,
    )

    return create_problem_response(
        problem,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def python_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unhandled Python exceptions and convert them to problem details.

    Args:
        request: The request that caused the exception
        exc: The exception

    Returns:
        JSONResponse: The problem details response
    """
    # Log the full exception
    logger.exception(
        "Unhandled exception occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=exc,
    )

    # Create an internal server error problem
    problem = InternalServerErrorProblem(
        detail="An unexpected error occurred",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        instance=request.url.path,
    )

    return create_problem_response(
        problem,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the FastAPI application.

    Args:
        app: The FastAPI application
    """
    # Register the handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, python_exception_handler)
    
    logger.info("Registered exception handlers")
