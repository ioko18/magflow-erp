"""
FastAPI middleware for collecting HTTP metrics with OpenTelemetry.
"""
import time
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.http_metrics import (
    HTTP_SERVER_ACTIVE_REQUESTS,
    record_http_request,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting HTTP metrics."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip metrics for certain paths (health checks, metrics, etc.)
        if request.url.path in ["/health", "/metrics", "/favicon.ico"]:
            return await call_next(request)
        
        # Get route path (FastAPI route, not URL path)
        route = request.scope.get("route")
        route_path = route.path if route else request.url.path
        
        # Record request start time
        start_time = time.time()
        request_headers = dict(request.headers)
        
        # Get content length if available
        content_length = request_headers.get("content-length")
        request_size = int(content_length) if content_length else None
        
        # Track active requests
        HTTP_SERVER_ACTIVE_REQUESTS.add(1, {
            "http.method": request.method,
            "http.route": route_path,
            "http.scheme": request.url.scheme,
            "http.host": request.url.hostname or "",
        })
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate request duration
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Get response size if available
            response_headers = dict(response.headers)
            content_length = response_headers.get("content-length")
            response_size = int(content_length) if content_length else None
            
            # Record the request metrics
            record_http_request(
                method=request.method,
                route=route_path,
                status_code=response.status_code,
                duration_ms=process_time,
                request_size=request_size,
                response_size=response_size,
            )
            
            return response
            
        except Exception as e:
            # Calculate process time even if an error occurs
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Record the failed request
            record_http_request(
                method=request.method,
                route=route_path,
                status_code=500,  # Internal Server Error
                duration_ms=process_time,
                request_size=request_size,
            )
            
            # Re-raise the exception to be handled by FastAPI's exception handlers
            raise
            
        finally:
            # Decrement active requests counter
            HTTP_SERVER_ACTIVE_REQUESTS.add(-1, {
                "http.method": request.method,
                "http.route": route_path,
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname or "",
            })
