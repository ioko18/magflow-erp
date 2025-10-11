"""Middleware for adding cache-related headers to responses."""

import hashlib

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware that adds Cache-Control and ETag headers to responses."""

    def __init__(
        self,
        app: ASGIApp,
        default_cache_control: str = "public, max-age=60",
        cacheable_methods: tuple = ("GET", "HEAD"),
        cacheable_status_codes: tuple = (200, 203, 300, 301, 302, 307, 404, 410),
        vary_headers: tuple = ("Accept", "Accept-Encoding"),
    ) -> None:
        super().__init__(app)
        self.default_cache_control = default_cache_control
        self.cacheable_methods = cacheable_methods
        self.cacheable_status_codes = cacheable_status_codes
        self.vary_headers = vary_headers

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Process the request
        response = await call_next(request)

        cache_status = getattr(request.state, "cache_status", None)

        # Skip if response already has cache headers
        if any(header in response.headers for header in ["Cache-Control", "ETag"]):
            if cache_status and "X-Cache-Status" not in response.headers:
                response.headers["X-Cache-Status"] = cache_status
            return response

        # Only cache successful GET/HEAD responses by default
        if (
            request.method not in self.cacheable_methods
            or response.status_code not in self.cacheable_status_codes
        ):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            if cache_status and "X-Cache-Status" not in response.headers:
                response.headers["X-Cache-Status"] = cache_status
            return response

        # Add Vary headers
        if self.vary_headers:
            response.headers["Vary"] = ", ".join(self.vary_headers)

        # Add default cache control
        response.headers["Cache-Control"] = self.default_cache_control

        # Generate ETag if not present
        if "ETag" not in response.headers and hasattr(response, "body"):
            etag = self._generate_etag(response.body)
            response.headers["ETag"] = etag

            # Handle If-None-Match
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match == etag:
                return Response(
                    status_code=304,
                    headers=dict(response.headers),
                )

        return response

    @staticmethod
    def _generate_etag(content: bytes) -> str:
        """Generate an ETag for the given content."""
        return f'"{hashlib.md5(content).hexdigest()}"'


def cache_control(
    max_age: int = 60,
    public: bool = True,
    private: bool = False,
    no_cache: bool = False,
    no_store: bool = False,
    must_revalidate: bool = False,
    stale_while_revalidate: int | None = None,
    stale_if_error: int | None = None,
):
    """Decorator to add Cache-Control headers to route responses.

    Args:
        max_age: Maximum time in seconds the response can be cached
        public: Can be cached by any cache
        private: Can only be cached by the client's browser
        no_cache: Must revalidate with server before using cached response
        no_store: Don't cache the response at all
        must_revalidate: Must revalidate with server when stale
        stale_while_revalidate: Allow serving stale content while revalidating (in seconds)
        stale_if_error: Allow serving stale content on error (in seconds)

    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            response = await func(*args, **kwargs)

            directives = []

            if no_store:
                directives.append("no-store")
            elif no_cache:
                directives.append("no-cache")
            else:
                if public and not private:
                    directives.append("public")
                elif private:
                    directives.append("private")

                directives.append(f"max-age={max_age}")

                if must_revalidate:
                    directives.append("must-revalidate")

                if stale_while_revalidate is not None:
                    directives.append(
                        f"stale-while-revalidate={stale_while_revalidate}",
                    )

                if stale_if_error is not None:
                    directives.append(f"stale-if-error={stale_if_error}")

            response.headers["Cache-Control"] = ", ".join(directives)
            return response

        return wrapper

    return decorator
