"""Unit tests for VAT models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.integrations.emag.models.responses.vat import VatRate, VatResponse


def test_vat_rate_creation():
    """Test creating a valid VatRate instance."""
    vat_rate = VatRate(
        id=1,
        name="TVA 19%",
        value=19.0,
        is_default=True,
        country_code="RO",
        is_active=True,
    )

    assert vat_rate.id == 1
    assert vat_rate.name == "TVA 19%"
    assert vat_rate.value == 19.0
    assert vat_rate.is_default is True
    assert vat_rate.country_code == "RO"
    assert vat_rate.is_active is True


def test_vat_rate_validation():
    """Test VatRate field validation."""
    # Test invalid country code
    with pytest.raises(ValidationError) as excinfo:
        VatRate(id=1, name="Invalid Country", value=19.0, country_code="INVALID")
    assert "Country code must be a 2-letter ISO code" in str(excinfo.value)

    # Test value out of range
    with pytest.raises(ValidationError) as excinfo:
        VatRate(id=1, name="Invalid Value", value=150.0, country_code="RO")
    assert "ensure this value is less than or equal to 100" in str(excinfo.value)

    # Test empty name
    with pytest.raises(ValidationError) as excinfo:
        VatRate(id=1, name="  ", value=19.0, country_code="RO")
    assert "VAT rate name cannot be empty" in str(excinfo.value)


def test_vat_response_creation():
    """Test creating a valid VatResponse instance."""
    vat_rates = [
        VatRate(id=1, name="TVA 19%", value=19.0, is_default=True, country_code="RO"),
        VatRate(id=2, name="TVA 9%", value=9.0, is_default=False, country_code="RO"),
    ]

    response = VatResponse(
        is_error=False,
        messages=[],
        results=vat_rates,
        next_cursor="vat_2",
        prev_cursor=None,
        total_count=2,
    )

    assert response.is_error is False
    assert len(response.results) == 2
    assert response.next_cursor == "vat_2"
    assert response.prev_cursor is None
    assert response.total_count == 2
    assert isinstance(response.timestamp, datetime)


def test_vat_response_from_emag_response():
    """Test creating VatResponse from eMAG API response."""
    emag_response = {
        "isError": False,
        "messages": [],
        "results": [
            {
                "id": 1,
                "name": "TVA 19%",
                "value": 19.0,
                "isDefault": True,
                "countryCode": "RO",
                "isActive": True,
            },
        ],
    }

    response = VatResponse.from_emag_response(emag_response)

    assert response.is_error is False
    assert len(response.results) == 1
    assert response.results[0].name == "TVA 19%"
    assert response.results[0].is_default is True


def test_get_default_rate():
    """Test getting the default VAT rate."""
    vat_rates = [
        VatRate(id=1, name="TVA 9%", value=9.0, is_default=False, country_code="RO"),
        VatRate(id=2, name="TVA 19%", value=19.0, is_default=True, country_code="RO"),
        VatRate(id=3, name="TVA 5%", value=5.0, is_default=False, country_code="RO"),
    ]

    response = VatResponse(
        is_error=False,
        messages=[],
        results=vat_rates,
        total_count=3,
    )

    default_rate = response.get_default_rate()
    assert default_rate is not None
    assert default_rate.id == 2
    assert default_rate.value == 19.0


def test_get_default_rate_not_found():
    """Test getting default rate when none is set as default."""
    vat_rates = [
        VatRate(id=1, name="TVA 9%", value=9.0, is_default=False, country_code="RO"),
        VatRate(id=2, name="TVA 19%", value=19.0, is_default=False, country_code="RO"),
    ]

    response = VatResponse(
        is_error=False,
        messages=[],
        results=vat_rates,
        total_count=2,
    )

    assert response.get_default_rate() is None


def test_has_next_page():
    """Test has_next_page method."""
    # Test with next cursor
    response_with_next = VatResponse(
        is_error=False,
        messages=[],
        results=[],
        next_cursor="vat_10",
        total_count=20,
    )
    assert response_with_next.has_next_page() is True

    # Test without next cursor
    response_without_next = VatResponse(
        is_error=False,
        messages=[],
        results=[],
        next_cursor=None,
        total_count=20,
    )
    assert response_without_next.has_next_page() is False


def test_get_pagination_links():
    """Test generating pagination links."""
    response = VatResponse(
        is_error=False,
        messages=[],
        results=[],
        next_cursor="vat_10",
        prev_cursor="vat_1",
        total_count=30,
    )

    base_url = "http://example.com/api/v1/vat"
    links = response.get_pagination_links(base_url)

    assert links["next"] == f"{base_url}?cursor=vat_10"
    assert links["prev"] == f"{base_url}?cursor=vat_1"

    # Test with no next/prev cursors
    response_no_pages = VatResponse(
        is_error=False,
        messages=[],
        results=[],
        next_cursor=None,
        prev_cursor=None,
        total_count=10,
    )

    links = response_no_pages.get_pagination_links(base_url)
    assert links["next"] is None
    assert links["prev"] is None
