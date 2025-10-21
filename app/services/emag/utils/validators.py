"""
Validation utilities for eMAG integration.

Provides validation functions for eMAG API data structures.
"""

from typing import Any

from app.core.exceptions import ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_product_data(product: dict[str, Any]) -> bool:
    """
    Validate product data structure from eMAG API.

    Args:
        product: Product data dictionary

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["id", "name"]

    for field in required_fields:
        if field not in product:
            raise ValidationError(f"Missing required field: {field}")

    # Validate ID
    if not isinstance(product["id"], (int, str)):
        raise ValidationError(f"Invalid product ID type: {type(product['id'])}")

    # Validate name
    if not product["name"] or not isinstance(product["name"], str):
        raise ValidationError("Product name must be a non-empty string")

    # Validate price if present
    if "price" in product:
        try:
            price = float(product["price"])
            if price < 0:
                raise ValidationError("Product price cannot be negative")
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid price value: {product['price']}") from e

    logger.debug(f"Product data validated successfully: {product.get('id')}")
    return True


def validate_order_data(order: dict[str, Any]) -> bool:
    """
    Validate order data structure from eMAG API.

    Args:
        order: Order data dictionary

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["id", "status"]

    for field in required_fields:
        if field not in order:
            raise ValidationError(f"Missing required field: {field}")

    # Validate ID
    if not isinstance(order["id"], (int, str)):
        raise ValidationError(f"Invalid order ID type: {type(order['id'])}")

    # Validate status
    if not order["status"] or not isinstance(order["status"], (int, str)):
        raise ValidationError("Order status must be a non-empty value")

    # Validate products if present
    if "products" in order:
        if not isinstance(order["products"], list):
            raise ValidationError("Order products must be a list")

        for product in order["products"]:
            if not isinstance(product, dict):
                raise ValidationError("Each product must be a dictionary")
            if "id" not in product:
                raise ValidationError("Product in order must have an ID")

    logger.debug(f"Order data validated successfully: {order.get('id')}")
    return True


def validate_credentials(
    username: str, password: str, account_type: str = "main"
) -> bool:
    """
    Validate eMAG API credentials.

    Args:
        username: API username
        password: API password
        account_type: Account type (main or fbe)

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not username or not isinstance(username, str):
        raise ValidationError(f"Invalid username for {account_type} account")

    if not password or not isinstance(password, str):
        raise ValidationError(f"Invalid password for {account_type} account")

    if len(username) < 3:
        raise ValidationError(f"Username too short for {account_type} account")

    if len(password) < 6:
        raise ValidationError(f"Password too short for {account_type} account")

    logger.debug(f"Credentials validated for {account_type} account: {username[:3]}***")
    return True


def validate_sync_params(
    account_type: str,
    full_sync: bool = False,
    limit: int | None = None,
) -> bool:
    """
    Validate synchronization parameters.

    Args:
        account_type: Account type (main or fbe)
        full_sync: Whether to perform full synchronization
        limit: Optional limit for number of items

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    # Validate account type
    valid_account_types = ["main", "fbe", "both"]
    if account_type not in valid_account_types:
        raise ValidationError(
            f"Invalid account type: {account_type}. "
            f"Must be one of: {', '.join(valid_account_types)}"
        )

    # Validate full_sync
    if not isinstance(full_sync, bool):
        raise ValidationError(f"full_sync must be boolean, got: {type(full_sync)}")

    # Validate limit
    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError(f"limit must be a positive integer, got: {limit}")

        if limit > 10000:
            raise ValidationError(f"limit too large: {limit}. Maximum is 10000")

    logger.debug(
        f"Sync params validated: account={account_type}, "
        f"full_sync={full_sync}, limit={limit}"
    )
    return True
