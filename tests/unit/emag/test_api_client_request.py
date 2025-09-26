import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.emag_integration_service import EmagApiClient, EmagApiConfig, EmagApiEnvironment, EmagIntegrationService


@pytest.fixture
def emag_config():
    return EmagApiConfig(
        environment=EmagApiEnvironment.SANDBOX,
        api_username="test-user",
        api_password="test-pass",
    )


@pytest.mark.asyncio
async def test_api_client_request_delegates_to_make_request(emag_config):
    client = EmagApiClient(emag_config)

    with patch.object(client, "_make_request", new=AsyncMock(return_value={"ok": True})) as mock_make_request:
        result = await client.request("GET", "/offers", data={"foo": "bar"}, params={"q": 1})

    assert result == {"ok": True}
    mock_make_request.assert_awaited_once_with(
        "GET",
        "/offers",
        data={"foo": "bar"},
        params={"q": 1},
    )


@pytest.mark.asyncio
async def test_service_make_request_prefers_public_request_helper(emag_config):
    context = MagicMock()
    context.settings = MagicMock()
    with patch.object(EmagIntegrationService, "_load_config", return_value=emag_config):
        service = EmagIntegrationService(context)

    mock_client = MagicMock()
    mock_client.request = AsyncMock(return_value={"result": "ok"})
    service.api_client = mock_client

    result = await service._make_request("GET", "/resource")

    assert result == {"result": "ok"}
    mock_client.request.assert_awaited_once_with("GET", "/resource", data=None, params=None)


@pytest.mark.asyncio
async def test_service_make_request_falls_back_to_private_helper(emag_config):
    context = MagicMock()
    context.settings = MagicMock()
    with patch.object(EmagIntegrationService, "_load_config", return_value=emag_config):
        service = EmagIntegrationService(context)

    mock_client = MagicMock()
    mock_client._make_request = AsyncMock(return_value={"result": "fallback"})
    delattr(mock_client, "request")
    service.api_client = mock_client

    result = await service._make_request("POST", "/resource", data={"foo": 1})

    assert result == {"result": "fallback"}
    mock_client._make_request.assert_awaited_once_with("POST", "/resource", data={"foo": 1}, params=None)
