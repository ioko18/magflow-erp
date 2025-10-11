"""
Order Validation Service for eMAG Integration.

Validates order data conforming to eMAG API v4.4.8 specifications (Section 5.1).
"""

from typing import Any


def validate_order_data(order_data: dict[str, Any]) -> list[str]:
    """
    Validate order data conforming to section 5.1 from eMAG API guide.

    Args:
        order_data: Dictionary containing order data from eMAG API

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Validare câmpuri obligatorii
    if not order_data.get("id"):
        errors.append("Missing required field: id")

    # Validare status (0-5)
    if "status" not in order_data:
        errors.append("Missing required field: status")
    elif order_data["status"] not in [0, 1, 2, 3, 4, 5]:
        errors.append(f"Invalid status: {order_data['status']} (must be 0-5)")

    # Validare payment_mode_id (1-3)
    if "payment_mode_id" not in order_data:
        errors.append("Missing required field: payment_mode_id")
    elif order_data["payment_mode_id"] not in [1, 2, 3]:
        errors.append(
            f"Invalid payment_mode_id: {order_data['payment_mode_id']} (must be 1-3)"
        )

    # Validare products array
    if not order_data.get("products"):
        errors.append("Missing required field: products")
    elif not isinstance(order_data["products"], list):
        errors.append("Invalid products field: must be an array")
    elif len(order_data["products"]) == 0:
        errors.append("Products array cannot be empty")
    else:
        # Validare fiecare produs
        for idx, product in enumerate(order_data["products"]):
            product_errors = _validate_order_product(product, idx)
            errors.extend(product_errors)

    # Validare customer information
    if not order_data.get("customer"):
        errors.append("Missing required field: customer")
    else:
        customer_errors = _validate_customer_data(order_data["customer"])
        errors.extend(customer_errors)

    # Validare payment information pentru online payments
    if order_data.get("payment_mode_id") == 3:  # Card online
        if "payment_status" not in order_data:
            errors.append("Missing payment_status for online payment")
        elif order_data["payment_status"] not in [0, 1]:
            errors.append(
                f"Invalid payment_status: {order_data['payment_status']} (must be 0 or 1)"
            )

    # Validare type pentru FBE/FBS orders
    if "type" in order_data and order_data["type"] not in [2, 3]:
        errors.append(
            f"Invalid order type: {order_data['type']} (must be 2=FBE or 3=FBS)"
        )

    return errors


def _validate_order_product(product: dict[str, Any], index: int) -> list[str]:
    """
    Validate individual product in order.

    Args:
        product: Product data dictionary
        index: Product index in array (for error messages)

    Returns:
        List of validation errors for this product
    """
    errors = []
    prefix = f"Product {index}"

    # Required fields
    if not product.get("id"):
        errors.append(f"{prefix}: missing id")

    if not product.get("quantity"):
        errors.append(f"{prefix}: missing quantity")
    elif not isinstance(product["quantity"], (int, float)) or product["quantity"] <= 0:
        errors.append(f"{prefix}: invalid quantity (must be > 0)")

    if "sale_price" not in product:
        errors.append(f"{prefix}: missing sale_price")
    elif (
        not isinstance(product["sale_price"], (int, float)) or product["sale_price"] < 0
    ):
        errors.append(f"{prefix}: invalid sale_price (must be >= 0)")

    # Product status (0 or 1)
    if "status" not in product:
        errors.append(f"{prefix}: missing status")
    elif product["status"] not in [0, 1]:
        errors.append(f"{prefix}: invalid status (must be 0 or 1)")

    # Optional but validated if present
    if "vat" in product:
        vat = product["vat"]
        if not isinstance(vat, (int, float)) or vat < 0 or vat > 100:
            errors.append(f"{prefix}: invalid vat (must be 0-100)")

    return errors


def _validate_customer_data(customer: dict[str, Any]) -> list[str]:
    """
    Validate customer information.

    Args:
        customer: Customer data dictionary

    Returns:
        List of validation errors
    """
    errors = []

    # Required customer fields
    if not customer.get("name"):
        errors.append("Customer: missing name")

    if not customer.get("phone1"):
        errors.append("Customer: missing phone1")

    # Email validation (basic)
    if customer.get("email"):
        email = customer["email"]
        if "@" not in email or "." not in email:
            errors.append(f"Customer: invalid email format: {email}")

    return errors


def validate_order_for_update(order_data: dict[str, Any]) -> list[str]:
    """
    Validate order data for update operations.

    Args:
        order_data: Order data for update

    Returns:
        List of validation errors
    """
    errors = []

    # For updates, order ID is required
    if not order_data.get("id"):
        errors.append("Order ID is required for updates")

    # Validate status if present
    if "status" in order_data:
        status = order_data["status"]
        if status not in [0, 1, 2, 3, 4, 5]:
            errors.append(f"Invalid status: {status} (must be 0-5)")

    # If status is being updated to canceled, cancellation_reason should be present
    if order_data.get("status") == 0:  # Canceled
        if not order_data.get("cancellation_reason"):
            errors.append("Cancellation reason is required when canceling an order")

    return errors


def validate_order_cancellation(order_id: str, cancellation_reason: int) -> list[str]:
    """
    Validate order cancellation request.

    Args:
        order_id: eMAG order ID
        cancellation_reason: Cancellation reason code (1-39)

    Returns:
        List of validation errors
    """
    errors = []

    if not order_id:
        errors.append("Order ID is required")

    # Valid cancellation reason codes from CANCELLATION_REASONS
    valid_codes = [
        1,
        2,
        3,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
    ]
    if cancellation_reason not in valid_codes:
        errors.append(f"Invalid cancellation reason: {cancellation_reason}")

    return errors


def validate_bulk_order_update(orders: list[dict[str, Any]]) -> dict[str, list[str]]:
    """
    Validate multiple orders for bulk update.

    Args:
        orders: List of order data dictionaries

    Returns:
        Dictionary mapping order IDs to their validation errors
    """
    validation_results = {}

    for order in orders:
        order_id = order.get("id", "unknown")
        errors = validate_order_for_update(order)
        if errors:
            validation_results[str(order_id)] = errors

    return validation_results
