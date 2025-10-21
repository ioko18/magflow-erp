"""
Utilities for detecting and handling Chinese text.

This module provides functions to:
- Detect if text contains Chinese characters
- Extract Chinese text from mixed content
- Validate Chinese text
"""

import re


def contains_chinese(text: str | None) -> bool:
    """Check if text contains Chinese characters.

    Args:
        text: Text to check

    Returns:
        True if text contains Chinese characters, False otherwise
    """
    if not text:
        return False

    # Unicode ranges for CJK Unified Ideographs
    # Common ranges: 4E00-9FFF (CJK Unified Ideographs)
    # Extended: 3400-4DBF, 20000-2A6DF, etc.
    chinese_pattern = re.compile(
        r'[\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f]'
    )
    return bool(chinese_pattern.search(text))


def extract_chinese_text(text: str | None) -> str | None:
    """Extract only Chinese characters from text.

    Args:
        text: Text to extract from

    Returns:
        String containing only Chinese characters, or None if no Chinese found
    """
    if not text:
        return None

    chinese_pattern = re.compile(
        r'[\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f]+'
    )
    matches = chinese_pattern.findall(text)

    if matches:
        return ''.join(matches)
    return None


def is_likely_chinese_product_name(text: str | None) -> bool:
    """Determine if text is likely a Chinese product name.

    A text is considered likely Chinese product name if:
    - It contains Chinese characters
    - It's reasonably long (at least 4 characters)

    Args:
        text: Text to check

    Returns:
        True if likely Chinese product name, False otherwise
    """
    if not text or len(text) < 4:
        return False

    return contains_chinese(text)


def normalize_chinese_name(text: str | None) -> str | None:
    """Normalize Chinese product name by:
    - Removing leading/trailing whitespace
    - Removing extra spaces
    - Preserving Chinese characters

    Args:
        text: Text to normalize

    Returns:
        Normalized text or None if empty
    """
    if not text:
        return None

    # Remove leading/trailing whitespace
    text = text.strip()

    # Remove multiple consecutive spaces
    text = re.sub(r'\s+', ' ', text)

    if not text:
        return None

    return text
