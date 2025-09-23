"""Pytest configuration and fixtures for eMAG integration tests."""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiohttp import web
import pytest

from app.integrations.emag.client import EmagAPIClient


class MockEmagAPI:
    """Mock eMAG API server for testing."""

    def __init__(self):
        self.routes = {}
        self.requests = []

    def get(
        self,
        path: str,
        status: int = 200,
        payload: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ):
        """Register a GET endpoint with the mock server."""
        self.routes[("GET", path)] = {
            "status": status,
            "payload": payload or {},
            "headers": headers or {},
        }
        return self

    def post(
        self,
        path: str,
        status: int = 200,
        payload: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ):
        """Register a POST endpoint with the mock server."""
        self.routes[("POST", path)] = {
            "status": status,
            "payload": payload or {},
            "headers": headers or {},
        }
        return self

    def put(
        self,
        path: str,
        status: int = 200,
        payload: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ):
        """Register a PUT endpoint with the mock server."""
        self.routes[("PUT", path)] = {
            "status": status,
            "payload": payload or {},
            "headers": headers or {},
        }
        return self

    def delete(
        self,
        path: str,
        status: int = 204,
        payload: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ):
        """Register a DELETE endpoint with the mock server."""
        self.routes[("DELETE", path)] = {
            "status": status,
            "payload": payload or {},
            "headers": headers or {},
        }
        return self

    async def handle_request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> web.Response:
        """Handle an incoming request to the mock server."""
        # Store the request for later inspection
        self.requests.append(
            {
                "method": method,
                "path": path,
                "query": dict(kwargs.get("params", {})),
                "headers": dict(kwargs.get("headers", {})),
                "json": kwargs.get("json"),
            },
        )

        # Find a matching route
        route_key = (method.upper(), path)
        if route_key not in self.routes:
            # Try to find a matching route with path parameters
            for (route_method, route_path), handler in self.routes.items():
                if route_method == method.upper() and path.startswith(
                    route_path.rstrip("/") + "/",
                ):
                    route_key = (route_method, route_path)
                    break
            else:
                # No matching route found
                return web.Response(
                    status=404,
                    text=json.dumps(
                        {
                            "isError": True,
                            "messages": [
                                {
                                    "code": "NOT_FOUND",
                                    "message": f"No route found for {method} {path}",
                                },
                            ],
                        },
                    ),
                    content_type="application/json",
                )

        handler = self.routes[route_key]

        # Create and return the response
        return web.Response(
            status=handler["status"],
            headers=handler["headers"],
            text=json.dumps(handler["payload"]),
            content_type="application/json",
        )

    def called(self, path: str, method: str = "GET") -> bool:
        """Check if a particular endpoint was called."""
        return any(
            req["path"] == path and req["method"].upper() == method.upper()
            for req in self.requests
        )

    def call_count(self, path: str, method: str = "GET") -> int:
        """Count how many times an endpoint was called."""
        return sum(
            1
            for req in self.requests
            if req["path"] == path and req["method"].upper() == method.upper()
        )

    @property
    def last_request(self):
        """Get the last request made to the mock server."""
        if not self.requests:
            raise IndexError("No requests have been made yet")
        return self.requests[-1]


@pytest.fixture
def mock_emag_api(monkeypatch):
    """Fixture to mock the eMAG API for testing."""
    mock_api = MockEmagAPI()

    # Patch the client to use our mock server
    async def patched_request(self, method, endpoint, **kwargs):
        # Convert the request to our mock server format
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        response = await mock_api.handle_request(method, path, **kwargs)

        # Convert the response to the format expected by the client
        if 200 <= response.status < 300:
            data = await response.json()
            return data
        error_data = await response.json()
        raise Exception(f"API Error: {error_data}")

    monkeypatch.setattr(EmagAPIClient, "_make_request", patched_request)

    return mock_api


@pytest.fixture
def mock_redis(monkeypatch):
    """Fixture to mock Redis for testing."""

    class MockRedis:
        def __init__(self):
            self._data = {}
            self._expirations = {}

        async def get(self, key):
            if key in self._data and (
                key not in self._expirations or self._expirations[key] > datetime.now()
            ):
                return self._data[key]
            return None

        async def set(
            self,
            key,
            value,
            ex=None,
            px=None,
            nx=False,
            xx=False,
            keepttl=False,
        ):
            self._data[key] = value
            if ex is not None:
                self._expirations[key] = datetime.now() + timedelta(seconds=ex)
            elif px is not None:
                self._data[key] = value
                self._expirations[key] = datetime.now() + timedelta(milliseconds=px)
            return True

        async def delete(self, *keys):
            count = 0
            for key in keys:
                if key in self._data:
                    del self._data[key]
                    if key in self._expirations:
                        del self._expirations[key]
                    count += 1
            return count

        async def close(self):
            pass

    mock_redis = MockRedis()

    # Patch the Redis client to use our mock
    monkeypatch.setattr("app.integrations.emag.cache.redis", mock_redis)

    return mock_redis


@pytest.fixture
def mock_emag_auth(monkeypatch):
    """Fixture to mock eMAG authentication."""

    async def mock_get_auth_token(self):
        return "mock_auth_token"

    monkeypatch.setattr(EmagAPIClient, "_get_auth_token", mock_get_auth_token)
