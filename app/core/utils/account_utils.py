"""
Account Type Utilities for MagFlow ERP.

Provides utilities for normalizing and validating account types
across the application to ensure consistency.
"""


VALID_ACCOUNT_TYPES = {"main", "fbe"}


def normalize_account_type(account_type: str | None) -> str | None:
    """
    Normalize account type to lowercase.

    Args:
        account_type: Account type string (case-insensitive)

    Returns:
        Normalized account type in lowercase or None if input is None

    Raises:
        ValueError: If account type is not valid
    """
    if account_type is None:
        return None

    normalized = account_type.lower().strip()

    if normalized not in VALID_ACCOUNT_TYPES:
        raise ValueError(
            f"Invalid account type: {account_type}. "
            f"Must be one of: {', '.join(VALID_ACCOUNT_TYPES)}"
        )

    return normalized


def validate_account_type(account_type: str) -> bool:
    """
    Validate if account type is valid.

    Args:
        account_type: Account type to validate

    Returns:
        True if valid, False otherwise
    """
    if not account_type:
        return False

    return account_type.lower().strip() in VALID_ACCOUNT_TYPES


def get_account_display_name(account_type: str) -> str:
    """
    Get display name for account type.

    Args:
        account_type: Account type

    Returns:
        Display name (uppercase)
    """
    if not account_type:
        return "UNKNOWN"

    normalized = account_type.lower().strip()

    if normalized == "main":
        return "MAIN"
    elif normalized == "fbe":
        return "FBE"
    else:
        return account_type.upper()
