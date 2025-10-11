"""
Data transformation utilities for eMAG integration.

Provides functions to transform eMAG API responses into internal data structures.
"""

from datetime import datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def transform_product_response(product: dict[str, Any]) -> dict[str, Any]:
    """
    Transform eMAG product response to internal format.

    Args:
        product: Raw product data from eMAG API

    Returns:
        Transformed product data
    """
    try:
        transformed = {
            "emag_id": int(product.get("id", 0)),
            "name": str(product.get("name", "")).strip(),
            "part_number": product.get("part_number"),
            "ean": product.get("ean"),
            "brand": product.get("brand"),
            "category_id": product.get("category_id"),
            "status": product.get("status", 0),
            "is_active": bool(product.get("status", 0) == 1),
            "sale_price": _parse_price(product.get("sale_price")),
            "recommended_price": _parse_price(product.get("recommended_price")),
            "stock": _parse_stock(product.get("stock")),
            "vat_rate": _parse_vat_rate(product.get("vat_rate")),
            "warranty": product.get("warranty"),
            "description": product.get("description"),
            "images": _extract_images(product.get("images", [])),
            "characteristics": product.get("characteristics", []),
            "updated_at": _parse_datetime(product.get("modified")),
            "created_at": _parse_datetime(product.get("created")),
        }

        # Remove None values
        transformed = {k: v for k, v in transformed.items() if v is not None}

        logger.debug(f"Transformed product: {transformed.get('emag_id')}")
        return transformed

    except Exception as e:
        logger.error(f"Error transforming product: {e}", exc_info=True)
        raise


def transform_order_response(order: dict[str, Any]) -> dict[str, Any]:
    """
    Transform eMAG order response to internal format.

    Args:
        order: Raw order data from eMAG API

    Returns:
        Transformed order data
    """
    try:
        transformed = {
            "emag_id": int(order.get("id", 0)),
            "order_number": str(order.get("order_number", "")),
            "status": order.get("status"),
            "payment_mode": order.get("payment_mode"),
            "payment_mode_id": order.get("payment_mode_id"),
            "shipping_mode": order.get("shipping_mode"),
            "customer_name": order.get("customer", {}).get("name"),
            "customer_email": order.get("customer", {}).get("email"),
            "customer_phone": order.get("customer", {}).get("phone"),
            "total_amount": _parse_price(order.get("total_amount")),
            "shipping_cost": _parse_price(order.get("shipping_cost")),
            "currency": order.get("currency", "RON"),
            "products": _transform_order_products(order.get("products", [])),
            "shipping_address": order.get("shipping_address"),
            "billing_address": order.get("billing_address"),
            "observations": order.get("observations"),
            "created_at": _parse_datetime(order.get("date")),
            "updated_at": _parse_datetime(order.get("modified")),
        }

        # Remove None values
        transformed = {k: v for k, v in transformed.items() if v is not None}

        logger.debug(f"Transformed order: {transformed.get('emag_id')}")
        return transformed

    except Exception as e:
        logger.error(f"Error transforming order: {e}", exc_info=True)
        raise


def _parse_price(value: Any) -> float | None:
    """Parse price value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid price value: {value}")
        return None


def _parse_stock(value: Any) -> int | None:
    """Parse stock value to integer."""
    if value is None:
        return None

    # Handle stock as list (eMAG format)
    if isinstance(value, list) and len(value) > 0:
        stock_item = value[0]
        if isinstance(stock_item, dict):
            value = stock_item.get("value", 0)

    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid stock value: {value}")
        return 0


def _parse_vat_rate(value: Any) -> float | None:
    """Parse VAT rate to float."""
    if value is None:
        return None
    try:
        rate = float(value)
        # Convert percentage to decimal if needed
        if rate > 1:
            rate = rate / 100
        return rate
    except (ValueError, TypeError):
        logger.warning(f"Invalid VAT rate: {value}")
        return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse datetime string to datetime object."""
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        # Try ISO format
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        try:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S"]:
                try:
                    return datetime.strptime(str(value), fmt)
                except ValueError:
                    continue
        except Exception:
            pass

    logger.warning(f"Could not parse datetime: {value}")
    return None


def _extract_images(images: list[Any]) -> list[str]:
    """Extract image URLs from images data."""
    if not images:
        return []

    urls = []
    for img in images:
        if isinstance(img, dict):
            url = img.get("url") or img.get("display_url")
            if url:
                urls.append(str(url))
        elif isinstance(img, str):
            urls.append(img)

    return urls


def _transform_order_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform order products to internal format."""
    transformed_products = []

    for product in products:
        try:
            transformed = {
                "emag_product_id": int(product.get("id", 0)),
                "name": str(product.get("name", "")).strip(),
                "quantity": int(product.get("quantity", 1)),
                "sale_price": _parse_price(product.get("sale_price")),
                "vat_rate": _parse_vat_rate(product.get("vat")),
                "status": product.get("status"),
            }
            transformed_products.append(transformed)
        except Exception as e:
            logger.warning(f"Error transforming order product: {e}")
            continue

    return transformed_products
