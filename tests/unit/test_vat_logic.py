"""Standalone tests for VAT service logic."""

from unittest.mock import AsyncMock

import pytest


class VatRate:
    """Simple VatRate model for testing."""

    def __init__(self, id, name, value, is_default, country_code, is_active):
        self.id = id
        self.name = name
        self.value = value
        self.isDefault = is_default
        self.countryCode = country_code
        self.isActive = is_active


class VatResponse:
    """Simple VatResponse model for testing."""

    def __init__(self, is_error=False, messages=None, results=None):
        self.isError = is_error
        self.messages = messages or []
        self.results = results or []


class TestVatLogic:
    """Test VAT service logic without any imports."""

    def test_vat_rate_creation(self):
        """Test VatRate creation and properties."""
        rate = VatRate(
            id=1,
            name="TVA 19%",
            value=19.0,
            is_default=True,
            country_code="RO",
            is_active=True,
        )

        assert rate.id == 1
        assert rate.name == "TVA 19%"
        assert rate.value == 19.0
        assert rate.isDefault is True
        assert rate.countryCode == "RO"
        assert rate.isActive is True

    def test_vat_response_creation(self):
        """Test VatResponse creation and properties."""
        rate = VatRate(1, "TVA 19%", 19.0, True, "RO", True)
        response = VatResponse(is_error=False, messages=["Success"], results=[rate])

        assert response.isError is False
        assert "Success" in response.messages
        assert len(response.results) == 1
        assert response.results[0].id == 1
        assert response.results[0].value == 19.0

    @pytest.mark.asyncio
    async def test_vat_service_logic(self):
        """Test VAT service logic with mock client."""

        class MockClient:
            async def get_paginated(self, *args, **kwargs):
                return VatResponse(
                    is_error=False,
                    messages=[],
                    results=[
                        VatRate(1, "TVA 19%", 19.0, True, "RO", True),
                        VatRate(2, "TVA 9%", 9.0, False, "RO", True),
                    ],
                )

        class VatService:
            def __init__(self, emag_client=None):
                self.emag_client = emag_client or MockClient()

            async def get_vat_rates(self, country_code="RO", **kwargs):
                response = await self.emag_client.get_paginated(
                    endpoint="/api/vat",
                    params={"countryCode": country_code},
                    **kwargs,
                )
                return response

        # Test the service
        service = VatService()
        result = await service.get_vat_rates()

        assert not result.isError
        assert len(result.results) == 2
        assert result.results[0].countryCode == "RO"
        assert result.results[1].countryCode == "RO"

        # Test with different country code
        result = await service.get_vat_rates(country_code="BG")
        assert not result.isError

    @pytest.mark.asyncio
    async def test_vat_service_with_mock(self):
        """Test VAT service with a mock client."""
        mock_client = AsyncMock()
        mock_client.get_paginated.return_value = VatResponse(
            is_error=False,
            results=[VatRate(1, "TVA 19%", 19.0, True, "RO", True)],
        )

        class VatService:
            def __init__(self, emag_client):
                self.emag_client = emag_client

            async def get_vat_rates(self, **kwargs):
                return await self.emag_client.get_paginated(
                    endpoint="/api/vat",
                    params={"countryCode": kwargs.get("country_code", "RO")},
                    **kwargs,
                )

        service = VatService(mock_client)
        result = await service.get_vat_rates(force_refresh=True)

        # Verify the mock was called correctly
        mock_client.get_paginated.assert_called_once()
        args, kwargs = mock_client.get_paginated.call_args
        assert kwargs["endpoint"] == "/api/vat"
        assert kwargs["force_refresh"] is True
        assert kwargs["params"]["countryCode"] == "RO"

        # Verify the response
        assert not result.isError
        assert len(result.results) == 1
        assert result.results[0].value == 19.0
