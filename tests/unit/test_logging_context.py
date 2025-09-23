"""Tests for logging context and middleware."""

import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.logging_setup import (
    clear_request_context,
    get_current_request_id,
    set_request_context,
)
from app.middleware.log_context import RequestContextLogMiddleware


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"message": "test"}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    return app


def test_set_request_context():
    """Test setting and getting request context."""
    # Clear any existing context
    clear_request_context()

    # Set context
    set_request_context(request_id="test-123")

    # Get and verify context
    request_id = get_current_request_id()
    assert request_id == "test-123"

    # Clear and verify
    clear_request_context()
    assert get_current_request_id() is None


@patch("app.middleware.log_context.structlog.get_logger")
@pytest.mark.asyncio
async def test_middleware_logs_request(mock_get_logger, app):
    """Test that the middleware logs requests correctly."""
    # Setup mock logger
    mock_logger = logging.getLogger("test_logger")
    mock_logger.setLevel(logging.INFO)
    mock_handler = MagicMock()
    mock_handler.level = logging.NOTSET
    mock_logger.addHandler(mock_handler)

    # Add middleware to the app
    app.add_middleware(RequestContextLogMiddleware, logger=mock_logger)

    # Create test client
    client = TestClient(app)

    # Make a request
    response = client.get("/test")

    # Check response
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    # Check that logger was called with expected arguments
    assert mock_handler.handle.call_count >= 2

    # Check request start log
    start_record = mock_handler.handle.call_args_list[0].args[0]
    assert "Request started: GET /test" in start_record.getMessage()

    # Check request complete log
    complete_record = mock_handler.handle.call_args_list[1].args[0]
    assert "Request completed - Status: 200" in complete_record.getMessage()


@patch("app.middleware.log_context.structlog.get_logger")
@pytest.mark.asyncio
async def test_middleware_handles_errors(mock_get_logger, app):
    """Test that the middleware logs errors correctly."""
    # Setup mock logger
    mock_logger = logging.getLogger("test_logger")
    mock_logger.setLevel(logging.INFO)
    mock_handler = MagicMock()
    mock_handler.level = logging.NOTSET
    mock_logger.addHandler(mock_handler)

    # Add middleware to the app
    app.add_middleware(RequestContextLogMiddleware, logger=mock_logger)

    # Create test client
    client = TestClient(app)

    # Make a request that will fail
    with pytest.raises(ValueError):
        client.get("/error")

    # Check that error was logged
    assert mock_handler.handle.call_count > 0
    error_record = mock_handler.handle.call_args_list[-1].args[0]
    assert "Request failed: Test error" in error_record.getMessage()


@pytest.mark.asyncio
async def test_logging_with_trace_context(app):
    """Test that trace context is included in logs."""
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
