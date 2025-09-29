import sys
from importlib.util import find_spec

if find_spec("greenlet") is None:
    print("Error: The 'greenlet' package is required for async database operations.")
    print(
        "Please install it by running: /Users/macos/anaconda3/envs/MagFlow/bin/pip install greenlet"
    )
    sys.exit(1)

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import backoff
import inspect
from sqlalchemy import select, exc as sa_exc, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import noload

# Import application components
try:
    from app.core.config import settings
    from app.core.database_resilience import DatabaseConfig, DatabaseHealthChecker
    from app.core.dependency_injection import ServiceContext
    from app.core.schema_validator import (
        validate_sync_environment,
        print_validation_report,
    )
    from app.core.service_registry import ServiceRegistry
    from app.db.session import AsyncSessionLocal
    from app.models.order import Order, OrderLine
    from app.models.product import Product
    from app.models.user import User
    from app.services.emag_integration_service import EmagIntegrationService
    from app.core.security import get_password_hash
except ImportError as e:
    print(f"Error importing application components: {e}", file=sys.stderr)
    print(f"Current sys.path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# Configure logging
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_level = logging.DEBUG  # Set to DEBUG for more detailed logs

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[logging.StreamHandler(), logging.FileHandler(log_dir / "order_sync.log")],
)

# Set log level for specific loggers
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Main logger
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# Configure backoff for retry logic
BACKOFF_CONFIG = {
    "max_tries": 5,
    "max_time": 300,  # 5 minutes max
    "jitter": backoff.full_jitter,
    "giveup": lambda e: not (
        isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError, sa_exc.DBAPIError))
    ),
}

# Global variables
current_sync_id = None
STATS = {
    "orders_processed": 0,
    "inventory_updates": 0,
    "errors": 0,
    "retries": 0,
    "start_time": None,
    "last_progress_update": None,
}


# Sync configuration helpers
@dataclass(frozen=True)
class OrderSyncConfig:
    max_pages: int = 100
    delay_between_requests: float = 1.0
    requests_per_minute: int = 60

    @property
    def effective_delay(self) -> float:
        requests_per_minute = max(1, self.requests_per_minute)
        rpm_delay = 60.0 / requests_per_minute
        return max(self.delay_between_requests, rpm_delay)


def _get_config_value(
    keys: Tuple[str, ...],
    cast,
    default,
    *,
    account_type: Optional[str] = None,
) -> Any:
    """Retrieve configuration values from env or settings with graceful fallback."""

    def _attempt_cast(value: Any) -> Any:
        if value is None or value == "":
            return None
        try:
            return cast(value)
        except (TypeError, ValueError):
            logger.warning(
                "Invalid value '%s' for configuration keys %s; falling back to default %s",
                value,
                keys,
                default,
            )
            return None

    scoped_keys = []
    if account_type:
        scoped_keys.extend(f"{key}_{account_type.upper()}" for key in keys)
    scoped_keys.extend(keys)

    for key in scoped_keys:
        if key in os.environ:
            cast_value = _attempt_cast(os.getenv(key))
            if cast_value is not None:
                return cast_value
    for key in scoped_keys:
        if hasattr(settings, key):
            cast_value = _attempt_cast(getattr(settings, key))
            if cast_value is not None:
                return cast_value

    return default


def load_order_sync_config(account_type: str) -> OrderSyncConfig:
    """Load sync configuration aligned with the documented eMAG guide."""

    max_pages = _get_config_value(
        ("EMAG_MAX_PAGES_PER_SYNC",),
        int,
        100,
        account_type=account_type,
    )
    delay_between_requests = _get_config_value(
        ("EMAG_DELAY_BETWEEN_REQUESTS",),
        float,
        1.0,
        account_type=account_type,
    )
    requests_per_minute = _get_config_value(
        ("EMAG_REQUESTS_PER_MINUTE",),
        int,
        60,
        account_type=account_type,
    )

    config = OrderSyncConfig(
        max_pages=max(1, max_pages),
        delay_between_requests=max(0.0, delay_between_requests),
        requests_per_minute=max(1, requests_per_minute),
    )
    logger.debug(
        "Loaded order sync config for %s: %s",
        account_type.upper(),
        config,
    )
    return config


# Performance metrics
class PerformanceMetrics:
    def __init__(self):
        self.metrics = {
            "api_calls": 0,
            "db_queries": 0,
            "processing_time": 0.0,
            "api_response_time": 0.0,
            "db_query_time": 0.0,
            "orders_with_missing_products": 0,
            "missing_product_occurrences": 0,
            "missing_product_counts": defaultdict(int),
            "missing_products": set(),
        }

    def record_metric(self, metric: str, value: float = 1.0):
        current_value = self.metrics.get(metric)
        if isinstance(current_value, (int, float)):
            self.metrics[metric] = current_value + value
        else:
            self.metrics[metric] = value

    def record_missing_product(self, product_id: int):
        self.metrics["missing_products"].add(product_id)
        self.metrics["missing_product_counts"][product_id] += 1
        self.metrics["missing_product_occurrences"] += 1

    def mark_order_with_missing_product(self):
        self.metrics["orders_with_missing_products"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        serialized: Dict[str, Any] = {}
        for key, value in self.metrics.items():
            if isinstance(value, set):
                serialized[key] = sorted(value)
            elif isinstance(value, defaultdict):
                serialized[key] = dict(value)
            else:
                serialized[key] = value
        return serialized


metrics = PerformanceMetrics()

ORDER_STATUS_MAPPING = {
    0: "cancelled",
    1: "new",
    2: "in_progress",
    3: "prepared",
    4: "finalized",
    5: "returned",
}


def _to_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Safely convert arbitrary payload values to ``Decimal``.

    Args:
        value: Incoming value from eMAG payload.
        default: Value to return when conversion fails.

    Returns:
        Decimal representation of the input, or ``default`` when parsing fails.
    """

    if value is None:
        return default

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return default
        try:
            return Decimal(candidate)
        except InvalidOperation:
            return default

    return default


def _extract_quantity(item: Dict[str, Any]) -> int:
    """Extract quantity information from a product payload."""

    for key in ("quantity", "qty", "quantity_ordered", "ordered_quantity"):
        value = item.get(key)
        if value is None:
            continue
        try:
            qty = int(value)
            if qty > 0:
                return qty
        except (TypeError, ValueError):
            continue
    return 1


def _extract_unit_price(item: Dict[str, Any]) -> Decimal:
    """Determine the best price candidate for a product line."""

    for key in ("sale_price", "price", "unit_price", "value", "product_price"):
        price = _to_decimal(item.get(key))
        if price > 0:
            return price
    return Decimal("0")


def _extract_line_total(
    item: Dict[str, Any], quantity: int, unit_price: Decimal
) -> Decimal:
    """Compute the line total, falling back to price * quantity when needed."""

    for key in ("line_total", "total", "line_value", "amount"):
        total = _to_decimal(item.get(key))
        if total > 0:
            return total
    if unit_price > 0 and quantity > 0:
        return unit_price * quantity
    return Decimal("0")


def _extract_order_total(
    order_data: Dict[str, Any], line_total_sum: Decimal
) -> Decimal:
    """Determine the overall order total using multiple fallback fields."""

    possible_paths = (
        ("total",),
        ("grand_total",),
        ("final_price",),
        ("payment", "amount"),
        ("totals", "grand_total"),
        ("totals", "total"),
    )

    for path in possible_paths:
        cursor: Any = order_data
        for key in path:
            if not isinstance(cursor, dict):
                cursor = None
                break
            cursor = cursor.get(key)
        total = _to_decimal(cursor)
        if total > 0:
            return total

    if line_total_sum > 0:
        return line_total_sum

    return Decimal("0")


# Backoff configuration for API requests
BACKOFF_CONFIG = {
    "max_tries": 5,
    "jitter": backoff.full_jitter,
    "max_time": 300,  # 5 minutes max
    "on_backoff": lambda details: logger.warning(
        f"Retrying API call (attempt {details['tries']}): {details.get('exception', 'Unknown error')}"
    ),
}


@backoff.on_exception(
    backoff.expo,
    (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        sa_exc.DBAPIError,
        ValueError,
        AttributeError,
    ),
    **BACKOFF_CONFIG,
)
async def _make_api_request(
    service: EmagIntegrationService, method: str, endpoint: str, **kwargs
) -> Dict[str, Any]:
    """Make an API request with retry logic and metrics."""
    start_time = time.monotonic()
    metrics.record_metric("api_calls")

    try:
        # Log the request details for debugging
        logger.debug(f"Making {method.upper()} request to endpoint: {endpoint}")
        logger.debug(
            f"Request params: {json.dumps(kwargs.get('params', {}), indent=2)}"
        )

        # Log available attributes of the API client for debugging
        if hasattr(service, "api_client"):
            logger.debug(f"API client attributes: {', '.join(dir(service.api_client))}")
            if hasattr(service.api_client, "_api_url"):
                logger.debug(
                    f"API base URL from _api_url: {service.api_client._api_url}"
                )

        # Check if API client is initialized
        if not hasattr(service, "api_client") or service.api_client is None:
            raise ValueError("API client not initialized in the service")

        # Prepare request parameters
        params = kwargs.get("params", {})

        # For eMAG API, we need to use the appropriate method based on the endpoint
        if endpoint == "order/read":
            # Use the api_client's method directly
            if hasattr(service.api_client, "get_orders"):
                sig = inspect.signature(service.api_client.get_orders)

                start_date = params.get("start_date")
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(
                        start_date.replace("Z", "+00:00")
                    )

                end_date = params.get("end_date")
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

                call_args = {
                    "start_date": start_date,
                    "end_date": end_date,
                    "page": params.get("page", 1),
                }

                per_page_value = params.get("per_page", 50)
                if "per_page" in sig.parameters:
                    call_args["per_page"] = per_page_value
                if "items_per_page" in sig.parameters:
                    call_args["items_per_page"] = per_page_value

                logger.debug(f"Calling get_orders with args: {call_args}")
                response = await service.api_client.get_orders(**call_args)
            else:
                # Fallback to _make_request if get_orders method doesn't exist
                response = await service.api_client._make_request(
                    "GET",
                    "order/read",
                    params={
                        "start_date": params.get("start_date"),
                        "end_date": params.get("end_date"),
                        "page": params.get("page", 1),
                        "per_page": params.get("per_page", 50),
                    },
                )
        else:
            # Fallback to generic request handling
            if method.lower() == "get":
                if hasattr(service.api_client, "get"):
                    response = await service.api_client.get(endpoint, **kwargs)
                else:
                    response = await service.api_client._make_request(
                        "GET", endpoint, **kwargs
                    )
            elif method.lower() == "post":
                if hasattr(service.api_client, "post"):
                    response = await service.api_client.post(endpoint, **kwargs)
                else:
                    response = await service.api_client._make_request(
                        "POST", endpoint, **kwargs
                    )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        # Log successful response
        response_time = time.monotonic() - start_time
        metrics.record_metric("api_response_time", response_time)
        logger.debug(f"API request to {endpoint} completed in {response_time:.2f}s")

        return response

    except Exception as e:
        error_message = f"API request to {endpoint} failed: {str(e)}"
        logger.error(error_message, exc_info=True)
        metrics.record_metric("errors")
        metrics.record_metric("api_retries")
        raise


async def ensure_default_customer(session: AsyncSession) -> int:
    """Ensure default customer exists and return its ID.

    This function is designed to be resilient to schema changes by:
    1. Using raw SQL to avoid ORM model dependencies
    2. Implementing retry logic for transient failures
    3. Providing fallback behavior when possible
    """
    DEFAULT_CUSTOMER_ID = 4
    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            # First try to get the customer using raw SQL to avoid ORM model issues
            query = text(
                """
                SELECT id FROM app.users
                WHERE id = :customer_id
                """
            )
            result = await session.execute(query, {"customer_id": DEFAULT_CUSTOMER_ID})
            customer_id = result.scalar_one_or_none()

            if customer_id:
                logger.debug(f"Found existing default customer with ID: {customer_id}")
                return customer_id

            # If customer doesn't exist, try to create it
            try:
                query = text(
                    """
                    INSERT INTO app.users
                    (id, email, full_name, is_active, is_superuser, hashed_password, created_at, updated_at)
                    VALUES
                    (:id, :email, :full_name, true, false, '', NOW(), NOW())
                    RETURNING id
                    """
                )
                result = await session.execute(
                    query,
                    {
                        "id": DEFAULT_CUSTOMER_ID,
                        "email": "default@customer.com",
                        "full_name": "Default Customer",
                    },
                )
                customer_id = result.scalar_one()
                await session.commit()
                logger.info(f"Created default customer with ID: {customer_id}")
                return customer_id

            except Exception as create_error:
                await session.rollback()
                # If we get a unique violation, the customer was created by another process
                if "unique constraint" in str(create_error).lower():
                    logger.debug("Customer already exists, retrying fetch")
                    continue
                raise

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed to ensure default customer: {str(e)[:200]}"
                )
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue

            # Last attempt failed, log and use a fallback
            logger.error(
                f"All attempts to ensure default customer failed. Error: {str(e)[:500]}"
            )
            return DEFAULT_CUSTOMER_ID  # Return default ID as fallback


async def upsert_customer_from_order(
    session: AsyncSession,
    order_data: Dict[str, Any],
    fallback_customer_id: int,
) -> int:
    """Create or update a customer based on the order payload."""

    customer_payload: Dict[str, Any] = order_data.get("customer") or {}
    if not customer_payload:
        return fallback_customer_id

    raw_email = (customer_payload.get("email") or "").strip().lower()
    customer_identifier = (
        customer_payload.get("id")
        or order_data.get("customer_id")
        or order_data.get("id")
    )

    if not raw_email:
        if customer_identifier is None:
            return fallback_customer_id
        raw_email = f"emag-customer-{customer_identifier}@magflow-sync.local"

    existing_customer = (
        await session.execute(
            select(User).options(noload(User.roles)).where(User.email == raw_email)
        )
    ).scalar_one_or_none()

    full_name = (
        customer_payload.get("name") or customer_payload.get("full_name") or ""
    ).strip()

    if existing_customer:
        updated = False
        if full_name and existing_customer.full_name != full_name:
            existing_customer.full_name = full_name
            updated = True
        if not existing_customer.is_active:
            existing_customer.is_active = True
            updated = True
        if updated:
            session.add(existing_customer)
        return existing_customer.id

    hashed_password = get_password_hash(f"external-sync-{raw_email}")
    new_customer = User(
        email=raw_email,
        hashed_password=hashed_password,
        full_name=full_name or raw_email,
        is_active=True,
        is_superuser=False,
    )

    session.add(new_customer)
    await session.flush()
    return new_customer.id


async def _create_missing_product(
    db_session: AsyncSession,
    product_id: int,
    *,
    name: Optional[str] = None,
    sku: Optional[str] = None,
) -> int:
    """Create or update a placeholder product for missing IDs.

    Args:
        db_session: Active database session.
        product_id: Identifier reported by eMAG.
        name: Optional descriptive name from the payload.
        sku: Optional SKU information from the payload.

    Returns:
        The product ID that now exists in the database.
    """
    try:
        # Check if placeholder already exists
        result = await db_session.execute(
            select(Product).where(Product.id == product_id)
        )
        if result.scalar_one_or_none() is not None:
            return product_id

        # Create placeholder product
        placeholder = Product(
            id=product_id,
            name=(name or f"[MISSING] Product {product_id}"),
            sku=(sku or f"MISSING-{product_id}"),
            is_active=False,
            is_placeholder=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(placeholder)
        await db_session.flush()
        logger.info(f"Created placeholder product for missing ID: {product_id}")
        return product_id

    except Exception as e:
        logger.error(f"Error creating placeholder product {product_id}: {str(e)}")
        # Don't raise, as we want to continue processing
        return product_id


async def _process_order_batch(
    orders: List[Dict[str, Any]],
    service: EmagIntegrationService,
    account_type: str,
    force_update: bool = False,
    start_date_filter: Optional[datetime] = None,
    end_date_filter: Optional[datetime] = None,
) -> Tuple[int, int, int]:
    """Process a batch of orders with transaction management."""
    success_count = 0
    error_count = 0
    skipped_count = 0

    # Get a new session for this batch to avoid connection issues
    async with AsyncSessionLocal() as batch_session:
        try:
            # Ensure default customer exists
            try:
                fallback_customer_id = await ensure_default_customer(batch_session)
                logger.debug(f"Using fallback customer ID: {fallback_customer_id}")
            except Exception as e:
                logger.error(f"Failed to ensure default customer: {e}")
                return 0, len(orders)  # Mark all as errors if we can't get a customer

            # Process each order in the batch
            for order_data in orders:
                order_id = None
                try:
                    order_id = order_data.get("id")
                    if not order_id:
                        logger.warning("Order missing 'id' field, skipping")
                        error_count += 1
                        continue

                    # Log order details for debugging
                    logger.info(f"Processing order ID: {order_id}")
                    logger.debug(f"Order status: {order_data.get('status')}")
                    logger.debug(f"Order date: {order_data.get('date')}")
                    logger.debug(
                        f"Customer: {order_data.get('customer', {}).get('name')}"
                    )
                    logger.debug(
                        f"Total: {order_data.get('total')} {order_data.get('currency')}"
                    )

                    # Log the first few items in the order
                    products = order_data.get("products", [])
                    if products:
                        logger.info(f"Order contains {len(products)} products")
                        for i, product in enumerate(products[:3], 1):
                            logger.debug(
                                f"  {i}. {product.get('name')} x{product.get('quantity')}"
                            )

                    # Parse order date before touching the database
                    order_date_str = order_data.get("date")
                    order_date = datetime.now(
                        timezone.utc
                    )  # Default to now if no date provided
                    if order_date_str:
                        try:
                            parsed_date = datetime.fromisoformat(
                                order_date_str.replace("Z", "+00:00")
                            )
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                            order_date = parsed_date.astimezone(timezone.utc)
                        except (ValueError, AttributeError) as e:
                            logger.warning(
                                "Invalid order date format: %s, using current time: %s",
                                order_date_str,
                                e,
                            )

                    if start_date_filter and order_date < start_date_filter:
                        logger.debug(
                            "⏭️  Skipping order %s dated %s (before start_date %s) - OLD ORDER",
                            order_id,
                            (
                                order_date.isoformat()
                                if isinstance(order_date, datetime)
                                else order_date
                            ),
                            start_date_filter.isoformat(),
                        )
                        skipped_count += 1
                        continue
                    if end_date_filter and order_date > end_date_filter:
                        logger.debug(
                            "Skipping order %s dated %s (after end_date %s)",
                            order_id,
                            (
                                order_date.isoformat()
                                if isinstance(order_date, datetime)
                                else order_date
                            ),
                            end_date_filter.isoformat(),
                        )
                        skipped_count += 1
                        continue

                    # Start a new transaction for this order
                    async with batch_session.begin_nested():
                        try:
                            customer_id = await upsert_customer_from_order(
                                batch_session,
                                order_data,
                                fallback_customer_id,
                            )

                            # Check if order already exists
                            existing_order = await batch_session.execute(
                                select(Order).where(
                                    Order.external_id == str(order_id),
                                    Order.external_source
                                    == f"emag_{account_type.lower()}",
                                )
                            )
                            existing_order = existing_order.scalar_one_or_none()

                            if existing_order and not force_update:
                                logger.debug(
                                    f"Order {order_id} already exists in database, skipping"
                                )
                                success_count += 1
                                continue

                            if existing_order and force_update:
                                logger.info(
                                    f"Order {order_id} exists, updating as --force-update is enabled"
                                )

                            # Determine status code using documented mapping
                            status_code = order_data.get("status", 0)
                            status = ORDER_STATUS_MAPPING.get(status_code, "unknown")

                            # Prepare order lines using helper extractors
                            prepared_lines: List[Tuple[int, int, Decimal]] = []
                            line_total_sum = Decimal("0")
                            order_missing_products = False

                            for item in products:
                                product_id = item.get("product_id") or item.get("id")
                                if not product_id:
                                    logger.warning(
                                        f"Product missing ID in order {order_id}, skipping line"
                                    )
                                    continue

                                try:
                                    product_id_int = int(product_id)
                                except (TypeError, ValueError):
                                    logger.warning(
                                        f"Invalid product ID '{product_id}' in order {order_id}"
                                    )
                                    error_count += 1
                                    continue

                                quantity = _extract_quantity(item)
                                unit_price = _extract_unit_price(item)
                                line_total = _extract_line_total(
                                    item, quantity, unit_price
                                )
                                line_total_sum += line_total

                                product = await batch_session.execute(
                                    select(Product).where(Product.id == product_id_int)
                                )
                                product = product.scalar_one_or_none()

                                if not product or not getattr(
                                    product, "is_active", True
                                ):
                                    logger.warning(
                                        f"Product with ID {product_id_int} not found or inactive, creating placeholder"
                                    )
                                    created_product_id = await _create_missing_product(
                                        batch_session,
                                        product_id_int,
                                        name=item.get("name"),
                                        sku=item.get("sku") or item.get("product_sku"),
                                    )
                                    order_missing_products = True
                                    metrics.record_missing_product(created_product_id)

                                prepared_lines.append(
                                    (product_id_int, quantity, unit_price)
                                )

                            if order_missing_products:
                                metrics.mark_order_with_missing_product()

                            order_total = _extract_order_total(
                                order_data, line_total_sum
                            )

                            if existing_order:
                                target_order = existing_order
                                target_order.customer_id = customer_id
                                target_order.order_date = order_date
                                target_order.status = status
                                target_order.total_amount = float(order_total)

                                if force_update:
                                    await batch_session.execute(
                                        text(
                                            "DELETE FROM app.order_lines WHERE order_id = :order_id"
                                        ),
                                        {"order_id": existing_order.id},
                                    )
                            else:
                                target_order = Order(
                                    customer_id=customer_id,
                                    order_date=order_date,
                                    status=status,
                                    total_amount=float(order_total),
                                    external_id=str(order_id),
                                    external_source=f"emag_{account_type.lower()}",
                                )
                                batch_session.add(target_order)
                                await batch_session.flush()

                            # Attach order lines
                            for product_id_int, quantity, unit_price in prepared_lines:
                                order_line = OrderLine(
                                    order_id=target_order.id,
                                    product_id=product_id_int,
                                    quantity=quantity,
                                    unit_price=float(unit_price),
                                )
                                batch_session.add(order_line)

                            # Commit the nested transaction for this order
                            await batch_session.commit()
                            logger.info(
                                f"Successfully saved order {order_id} to database"
                            )
                            success_count += 1
                            metrics.record_metric("orders_processed")

                            # Log progress every 5 orders
                            if success_count % 5 == 0:
                                logger.info(
                                    f"Processed {success_count} orders so far (last ID: {order_id})"
                                )
                            else:
                                logger.info(f"Processed order {order_id} successfully")

                        except Exception as e:
                            await batch_session.rollback()
                            if (
                                "unique constraint" in str(e).lower()
                                or "duplicate key" in str(e).lower()
                            ):
                                logger.warning(
                                    f"Duplicate data detected for order {order_id}: {str(e)}"
                                )
                                success_count += (
                                    1  # Count as success since it already exists
                                )
                            else:
                                logger.error(
                                    f"Database error for order {order_id}: {str(e)}"
                                )
                                error_count += 1
                                metrics.record_metric("errors")

                except Exception as e:
                    logger.error(
                        f"Error processing order {order_id if order_id else 'unknown'}: {str(e)}"
                    )
                    error_count += 1
                    metrics.record_metric("errors")

            # Commit any remaining changes
            await batch_session.commit()

        except Exception as e:
            await batch_session.rollback()
            logger.error(f"Error in batch processing: {str(e)}")
            error_count = len(orders)  # Mark all as errors if batch fails
            metrics.record_metric("errors", len(orders))

    # Log batch completion with old order summary
    old_orders_count = 0
    for order in orders:
        order_date_str = order.get("date")
        if order_date_str and start_date_filter:
            try:
                # Parse the order date with proper timezone handling
                parsed_date = datetime.fromisoformat(
                    order_date_str.replace("Z", "+00:00")
                )
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                parsed_date = parsed_date.astimezone(timezone.utc)

                if parsed_date < start_date_filter:
                    old_orders_count += 1
            except (ValueError, TypeError):
                # Skip orders with invalid dates
                continue

    logger.info(
        "✅ Completed processing batch: %s successful, %s errors, %s skipped (%s were old orders from before %s)",
        success_count,
        error_count,
        skipped_count,
        old_orders_count,
        start_date_filter.strftime("%Y-%m-%d") if start_date_filter else "start_date",
    )
    return success_count, error_count, skipped_count


async def sync_orders(
    account_type: str,
    days: int = 1,
    batch_size: int = 20,  # Reduced batch size to prevent connection issues
    max_concurrent: int = 3,  # Reduced concurrency to prevent connection exhaustion
    force_update: bool = False,
    show_summary: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Synchronize orders for a specific account type with enhanced error handling and performance."""
    global STATS
    STATS["start_time"] = time.time()
    STATS["last_progress_update"] = STATS["start_time"]
    STATS["orders_processed"] = 0
    STATS["errors"] = 0

    logger.info(
        f"Starting order sync for {account_type.upper()} account (last {days} days)"
    )

    sync_config = load_order_sync_config(account_type)
    page_size = max(1, min(batch_size, 100))
    if page_size != batch_size:
        logger.info(
            "Requested batch size %s capped to %s to respect eMAG API page limits",
            batch_size,
            page_size,
        )

    # Initialize database connection
    engine = None
    service = None

    try:
        # Initialize database connection
        db_config = DatabaseConfig()
        engine = db_config.create_optimized_engine()

        # Initialize services
        service: EmagIntegrationService = await _init_emag_service(account_type)

        # Debug: Log service details
        logger.debug(f"Initialized service for {account_type.upper()} account")
        logger.debug(
            f"Service config: username={service.config.api_username[:10]}..., account_type={service.account_type}"
        )
        if hasattr(service, "api_client") and service.api_client:
            logger.debug(
                f"API client: username={service.api_client.username[:10]}..., account_type={getattr(service.api_client, 'account_type', 'NOT_SET')}"
            )

        # Calculate date range
        end_date: datetime = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Optimize date range to avoid fetching very old orders
        # Add buffer days to start_date to account for API behavior
        buffer_days = 90  # Skip orders older than 90 days to reduce API load
        optimized_start_date = end_date - timedelta(days=days + buffer_days)

        # Fetch and process orders in batches
        page = 1
        total_processed = 0
        total_errors = 0
        total_skipped = 0
        has_more = True

        while has_more:
            try:
                if page > sync_config.max_pages:
                    logger.info(
                        "Reached configured maximum of %s pages for %s account; stopping pagination",
                        sync_config.max_pages,
                        account_type.upper(),
                    )
                    break

                # Fetch orders with retry
                logger.info(f"Fetching page {page} with batch size {page_size}")
                orders = await _make_api_request(
                    service=service,
                    method="get",
                    endpoint="order/read",
                    params={
                        "start_date": optimized_start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "page": page,
                        "per_page": page_size,
                    },
                )

                if not orders or not orders.get("results"):
                    logger.info(f"No more orders found in page {page}")
                    has_more = False
                    break

                # Log the number of orders received
                logger.info(
                    f"Processing {len(orders['results'])} orders from page {page}"
                )

                # Early exit if API returns only very old orders (more than 30 days before requested range)
                current_orders = orders["results"]
                if current_orders:
                    oldest_order_date = None
                    for order in current_orders:
                        order_date_str = order.get("date")
                        if order_date_str:
                            try:
                                parsed_date = datetime.fromisoformat(
                                    order_date_str.replace("Z", "+00:00")
                                )
                                if parsed_date.tzinfo is None:
                                    parsed_date = parsed_date.replace(
                                        tzinfo=timezone.utc
                                    )
                                parsed_date = parsed_date.astimezone(timezone.utc)
                                if (
                                    oldest_order_date is None
                                    or parsed_date < oldest_order_date
                                ):
                                    oldest_order_date = parsed_date
                            except (ValueError, TypeError):
                                continue

                    if oldest_order_date and start_date:
                        days_difference = (start_date - oldest_order_date).days
                        if (
                            days_difference > 30
                        ):  # If oldest order is more than 30 days before our target
                            logger.info(
                                f"🚫 API returned very old orders (oldest: {oldest_order_date.strftime('%Y-%m-%d')}, "
                                f"target start: {start_date.strftime('%Y-%m-%d')}). Stopping early to save API calls."
                            )
                            has_more = False
                            break

                # Process orders in smaller batches to prevent connection issues
                batch_errors = 0
                batch_processed = 0

                # Process orders in smaller chunks to prevent connection exhaustion
                chunk_size = min(5, len(orders["results"]))
                for i in range(0, len(orders["results"]), chunk_size):
                    chunk = orders["results"][i : i + chunk_size]

                    processed, errors, skipped = await _process_order_batch(
                        chunk,
                        service,
                        account_type,
                        force_update=force_update,
                        start_date_filter=start_date,
                        end_date_filter=end_date,
                    )

                    batch_processed += processed
                    batch_errors += errors
                    total_skipped += skipped
                    total_processed += processed
                    total_errors += errors
                    STATS["orders_processed"] = total_processed
                    STATS["errors"] = total_errors

                    if limit is not None and (total_processed + total_skipped) >= limit:
                        logger.info(
                            "Reached requested limit of %s processed orders; stopping early",
                            limit,
                        )
                        has_more = False
                        break

                if not has_more:
                    break

                if len(orders["results"]) < page_size:
                    logger.info(f"No more orders found in page {page}")
                    has_more = False
                    break

                # Log progress periodically
                current_time = time.time()
                if (
                    current_time - STATS["last_progress_update"] > 30
                ):  # Every 30 seconds
                    _log_progress(account_type, total_processed, total_errors)
                    STATS["last_progress_update"] = current_time

                # Small delay between pages to be nice to the API
                await asyncio.sleep(sync_config.effective_delay)

            except Exception as e:
                logger.error(f"Error in batch processing: {str(e)}", exc_info=True)
                metrics.record_metric("errors")
                if page > 1:  # Don't retry on first page to avoid infinite loops
                    break
                raise

        # Final progress update
        _log_progress(account_type, total_processed, total_errors)

        # Generate report
        duration = time.time() - STATS["start_time"]
        report = {
            "status": "success",
            "account_type": account_type,
            "processed": total_processed,
            "errors": total_errors,
            "duration_seconds": round(duration, 2),
            "metrics": metrics.get_metrics(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Completed order sync for {account_type.upper()}: {json.dumps(report, indent=2)}"
        )
        return report

    except Exception as e:
        logger.error(
            f"Fatal error in order sync for {account_type.upper()}: {str(e)}",
            exc_info=True,
        )
        return {
            "status": "error",
            "account_type": account_type,
            "error": str(e),
            "processed": STATS.get("orders_processed", 0),
            "errors": STATS.get("errors", 0) + 1,
            "duration_seconds": round(
                time.time() - STATS.get("start_time", time.time()), 2
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    finally:
        # Clean up resources
        if engine:
            await engine.dispose()
        if hasattr(service, "cleanup") and callable(service.cleanup):
            await service.cleanup()


async def _init_services(account_type: str):
    """Initialize database and health checker with retry logic."""
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            engine = DatabaseConfig.create_optimized_engine()
            async_session_factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            health_checker = DatabaseHealthChecker(async_session_factory)
            await health_checker.ensure_healthy()
            return engine

        except Exception as e:
            last_error = e
            wait_time = (attempt + 1) * 5  # Exponential backoff
            logger.warning(
                f"Service initialization attempt {attempt + 1} failed: {str(e)}. "
                f"Retrying in {wait_time} seconds..."
            )
            await asyncio.sleep(wait_time)

    raise RuntimeError(
        f"Failed to initialize services after {max_retries} attempts: {str(last_error)}"
    )


async def _init_emag_service(account_type: str) -> EmagIntegrationService:
    """Initialize eMAG service with proper credentials."""

    # Get credentials based on account type
    def _pick_first(*candidates):
        for candidate in candidates:
            if candidate:
                return candidate
        return None

    if account_type.lower() == "fbe":
        api_username = _pick_first(
            os.getenv("EMAG_USERNAME_FBE"),
            os.getenv("EMAG_FBE_USERNAME"),
            os.getenv("EMAG_FBE_API_USERNAME"),
            getattr(settings, "EMAG_USERNAME_FBE", None),
            getattr(settings, "EMAG_FBE_USERNAME", None),
            getattr(settings, "EMAG_FBE_API_USERNAME", None),
        )
        api_password = _pick_first(
            os.getenv("EMAG_PASSWORD_FBE"),
            os.getenv("EMAG_FBE_PASSWORD"),
            os.getenv("EMAG_FBE_API_PASSWORD"),
            getattr(settings, "EMAG_PASSWORD_FBE", None),
            getattr(settings, "EMAG_FBE_PASSWORD", None),
            getattr(settings, "EMAG_FBE_API_PASSWORD", None),
        )
    else:
        api_username = _pick_first(
            os.getenv("EMAG_USERNAME"),
            os.getenv("EMAG_API_USERNAME"),
            getattr(settings, "EMAG_USERNAME", None),
            getattr(settings, "EMAG_API_USERNAME", None),
            getattr(settings, "EMAG_API_USER", None),
            getattr(settings, "emag_main_username", None),
        )
        api_password = _pick_first(
            os.getenv("EMAG_PASSWORD"),
            os.getenv("EMAG_API_PASSWORD"),
            getattr(settings, "EMAG_PASSWORD", None),
            getattr(settings, "EMAG_API_PASSWORD", None),
            getattr(settings, "EMAG_API_KEY", None),
            getattr(settings, "emag_main_password", None),
        )

    if not api_username or not api_password:
        raise ValueError(
            f"Missing required credentials for {account_type} account. "
            f"Please set {'EMAG_USERNAME_FBE and EMAG_PASSWORD_FBE' if account_type.lower() == 'fbe' else 'EMAG_USERNAME and EMAG_PASSWORD'} "
            f"in your .env file or ensure they are loaded into the environment."
        )

    logger.info(
        f"Initializing eMAG {account_type} service with username: {api_username[:3]}..."
    )

    # Create service context
    context = ServiceContext(
        settings=settings,
        environment={
            "EMAG_API_USERNAME": api_username,
            "EMAG_API_PASSWORD": api_password,
            "EMAG_ENVIRONMENT": os.getenv("EMAG_ENVIRONMENT", "sandbox"),
        },
    )

    try:
        # Initialize service registry and service
        service_registry = ServiceRegistry()
        await service_registry.initialize(context)

        service = EmagIntegrationService(context, account_type=account_type)
        await service.initialize()
        return service
    except Exception as e:
        logger.error(f"Failed to initialize eMAG {account_type} service: {str(e)}")
        raise


def _log_progress(
    account_type: str,
    processed: int,
    errors: int,
    total: int = 0,
    start_time: float = None,
) -> None:
    """Log sync progress with performance metrics, ETA, and progress percentage."""
    if start_time is None:
        start_time = STATS.get("start_time", time.time())

    elapsed = time.time() - start_time
    rate = processed / elapsed if elapsed > 0 else 0

    # Build progress string
    progress = f"{processed}"
    if total > 0:
        progress = f"{processed}/{total} ({processed/max(total,1)*100:.1f}%)"

        # Calculate ETA if we have processed at least one item
        if processed > 0:
            remaining = max(0, total - processed)
            eta_seconds = remaining / rate if rate > 0 else 0
            eta = f" | ETA: {str(timedelta(seconds=int(eta_seconds))).rjust(8)}"
        else:
            eta = " | ETA: --:--:--"
    else:
        eta = ""

    # Format the log message
    logger.info(
        f"{account_type.upper()} | "
        f"Progress: {progress.ljust(15)} | "
        f"Errors: {str(errors).ljust(4)} | "
        f"Rate: {rate:5.1f}/s | "
        f"API: {metrics.metrics.get('api_calls', 0)} | "
        f"DB: {metrics.metrics.get('db_queries', 0)}{eta}"
    )


async def sync_both_accounts(days: int = 1) -> Dict[str, Any]:
    """Synchronize orders from both MAIN and FBE accounts with enhanced error handling."""
    logger.info(
        f"Starting order sync for both MAIN and FBE accounts (last {days} days)"
    )
    start_time = time.time()

    try:
        # Run sync for both accounts in parallel
        main_task = asyncio.create_task(sync_orders("main", days=days))
        fbe_task = asyncio.create_task(sync_orders("fbe", days=days))

        # Wait for both tasks to complete with timeout
        done, pending = await asyncio.wait(
            {main_task, fbe_task},
            timeout=3600,  # 1 hour timeout
            return_when=asyncio.ALL_COMPLETED,
        )

        # Process results
        results = []
        success_count = 0
        error_count = 0

        for task in done:
            try:
                result = task.result()
                results.append(result)
                if result.get("status") == "success":
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                results.append(
                    {
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        # Cancel any pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Log summary
        duration = time.time() - start_time
        logger.info(
            f"Order sync completed in {duration:.2f} seconds. "
            f"Success: {success_count}, Errors: {error_count}"
        )

        return {
            "status": "completed",
            "success_count": success_count,
            "error_count": error_count,
            "duration_seconds": round(duration, 2),
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Fatal error in sync_both_accounts: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "duration_seconds": round(time.time() - start_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command line arguments."""
    parser = argparse.ArgumentParser(
        description="Synchronize eMAG orders with enhanced features"
    )

    parser.add_argument(
        "--account",
        choices=["main", "fbe", "both"],
        default="both",
        help="Account type to sync (default: both)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days of orders to sync (default: 1)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of orders to process in each batch (default: 50)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Maximum number of concurrent batches (default: 5)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update existing orders (default: False)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of orders to process before stopping early",
    )
    parser.add_argument(
        "--show-summary",
        action="store_true",
        help="Show detailed summary at the end (default: False)",
    )
    parser.add_argument(
        "--summary-file", type=Path, help="Optional path to write sync summary as JSON"
    )

    return parser.parse_args()


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging with file and console handlers."""
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler for all logs
    file_handler = logging.FileHandler(log_dir / "order_sync.log")
    file_handler.setLevel(logging.DEBUG)

    # Console handler with higher level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def print_summary(result: Dict[str, Any]) -> None:
    """Print a detailed summary of the sync results with metrics and recommendations."""
    print("\n" + "=" * 80)
    print("SYNC SUMMARY".center(80))
    print("=" * 80)

    status = result.get("status", "unknown")
    status_text = status.upper()
    duration = float(result.get("duration_seconds", result.get("time_taken", 0) or 0))
    total_orders = 0
    success_orders = 0
    error_orders = 0
    metrics_data: Dict[str, Any] = {}

    def merge_metrics(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in incoming.items():
            if isinstance(value, (int, float)):
                base[key] = base.get(key, 0) + value
            elif isinstance(value, set):
                base.setdefault(key, set()).update(value)
            elif isinstance(value, dict):
                nested = base.setdefault(key, {})
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, (int, float)):
                        nested[nested_key] = nested.get(nested_key, 0) + nested_value
                    elif isinstance(nested_value, set):
                        nested.setdefault(nested_key, set()).update(nested_value)
                    else:
                        nested[nested_key] = nested_value
            else:
                base[key] = value
        return base

    account_breakdown: List[Tuple[str, str, int, int]] = []

    if status in {"success", "error"}:
        processed = int(result.get("processed", 0))
        errors = int(result.get("errors", 0))
        total_orders = processed
        error_orders = max(errors, 0)
        success_orders = max(processed - errors, 0)
        metrics_data = merge_metrics({}, result.get("metrics", {}))
        if status == "success" and error_orders == 0:
            status_text = "SUCCESS"
        elif status == "success" and error_orders > 0:
            status_text = "PARTIAL SUCCESS"
        else:
            status_text = "ERROR"

    elif status == "completed":
        status_text = "COMPLETED"
        duration = float(result.get("duration_seconds", duration))
        for account_result in result.get("results", []):
            processed = int(account_result.get("processed", 0))
            errors = int(account_result.get("errors", 0))
            total_orders += processed
            error_orders += max(errors, 0)
            success_orders += max(processed - errors, 0)
            account_breakdown.append(
                (
                    account_result.get("account_type", "unknown").upper(),
                    account_result.get("status", "unknown").upper(),
                    processed,
                    errors,
                )
            )
            metrics_data = merge_metrics(
                metrics_data, account_result.get("metrics", {})
            )
        # Fallback to explicit counts if provided
        if total_orders == 0:
            success_orders = int(result.get("success_count", 0))
            error_orders = int(result.get("error_count", 0))
            total_orders = success_orders + error_orders
        metrics_data = merge_metrics(metrics_data, result.get("metrics", {}))

    else:
        # Unknown structure; print raw keys for debugging
        status_text = status_text or "UNKNOWN"
        total_orders = int(result.get("total_orders", 0))
        success_orders = int(result.get("success_count", 0))
        error_orders = int(result.get("error_count", 0))
        metrics_data = merge_metrics({}, result.get("metrics", {}))

    print(f"Status: {status_text}")
    print("-" * 80)
    print(f"Total orders processed: {total_orders}")
    print(f"Successful orders: {success_orders}")
    print(f"Failed orders: {error_orders}")
    print(f"Time taken: {duration:.2f} seconds")

    if account_breakdown:
        print("\n" + "ACCOUNT BREAKDOWN".center(80, "-"))
        header = f"{'Account':<10} | {'Status':<15} | {'Processed':>9} | {'Errors':>6}"
        print(header)
        print("-" * len(header))
        for account, acc_status, processed, errors in account_breakdown:
            print(f"{account:<10} | {acc_status:<15} | {processed:>9} | {errors:>6}")

    # Performance metrics
    if any(metrics_data.values()):
        print("\n" + "PERFORMANCE METRICS".center(80, "-"))
        print(f"API Calls: {metrics_data.get('api_calls', 0)}")
        print(f"DB Queries: {metrics_data.get('db_queries', 0)}")
        print(f"Processing Time: {metrics_data.get('processing_time', 0):.2f}s")
        print(f"API Response Time: {metrics_data.get('api_response_time', 0):.2f}s")
        print(f"DB Query Time: {metrics_data.get('db_query_time', 0):.2f}s")

    # Missing products section
    missing_products = metrics_data.get("missing_products", set())
    if missing_products:
        print("\n" + "MISSING PRODUCTS".center(80, "-"))
        print(f"Total unique missing products: {len(missing_products)}")
        print(
            f"Orders with missing products: {metrics_data.get('orders_with_missing_products', 0)}"
        )
        print(
            f"Total missing product occurrences: {metrics_data.get('missing_product_occurrences', 0)}"
        )

        # Show first 10 missing product IDs with counts if available
        missing_counts = metrics_data.get("missing_product_counts", {})
        if missing_counts:
            sorted_missing = sorted(
                missing_counts.items(), key=lambda x: x[1], reverse=True
            )
            print("\nTop 10 most frequent missing products:")
            for i, (product_id, count) in enumerate(sorted_missing[:10], 1):
                print(f"  {i}. ID: {product_id} (missing in {count} orders)")
        else:
            print("\nFirst 10 missing product IDs:")
            for i, product_id in enumerate(sorted(missing_products)[:10], 1):
                print(f"  {i}. {product_id}")

        # Recommendations
        print("\n" + "RECOMMENDATIONS".center(80, "-"))
        print("1. Review missing products in the database")
        print("2. Check product synchronization with eMAG")
        print("3. Verify product activation status in MagFlow")
        print("4. Placeholder products have been created for missing items")

    print("\n" + "=" * 50 + "\n")


def save_summary_to_file(result: Dict[str, Any], summary_path: Path) -> None:
    """Write sync result summary to ``summary_path`` as JSON."""
    try:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("w", encoding="utf-8") as summary_file:
            json.dump(result, summary_file, indent=2, default=str)
        logger.info(f"Sync summary written to {summary_path}")
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.error(f"Failed to write summary file {summary_path}: {exc}")


def main() -> int:
    """Main entry point with enhanced error handling and reporting."""
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Setup logging
        setup_logging(args.log_level)

        # Log startup
        logger.info("=" * 70)
        logger.info(f"Starting eMAG Order Sync (PID: {os.getpid()})")
        logger.info(f"Account: {args.account}, Days: {args.days}")
        logger.info("-" * 70)

        # Validate database schema before proceeding
        logger.info("Validating database schema...")
        try:
            # Create database session factory for validation
            db_config = DatabaseConfig()
            engine = db_config.create_optimized_engine()
            async_session_factory = async_sessionmaker(
                bind=engine, expire_on_commit=False, class_=AsyncSession
            )

            # Run schema validation
            validation_results = asyncio.run(
                validate_sync_environment(async_session_factory)
            )
            print_validation_report(validation_results)

            # Exit if schema validation failed
            if not validation_results["schema_valid"]:
                logger.error(
                    "Database schema validation failed. Please fix the schema issues before running sync."
                )
                return 1

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return 1

        # Run the sync
        if args.account == "both":
            result = asyncio.run(sync_both_accounts(days=args.days))
        else:
            result = asyncio.run(
                sync_orders(
                    account_type=args.account,
                    days=args.days,
                    batch_size=args.batch_size,
                    max_concurrent=args.concurrency,
                    force_update=args.force_update,
                    limit=args.limit,
                )
            )

        # Print summary
        print_summary(result)

        # Optionally persist summary to disk
        if args.summary_file:
            save_summary_to_file(result, args.summary_file)

        # Return appropriate exit code
        return 0 if result.get("error_count", 0) == 0 else 1

    except KeyboardInterrupt:
        logger.warning("Order sync interrupted by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.critical(f"Fatal error in main: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
