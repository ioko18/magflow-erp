"""Response compression middleware for FastAPI."""

import gzip
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware to compress HTTP responses using gzip."""

    def __init__(
        self,
        app: Callable,
        minimum_size: int = 1024,  # Only compress responses larger than 1KB
        compress_types: set = None,
    ):
        """Initialize compression middleware.

        Args:
            app: The FastAPI application
            minimum_size: Minimum response size to compress (bytes)
            compress_types: Set of content types to compress

        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compress_types = compress_types or {
            "text/plain",
            "text/html",
            "text/css",
            "text/javascript",
            "application/json",
            "application/xml",
            "application/javascript",
            "text/xml",
            "application/octet-stream",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and compress response if applicable."""
        response = await call_next(request)

        # Skip compression for non-GET requests or responses that are already compressed
        if (
            request.method != "GET"
            or response.headers.get("content-encoding")
            or response.headers.get("transfer-encoding") == "chunked"
            or not hasattr(response, "body")
        ):
            return response

        # Get response body
        if isinstance(response, StreamingResponse):
            # For streaming responses, we can't easily compress
            return response

        body = b""
        if hasattr(response, "body"):
            body = response.body

        # Skip compression for small responses
        if len(body) < self.minimum_size:
            return response

        # Check content type
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type not in self.compress_types:
            return response

        # Compress the response
        try:
            compressed_body = gzip.compress(body)

            # Update response
            response.body = compressed_body
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed_body))

            # Add Vary header to indicate compression
            existing_vary = response.headers.get("Vary", "")
            if existing_vary:
                if "Accept-Encoding" not in existing_vary:
                    response.headers["Vary"] = f"{existing_vary}, Accept-Encoding"
            else:
                response.headers["Vary"] = "Accept-Encoding"

            logger.debug(
                f"Compressed response: {len(body)} -> {len(compressed_body)} bytes "
                f"({content_type})",
            )

        except Exception as e:
            logger.warning(f"Failed to compress response: {e!s}")
            # Return original response if compression fails
            return response

        return response
