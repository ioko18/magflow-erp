"""
Unit tests for Chinese text utilities.

Tests the functions in app.core.utils.chinese_text_utils module.
"""

import pytest

from app.core.utils.chinese_text_utils import (
    contains_chinese,
    extract_chinese_text,
    is_likely_chinese_product_name,
    normalize_chinese_name,
)


class TestContainsChinese:
    """Test contains_chinese function."""

    def test_contains_chinese_with_pure_chinese(self):
        """Test with pure Chinese text."""
        assert contains_chinese("2路PWM脉冲频率占空比可调模块方波矩形波信号发生器步进电机驱动") is True

    def test_contains_chinese_with_mixed_text(self):
        """Test with mixed Chinese and English."""
        assert contains_chinese("Product 2路PWM脉冲频率") is True

    def test_contains_chinese_with_english_only(self):
        """Test with English only."""
        assert contains_chinese("Hello World Product") is False

    def test_contains_chinese_with_numbers_only(self):
        """Test with numbers only."""
        assert contains_chinese("12345") is False

    def test_contains_chinese_with_empty_string(self):
        """Test with empty string."""
        assert contains_chinese("") is False

    def test_contains_chinese_with_none(self):
        """Test with None."""
        assert contains_chinese(None) is False

    def test_contains_chinese_with_special_characters(self):
        """Test with special characters."""
        assert contains_chinese("!@#$%^&*()") is False

    def test_contains_chinese_with_spaces(self):
        """Test with spaces and Chinese."""
        assert contains_chinese("  脉冲频率  ") is True


class TestExtractChineseText:
    """Test extract_chinese_text function."""

    def test_extract_chinese_from_mixed_text(self):
        """Test extracting Chinese from mixed text."""
        result = extract_chinese_text("Product 脉冲频率 Test 占空比")
        assert result == "脉冲频率占空比"

    def test_extract_chinese_from_pure_chinese(self):
        """Test extracting from pure Chinese."""
        result = extract_chinese_text("脉冲频率占空比")
        assert result == "脉冲频率占空比"

    def test_extract_chinese_from_english_only(self):
        """Test extracting from English only."""
        result = extract_chinese_text("Hello World")
        assert result is None

    def test_extract_chinese_from_empty_string(self):
        """Test extracting from empty string."""
        result = extract_chinese_text("")
        assert result is None

    def test_extract_chinese_from_none(self):
        """Test extracting from None."""
        result = extract_chinese_text(None)
        assert result is None


class TestIsLikelyChineseProductName:
    """Test is_likely_chinese_product_name function."""

    def test_likely_chinese_product_name(self):
        """Test with likely Chinese product name."""
        assert is_likely_chinese_product_name("2路PWM脉冲频率占空比可调模块") is True

    def test_unlikely_short_chinese_text(self):
        """Test with short Chinese text (less than 4 chars)."""
        assert is_likely_chinese_product_name("脉冲") is False

    def test_unlikely_english_text(self):
        """Test with English text."""
        assert is_likely_chinese_product_name("Product Name") is False

    def test_unlikely_none(self):
        """Test with None."""
        assert is_likely_chinese_product_name(None) is False

    def test_unlikely_empty_string(self):
        """Test with empty string."""
        assert is_likely_chinese_product_name("") is False

    def test_likely_mixed_text_with_chinese(self):
        """Test with mixed text containing Chinese."""
        assert is_likely_chinese_product_name("2路PWM脉冲频率占空比") is True


class TestNormalizeChineseName:
    """Test normalize_chinese_name function."""

    def test_normalize_with_extra_spaces(self):
        """Test normalizing text with extra spaces."""
        result = normalize_chinese_name("  脉冲   频率   占空比  ")
        assert result == "脉冲 频率 占空比"

    def test_normalize_with_leading_trailing_spaces(self):
        """Test normalizing text with leading/trailing spaces."""
        result = normalize_chinese_name("  脉冲频率占空比  ")
        assert result == "脉冲频率占空比"

    def test_normalize_with_no_spaces(self):
        """Test normalizing text without spaces."""
        result = normalize_chinese_name("脉冲频率占空比")
        assert result == "脉冲频率占空比"

    def test_normalize_with_none(self):
        """Test normalizing None."""
        result = normalize_chinese_name(None)
        assert result is None

    def test_normalize_with_empty_string(self):
        """Test normalizing empty string."""
        result = normalize_chinese_name("")
        assert result is None

    def test_normalize_with_only_spaces(self):
        """Test normalizing string with only spaces."""
        result = normalize_chinese_name("   ")
        assert result is None

    def test_normalize_preserves_chinese_characters(self):
        """Test that normalization preserves Chinese characters."""
        original = "2路PWM脉冲频率占空比可调模块方波矩形波信号发生器步进电机驱动"
        result = normalize_chinese_name(original)
        assert result == original


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow_with_product_name(self):
        """Test full workflow with a real product name."""
        product_name = "2路PWM脉冲频率占空比可调模块方波矩形波信号发生器步进电机驱动"

        # Check if it contains Chinese
        assert contains_chinese(product_name) is True

        # Check if it's likely a product name
        assert is_likely_chinese_product_name(product_name) is True

        # Extract and normalize
        extracted = extract_chinese_text(product_name)
        assert extracted is not None

        normalized = normalize_chinese_name(product_name)
        assert normalized == product_name

    def test_workflow_with_mixed_text(self):
        """Test workflow with mixed text."""
        mixed_text = "  Product 2路PWM脉冲频率  "

        # Check if it contains Chinese
        assert contains_chinese(mixed_text) is True

        # Extract Chinese
        extracted = extract_chinese_text(mixed_text)
        assert extracted == "2路PWM脉冲频率"

        # Normalize
        normalized = normalize_chinese_name(mixed_text)
        assert normalized == "Product 2路PWM脉冲频率"

    def test_workflow_with_english_only(self):
        """Test workflow with English only."""
        english_text = "  Product Name  "

        # Check if it contains Chinese
        assert contains_chinese(english_text) is False

        # Extract Chinese
        extracted = extract_chinese_text(english_text)
        assert extracted is None

        # Normalize
        normalized = normalize_chinese_name(english_text)
        assert normalized == "Product Name"
