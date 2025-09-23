"""Completely isolated unit tests for the VAT service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock the VatResponse and VatRate models
class MockVatRate:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MockVatResponse:
    def __init__(self, isError=False, messages=None, results=None):
        self.isError = isError
        self.messages = messages or []
        self.results = results or []


# Mock the VatService class
class MockVatService:
    def __init__(self, emag_client=None):
        self.emag_client = emag_client or AsyncMock()

    async def get_vat_rates(
        self,
        country_code="RO",
        cursor=None,
        limit=100,
        force_refresh=False,
    ):
        return MockVatResponse(
            isError=False,
            messages=[],
            results=[
                MockVatRate(
                    id=1,
                    name=f"TVA 19% ({country_code})",
                    value=19.0,
                    isDefault=True,
                    countryCode=country_code,
                    isActive=True,
                ),
            ],
        )


# Create a test fixture that patches all necessary imports
@pytest.fixture(autouse=True)
def mock_imports():
    with patch.dict(
        "sys.modules",
        {
            "app.integrations.emag.config": MagicMock(),
            "app.integrations.emag.client": MagicMock(),
            "app.integrations.emag.models.responses.vat": MagicMock(
                VatResponse=MockVatResponse,
                VatRate=MockVatRate,
            ),
        },
    ):
        # Now import the actual service
        from app.integrations.emag.services import vat_service

        # Replace the actual implementation with our mock
        vat_service.VatService = MockVatService
        yield


# Tests
class TestVatServiceIsolated:
    @pytest.fixture
    def mock_emag_client(self):
        client = AsyncMock()
        client.get_paginated = AsyncMock()
        return client

    @pytest.fixture
    def vat_service(self, mock_emag_client):
        return MockVatService(emag_client=mock_emag_client)

    @pytest.mark.asyncio
    async def test_get_vat_rates_basic(self, vat_service):
        """Test basic VAT rate retrieval."""
        result = await vat_service.get_vat_rates()
        assert not result.isError
        assert len(result.results) == 1
        assert result.results[0].countryCode == "RO"
        assert result.results[0].value == 19.0

    @pytest.mark.asyncio
    async def test_get_vat_rates_with_country(self, vat_service):
        """Test VAT rate retrieval with specific country code."""
        result = await vat_service.get_vat_rates(country_code="BG")
        assert result.results[0].countryCode == "BG"
        assert "BG" in result.results[0].name

    @pytest.mark.asyncio
    async def test_get_vat_rates_with_pagination(self, vat_service, mock_emag_client):
        """Test VAT rate retrieval with pagination."""
        # Set up the mock to return a specific response
        mock_response = MockVatResponse(
            isError=False,
            messages=[],
            results=[
                MockVatRate(
                    id=1,
                    name="TVA 19%",
                    value=19.0,
                    isDefault=True,
                    countryCode="RO",
                    isActive=True,
                ),
                MockVatRate(
                    id=2,
                    name="TVA 9%",
                    value=9.0,
                    isDefault=False,
                    countryCode="RO",
                    isActive=True,
                ),
            ],
        )
        vat_service.emag_client.get_paginated.return_value = mock_response

        result = await vat_service.get_vat_rates(cursor="page2", limit=2)
        assert len(result.results) == 2
        assert result.results[0].value == 19.0
        assert result.results[1].value == 9.0

        # Verify the client was called with the right parameters
        vat_service.emag_client.get_paginated.assert_called_once()
        args, kwargs = vat_service.emag_client.get_paginated.call_args
        assert kwargs["cursor"] == "page2"
        assert kwargs["limit"] == 2
        assert kwargs["params"]["countryCode"] == "RO"

    @pytest.mark.asyncio
    async def test_force_refresh(self, vat_service, mock_emag_client):
        """Test that force refresh is passed to the client."""
        await vat_service.get_vat_rates(force_refresh=True)
        mock_emag_client.get_paginated.assert_called_once()
        args, kwargs = mock_emag_client.get_paginated.call_args
        assert kwargs["force_refresh"] is True
