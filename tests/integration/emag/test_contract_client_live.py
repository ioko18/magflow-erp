"""Contract-style integration tests for `EmagApiClient` against a live aiohttp server."""

from __future__ import annotations

import base64
import socket
from typing import Dict, List, Tuple

import pytest
from aiohttp import web

from app.services.emag.emag_integration_service import (
    EmagApiClient,
    EmagApiConfig,
    EmagApiEnvironment,
)


@pytest.fixture
async def live_emag_server() -> Tuple[str, List[Dict[str, Dict[str, str]]]]:
    """Spin up a lightweight aiohttp server to emulate the eMAG API."""
    requests: List[Dict[str, Dict[str, str]]] = []

    async def handle_test(request: web.Request) -> web.Response:
        requests.append(
            {
                "path": request.path,
                "method": request.method,
                "headers": dict(request.headers),
                "query": dict(request.rel_url.query),
            }
        )
        return web.json_response({"isError": False, "messages": [], "data": {"pong": True}})

    async def handle_products(request: web.Request) -> web.Response:
        requests.append(
            {
                "path": request.path,
                "method": request.method,
                "headers": dict(request.headers),
                "query": dict(request.rel_url.query),
            }
        )
        return web.json_response(
            {
                "isError": False,
                "messages": [],
                "data": {
                    "products": [
                        {
                            "id": "P123",
                            "name": "Contract Product",
                            "sku": "CONTRACT-001",
                        }
                    ],
                    "total_count": 1,
                },
            }
        )

    app = web.Application()
    app.add_routes(
        [
            web.get("/test", handle_test),
            web.get("/products", handle_products),
        ]
    )

    # Bind to an ephemeral port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    base_url = f"http://{host}:{port}"

    try:
        yield base_url, requests
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_emag_api_client_live_contract(
    live_emag_server: Tuple[str, List[Dict[str, Dict[str, str]]]]
) -> None:
    """`EmagApiClient` should perform real HTTP requests against the test server."""
    base_url, recorded_requests = live_emag_server

    config = EmagApiConfig(
        environment=EmagApiEnvironment.SANDBOX,
        api_username="contract_user",
        api_password="contract_pass",
        api_timeout=5,
    )
    # Override the default sandbox URL with our local test server
    config.base_url = base_url

    client = EmagApiClient(
        username=config.api_username,
        password=config.api_password,
        base_url=base_url,
        timeout=config.api_timeout,
        max_retries=config.max_retries,
    )

    try:
        await client.start()
        products_response = await client.get_products(page=1, limit=25)
    finally:
        await client.close()

    # Validate response payload integrity
    assert products_response["isError"] is False
    assert products_response["data"]["total_count"] == 1
    product = products_response["data"]["products"][0]
    assert product["sku"] == "CONTRACT-001"
    assert product["name"] == "Contract Product"

    # Ensure requests were actually issued with expected headers and query params
    assert len(recorded_requests) >= 2  # /test during initialize + /products fetch
    expected_auth = "Basic " + base64.b64encode(b"contract_user:contract_pass").decode()

    product_calls = [req for req in recorded_requests if req["path"] == "/products"]
    assert product_calls, "Expected at least one call to /products"

    for call in product_calls:
        assert call["headers"].get("Authorization") == expected_auth
        assert call["query"] == {"page": "1", "limit": "25"}
