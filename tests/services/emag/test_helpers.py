"""
Tests for eMAG helper utilities.
"""

import pytest
from datetime import datetime
from app.services.emag.utils.helpers import (
    build_api_url,
    format_price,
    format_date,
    sanitize_product_name,
    calculate_vat_amount,
    calculate_price_without_vat,
    chunk_list,
    mask_sensitive_data,
    get_account_display_name,
)


class TestUrlBuilder:
    """Test API URL building."""
    
    def test_simple_url(self):
        """Test building simple URL without parameters."""
        url = build_api_url("https://api.example.com", "/products")
        assert url == "https://api.example.com/products"
    
    def test_url_with_params(self):
        """Test building URL with parameters."""
        url = build_api_url(
            "https://api.example.com",
            "/products",
            {"limit": 10, "offset": 0}
        )
        assert "limit=10" in url
        assert "offset=0" in url
    
    def test_url_normalization(self):
        """Test URL normalization (trailing slashes, etc.)."""
        url = build_api_url("https://api.example.com/", "products")
        assert url == "https://api.example.com/products"


class TestPriceFormatting:
    """Test price formatting."""
    
    def test_format_price_default(self):
        """Test default price formatting."""
        result = format_price(99.99)
        assert result == "99.99 RON"
    
    def test_format_price_custom_currency(self):
        """Test price formatting with custom currency."""
        result = format_price(99.99, currency="EUR")
        assert result == "99.99 EUR"
    
    def test_format_price_decimals(self):
        """Test price formatting with custom decimals."""
        result = format_price(99.999, decimals=3)
        assert result == "99.999 RON"
    
    def test_format_invalid_price(self):
        """Test formatting invalid price."""
        result = format_price("invalid")
        assert result == "0.00 RON"


class TestDateFormatting:
    """Test date formatting."""
    
    def test_format_date_default(self):
        """Test default date formatting."""
        date = datetime(2025, 10, 10, 14, 30, 0)
        result = format_date(date)
        assert result == "2025-10-10 14:30:00"
    
    def test_format_date_custom(self):
        """Test custom date formatting."""
        date = datetime(2025, 10, 10, 14, 30, 0)
        result = format_date(date, format_str="%d/%m/%Y")
        assert result == "10/10/2025"
    
    def test_format_invalid_date(self):
        """Test formatting invalid date."""
        result = format_date("not a date")
        assert result == ""


class TestProductNameSanitization:
    """Test product name sanitization."""
    
    def test_sanitize_normal_name(self):
        """Test sanitizing normal product name."""
        result = sanitize_product_name("  Test Product  ")
        assert result == "Test Product"
    
    def test_sanitize_multiple_spaces(self):
        """Test sanitizing name with multiple spaces."""
        result = sanitize_product_name("Test    Product")
        assert result == "Test Product"
    
    def test_sanitize_long_name(self):
        """Test sanitizing long product name."""
        long_name = "A" * 300
        result = sanitize_product_name(long_name, max_length=255)
        assert len(result) == 255
        assert result.endswith("...")


class TestVatCalculations:
    """Test VAT calculations."""
    
    def test_calculate_vat_amount(self):
        """Test calculating VAT amount."""
        # Price 119 RON with 19% VAT should have VAT of 19 RON
        vat = calculate_vat_amount(119.0, 0.19)
        assert abs(vat - 19.0) < 0.01
    
    def test_calculate_price_without_vat(self):
        """Test calculating price without VAT."""
        # Price 119 RON with 19% VAT should be 100 RON without VAT
        price = calculate_price_without_vat(119.0, 0.19)
        assert abs(price - 100.0) < 0.01
    
    def test_zero_vat_rate(self):
        """Test calculations with zero VAT rate."""
        vat = calculate_vat_amount(100.0, 0.0)
        assert vat == 0.0
        
        price = calculate_price_without_vat(100.0, 0.0)
        assert price == 100.0


class TestListChunking:
    """Test list chunking."""
    
    def test_chunk_list_even(self):
        """Test chunking list with even division."""
        items = list(range(10))
        chunks = chunk_list(items, 5)
        assert len(chunks) == 2
        assert len(chunks[0]) == 5
        assert len(chunks[1]) == 5
    
    def test_chunk_list_uneven(self):
        """Test chunking list with uneven division."""
        items = list(range(11))
        chunks = chunk_list(items, 5)
        assert len(chunks) == 3
        assert len(chunks[0]) == 5
        assert len(chunks[1]) == 5
        assert len(chunks[2]) == 1
    
    def test_chunk_list_invalid_size(self):
        """Test chunking with invalid chunk size."""
        items = list(range(10))
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_list(items, 0)


class TestDataMasking:
    """Test sensitive data masking."""
    
    def test_mask_sensitive_data(self):
        """Test masking sensitive data."""
        result = mask_sensitive_data("test_password", visible_chars=3)
        assert result == "tes**********"
    
    def test_mask_short_data(self):
        """Test masking short data."""
        result = mask_sensitive_data("ab", visible_chars=3)
        assert result == "**"
    
    def test_mask_empty_data(self):
        """Test masking empty data."""
        result = mask_sensitive_data("")
        assert result == ""


class TestAccountDisplayName:
    """Test account display name."""
    
    def test_main_account(self):
        """Test display name for main account."""
        result = get_account_display_name("main")
        assert result == "Cont Principal"
    
    def test_fbe_account(self):
        """Test display name for FBE account."""
        result = get_account_display_name("fbe")
        assert result == "Cont FBE (Fulfillment by eMAG)"
    
    def test_unknown_account(self):
        """Test display name for unknown account."""
        result = get_account_display_name("unknown")
        assert result == "unknown"
