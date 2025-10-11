"""
Helper utilities for eMAG integration.

Provides general helper functions for eMAG API operations.
"""

from datetime import datetime
from decimal import Decimal

from app.core.logging import get_logger

logger = get_logger(__name__)


def build_api_url(base_url: str, endpoint: str, params: dict | None = None) -> str:
    """
    Build complete API URL with parameters.

    Args:
        base_url: Base API URL
        endpoint: API endpoint path
        params: Optional query parameters

    Returns:
        Complete URL string
    """
    # Ensure base_url doesn't end with /
    base_url = base_url.rstrip("/")

    # Ensure endpoint starts with /
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    url = f"{base_url}{endpoint}"

    if params:
        query_parts = []
        for key, value in params.items():
            if value is not None:
                query_parts.append(f"{key}={value}")

        if query_parts:
            url += "?" + "&".join(query_parts)

    return url


def format_price(price: float, currency: str = "RON", decimals: int = 2) -> str:
    """
    Format price for display.

    Args:
        price: Price value
        currency: Currency code
        decimals: Number of decimal places

    Returns:
        Formatted price string
    """
    try:
        price_decimal = Decimal(str(price))
        formatted = f"{price_decimal:.{decimals}f}"
        return f"{formatted} {currency}"
    except (ValueError, TypeError, Exception):
        logger.warning(f"Invalid price value: {price}")
        return f"0.00 {currency}"


def format_date(
    date: datetime,
    format_str: str = "%Y-%m-%d %H:%M:%S",
    timezone: str | None = None,
) -> str:
    """
    Format datetime for display.

    Args:
        date: Datetime object
        format_str: Format string
        timezone: Optional timezone name

    Returns:
        Formatted date string
    """
    if not isinstance(date, datetime):
        logger.warning(f"Invalid date value: {date}")
        return ""

    try:
        # TODO: Add timezone conversion if needed
        return date.strftime(format_str)
    except Exception as e:
        logger.warning(f"Error formatting date: {e}")
        return str(date)


def sanitize_product_name(name: str, max_length: int = 255) -> str:
    """
    Sanitize product name for database storage.

    Args:
        name: Product name
        max_length: Maximum length

    Returns:
        Sanitized name
    """
    if not name:
        return ""

    # Strip whitespace
    name = name.strip()

    # Remove multiple spaces
    name = " ".join(name.split())

    # Truncate if too long
    if len(name) > max_length:
        name = name[: max_length - 3] + "..."

    return name


def calculate_vat_amount(price: float, vat_rate: float) -> float:
    """
    Calculate VAT amount from price and rate.

    Args:
        price: Price including VAT
        vat_rate: VAT rate (as decimal, e.g., 0.19 for 19%)

    Returns:
        VAT amount
    """
    try:
        if vat_rate <= 0:
            return 0.0

        # Price includes VAT, so we need to extract it
        # VAT = Price - (Price / (1 + VAT_rate))
        vat_amount = price - (price / (1 + vat_rate))
        return round(vat_amount, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        logger.warning(f"Error calculating VAT: price={price}, rate={vat_rate}")
        return 0.0


def calculate_price_without_vat(price: float, vat_rate: float) -> float:
    """
    Calculate price without VAT.

    Args:
        price: Price including VAT
        vat_rate: VAT rate (as decimal, e.g., 0.19 for 19%)

    Returns:
        Price without VAT
    """
    try:
        if vat_rate <= 0:
            return price

        price_without_vat = price / (1 + vat_rate)
        return round(price_without_vat, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        logger.warning(
            f"Error calculating price without VAT: price={price}, rate={vat_rate}"
        )
        return price


def chunk_list(items: list, chunk_size: int) -> list:
    """
    Split list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i : i + chunk_size])

    return chunks


def mask_sensitive_data(data: str, visible_chars: int = 3, mask_char: str = "*") -> str:
    """
    Mask sensitive data for logging.

    Args:
        data: Data to mask
        visible_chars: Number of visible characters at start
        mask_char: Character to use for masking

    Returns:
        Masked string
    """
    if not data:
        return ""

    if len(data) <= visible_chars:
        return mask_char * len(data)

    visible = data[:visible_chars]
    masked = mask_char * (len(data) - visible_chars)

    return f"{visible}{masked}"


def get_account_display_name(account_type: str) -> str:
    """
    Get display name for account type.

    Args:
        account_type: Account type code

    Returns:
        Display name
    """
    names = {
        "main": "Cont Principal",
        "fbe": "Cont FBE (Fulfillment by eMAG)",
        "both": "Ambele Conturi",
    }

    return names.get(account_type.lower(), account_type)
