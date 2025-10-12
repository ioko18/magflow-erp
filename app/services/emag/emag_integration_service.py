"""Enhanced eMAG Marketplace API Integration for MagFlow ERP.

This module provides comprehensive integration with the eMAG marketplace API v4.4.8,
enabling full product synchronization, order management, inventory updates, and
real-time marketplace connectivity with proper rate limiting and error handling.
"""

import asyncio
import contextlib
import os
import secrets
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from functools import wraps
from typing import Any

import aiohttp

from app.core.config import settings
from app.core.exceptions import ConfigurationError, ServiceError
from app.core.logging import get_logger as setup_logger
from app.repositories.order_repository import get_order_repository
from app.repositories.product_repository import get_product_repository
from app.services.base_service import BaseService
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError
from app.services.service_context import ServiceContext

logger = setup_logger(__name__)


def performance_monitor(func_name: str):
    """Decorator to monitor performance of async functions"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                logger.debug(f"Starting {func_name}")
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{func_name} completed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func_name} failed after {execution_time:.3f}s: {e}")
                raise

        return wrapper

    return decorator


class EmagApiEnvironment(Enum):
    """eMAG API environments."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"


# EmagApiError is now imported from emag_api_client


@dataclass
class EmagApiConfig:
    """Configuration for eMAG API integration."""

    environment: EmagApiEnvironment = EmagApiEnvironment.SANDBOX
    api_username: str = ""
    api_password: str = ""
    # client_id not used in Basic Auth
    # client_secret not used in Basic Auth
    base_url: str = ""
    api_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    # Rate limiting per eMAG API v4.4.8 specs
    orders_rate_rps: int = 12  # 12 requests per second for orders
    other_rate_rps: int = 3  # 3 requests per second for other endpoints
    bulk_max_entities: int = 50  # Max 50 entities per bulk operation

    def __post_init__(self):
        """Set base URL based on environment."""
        if not self.base_url:
            if self.environment == EmagApiEnvironment.PRODUCTION:
                self.base_url = "https://marketplace-api.emag.ro/api-3"
            else:
                self.base_url = "https://marketplace-api-sandbox.emag.ro/api-3"

        # Validate required fields for Basic Auth
        if not self.api_username or not self.api_password:
            raise ConfigurationError(
                "eMAG API username and password are required for Basic Auth"
            )


@dataclass
class EmagRateLimiter:
    """Rate limiter for eMAG API with per-second and per-minute limits."""

    orders_rps: int = 12  # 12 requests per second for orders
    other_rps: int = 3  # 3 requests per second for other endpoints
    orders_rpm: int = 720  # 720 requests per minute for orders
    other_rpm: int = 180  # 180 requests per minute for other endpoints
    jitter_max: float = 0.1  # Maximum jitter to avoid thundering herd
    sleep_fn: Callable[[float], Awaitable[None]] = (
        asyncio.sleep
    )  # Injectable sleep function

    def __post_init__(self):
        self._locks: dict[str, asyncio.Lock] = {}
        # Track timestamps of previous requests for both 1-second and 60-second windows
        self._request_windows: dict[str, dict[str, deque[float]]] = {}
    async def acquire(self, resource_type: str = "other"):
        """Acquire permission to make a request respecting eMAG API limits."""
        # Using secrets.SystemRandom() for cryptographic safety

        per_second_limit = (
            self.orders_rps if resource_type == "orders" else self.other_rps
        )
        per_minute_limit = (
            self.orders_rpm if resource_type == "orders" else self.other_rpm
        )

        lock = self._locks.setdefault(resource_type, asyncio.Lock())
        windows = self._request_windows.setdefault(
            resource_type,
            {
                "second": deque(),
                "minute": deque(),
            },
        )

        second_window = windows["second"]
        minute_window = windows["minute"]
        time_source = time.monotonic

        while True:
            async with lock:
                now = time_source()

                # Clear expired entries
                while second_window and now - second_window[0] >= 1.0:
                    second_window.popleft()

                while minute_window and now - minute_window[0] >= 60.0:
                    minute_window.popleft()

                if (
                    len(second_window) < per_second_limit
                    and len(minute_window) < per_minute_limit
                ):
                    # Approved; register request timestamp using actual acquisition time
                    second_window.append(now)
                    minute_window.append(now)
                    return

                # Determine time to wait until at least one slot frees up
                wait_times: list[float] = []

                if len(second_window) >= per_second_limit:
                    wait_times.append(1.0 - (now - second_window[0]))

                if len(minute_window) >= per_minute_limit:
                    wait_times.append(60.0 - (now - minute_window[0]))

                # Guard against negative waits due to timing drift
                wait_time = max(0.0, min(wait_times) if wait_times else 0.0)

            # Apply optional jitter when waiting to avoid synchronized bursts
            jitter = secrets.SystemRandom().uniform(0, self.jitter_max) if self.jitter_max > 0 else 0.0
            await self.sleep_fn(max(0.001, wait_time) + jitter)


@dataclass
class EmagProduct:
    """eMAG product data structure with v4.4.8 fields."""

    id: str | None = None
    name: str = ""
    sku: str = ""
    description: str = ""
    price: float = 0.0
    currency: str = "RON"
    stock_quantity: int = 0
    category_id: str | None = None
    brand: str = ""
    images: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    emag_category_id: str | None = None
    emag_characteristics: dict[str, Any] = field(default_factory=dict)

    # New v4.4.8 fields
    images_overwrite: bool = False  # Control append vs overwrite behavior
    green_tax: float | None = None  # RO only, includes TVA
    supply_lead_time: int | None = None  # 2,3,5,7,14,30,60,90,120 days

    # GPSR (General Product Safety Regulation) fields
    safety_information: str | None = None
    manufacturer: list[dict[str, str]] = field(
        default_factory=list
    )  # [{name, address, email}]
    eu_representative: list[dict[str, str]] = field(
        default_factory=list
    )  # [{name, address, email}]


@dataclass
class EmagOrder:
    """eMAG order data structure."""

    id: str = ""
    emag_order_id: str = ""
    status: str = ""
    customer_name: str = ""
    customer_email: str = ""
    total_amount: float = 0.0
    currency: str = "RON"
    order_date: datetime = None
    items: list[dict[str, Any]] = field(default_factory=list)
    shipping_address: dict[str, Any] = field(default_factory=dict)
    billing_address: dict[str, Any] = field(default_factory=dict)
    payment_method: str = ""
    shipping_cost: float = 0.0


class EmagIntegrationService(BaseService):
    """Service for managing eMAG marketplace integration.

    This service provides a high-level interface for interacting with the eMAG API,
    handling authentication, rate limiting, and error handling.
    """

    def __init__(self, context: ServiceContext, account_type: str = "main"):
        """Initialize the eMAG integration service.

        Args:
            context: Service context with dependencies
            account_type: Type of eMAG account ('main' or 'fbe')
        """
        super().__init__(context)
        self.account_type = (account_type or "main").lower()
        self.config = self._load_config(self.account_type)
        self.client: EmagApiClient | None = None
        self.product_repository = get_product_repository()
        self.order_repository = get_order_repository()
        self._sync_tasks: dict[str, asyncio.Task] = {}

    def _load_config(self, account_type: str) -> EmagApiConfig:
        """Load eMAG API configuration from settings."""
        prefix = f"EMAG_{account_type.upper()}_"
        env = (
            EmagApiEnvironment.PRODUCTION
            if settings.ENVIRONMENT == "production"
            else EmagApiEnvironment.SANDBOX
        )

        return EmagApiConfig(
            environment=env,
            api_username=os.getenv(f"{prefix}USERNAME", ""),
            api_password=os.getenv(f"{prefix}PASSWORD", ""),
            base_url=os.getenv(f"{prefix}BASE_URL", ""),
            api_timeout=int(os.getenv(f"{prefix}TIMEOUT", "30")),
            max_retries=int(os.getenv(f"{prefix}MAX_RETRIES", "3")),
            retry_delay=float(os.getenv(f"{prefix}RETRY_DELAY", "1.0")),
            orders_rate_rps=int(os.getenv(f"{prefix}ORDERS_RPS", "12")),
            other_rate_rps=int(os.getenv(f"{prefix}OTHER_RPS", "3")),
            bulk_max_entities=int(os.getenv(f"{prefix}BULK_MAX", "50")),
        )

    async def initialize(self):
        """Initialize the eMAG API client."""
        if not self.client:
            self.client = EmagApiClient(
                username=self.config.api_username,
                password=self.config.api_password,
                base_url=self.config.base_url,
                timeout=self.config.api_timeout,
                max_retries=self.config.max_retries,
            )
            await self.client.start()
            logger.info(
                "Initialized eMAG API client for %s account (environment: %s)",
                self.account_type,
                self.config.environment.value,
            )

    async def close(self):
        """Close the eMAG API client and clean up resources."""
        if self.client:
            await self.client.close()
            self.client = None
        logger.info("Closed eMAG API client for %s account", self.account_type)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @performance_monitor("sync_products")
    async def sync_products(self, full_sync: bool = False) -> dict[str, Any]:
        """Synchronize products between eMAG and the local database.

        Args:
            full_sync: If True, perform a full synchronization

        Returns:
            Dict with synchronization results
        """
        if not self.client:
            await self.initialize()

        try:
            # Get products from eMAG
            logger.info("Fetching products from eMAG...")
            emag_products = await self._get_emag_products()

            # Get products from local database
            logger.info("Fetching products from local database...")
            local_products = await self._get_local_products()

            # Synchronize products
            return await self._synchronize_products(
                emag_products, local_products, full_sync
            )

        except Exception as e:
            logger.error("Failed to sync products: %s", str(e), exc_info=True)
            raise ServiceError(f"Failed to sync products: {str(e)}") from e

    async def _get_emag_products(self) -> list[dict[str, Any]]:
        """Get products from eMAG API."""
        if not self.client:
            raise ServiceError("eMAG API client not initialized")

        try:
            products = []
            page = 1
            has_more = True

            while has_more:
                response = await self.client.get_products(page=page, items_per_page=100)
                if not response or "results" not in response:
                    break

                products.extend(response["results"])
                has_more = response.get("current_page", 0) < response.get(
                    "total_pages", 0
                )
                page += 1

            return products

        except EmagApiError as e:
            logger.error("eMAG API error: %s", str(e))
            raise ServiceError(f"eMAG API error: {str(e)}") from e

    async def _get_local_products(self) -> list[dict[str, Any]]:
        """Get products from local database."""
        try:
            # This is a placeholder - implement actual database query
            return []
        except Exception as e:
            logger.error("Failed to get local products: %s", str(e))
            raise ServiceError(f"Failed to get local products: {str(e)}") from e

    async def _synchronize_products(
        self,
        emag_products: list[dict[str, Any]],
        local_products: list[dict[str, Any]],
        full_sync: bool = False,
    ) -> dict[str, Any]:
        """Synchronize products between eMAG and local database."""
        # This is a simplified implementation
        stats = {
            "total_emag_products": len(emag_products),
            "total_local_products": len(local_products),
            "created": 0,
            "updated": 0,
            "deactivated": 0,
            "errors": [],
        }

        # Create a map of SKU to local product for faster lookup
        local_products_map = {p["sku"]: p for p in local_products if "sku" in p}

        # Process each eMAG product
        for emag_product in emag_products:
            try:
                sku = emag_product.get("part_number") or emag_product.get("sku")
                if not sku:
                    continue

                if sku in local_products_map:
                    # Update existing product
                    stats["updated"] += 1
                else:
                    # Create new product
                    stats["created"] += 1

            except Exception as e:
                stats["errors"].append(f"Error processing product {sku}: {str(e)}")
                logger.error(
                    "Error processing product %s: %s", sku, str(e), exc_info=True
                )

        return stats

    @performance_monitor("sync_orders")
    async def sync_orders(self) -> dict[str, Any]:
        """Synchronize orders from eMAG to local database."""
        if not self.client:
            await self.initialize()

        try:
            # Get orders from eMAG
            logger.info("Fetching orders from eMAG...")
            emag_orders = await self._get_emag_orders()

            # Process orders
            return await self._process_orders(emag_orders)

        except Exception as e:
            logger.error("Failed to sync orders: %s", str(e), exc_info=True)
            raise ServiceError(f"Failed to sync orders: {str(e)}") from e

    async def _get_emag_orders(self) -> list[dict[str, Any]]:
        """Get orders from eMAG API."""
        if not self.client:
            raise ServiceError("eMAG API client not initialized")

        try:
            # This is a simplified implementation
            # In a real implementation, you would handle pagination, filtering, etc.
            response = await self.client.get_orders(status="new")
            return response.get("results", [])

        except EmagApiError as e:
            logger.error("eMAG API error: %s", str(e))
            raise ServiceError(f"eMAG API error: {str(e)}") from e

    async def _process_orders(self, orders: list[dict[str, Any]]) -> dict[str, Any]:
        """Process orders from eMAG."""
        stats = {
            "total_orders": len(orders),
            "processed": 0,
            "errors": [],
        }

        for order in orders:
            try:
                # Process order (create or update in local database)
                # This is a placeholder - implement actual order processing
                stats["processed"] += 1

            except Exception as e:
                order_id = order.get("id", "unknown")
                stats["errors"].append(f"Error processing order {order_id}: {str(e)}")
                logger.error(
                    "Error processing order %s: %s", order_id, str(e), exc_info=True
                )

        return stats

        # Test the connection
        try:
            # Make a test request to verify credentials (but don't fail if it doesn't exist)
            await self._make_request(
                "GET",
                "/test",
                allowed_status_codes={404},
            )
            logger.info("eMAG API authentication test successful")
        except Exception as e:
            logger.debug(
                "eMAG API authentication test returned expected non-success response: %s",
                e,
            )

    async def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        # For Basic auth we only need the header once
        if not self.access_token:
            await self.authenticate()
            return

        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            logger.info("Access token expired, re-authenticating")
            await self.authenticate()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] = None,
        params: dict[str, Any] = None,
        allowed_status_codes: set[int] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to eMAG API with proper rate limiting."""
        await self._ensure_authenticated()

        # Determine resource type for rate limiting
        resource_type = self._get_resource_type(endpoint)

        # Apply rate limiting
        await self.rate_limiter.acquire(resource_type)

        if self.captcha_blocked:
            raise EmagApiError(
                "Captcha challenge previously detected; unblock access via the sandbox portal before retrying",
                status_code=511,
                details={"captcha_required": True},
            )

        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            normalized_base = self.config.base_url.rstrip("/")
            normalized_endpoint = endpoint.lstrip("/")
            if normalized_endpoint:
                url = f"{normalized_base}/{normalized_endpoint}"
            else:
                url = normalized_base

        headers = {
            "Authorization": self.access_token,  # Basic auth token
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Account-Type": getattr(
                self,
                "account_type",
                "main",
            ),  # Support account type in headers
        }

        max_retries = self.config.max_retries
        retry_count = 0

        import inspect

        while retry_count <= max_retries:
            try:
                # Support both real aiohttp and test doubles
                req_obj = self.session.request(
                    method, url, json=data, params=params, headers=headers
                )
                if inspect.isawaitable(req_obj):
                    req_obj = await req_obj

                response = None
                response_data = None

                try:
                    async with req_obj as resp:
                        response = resp
                        content_type = response.headers.get("Content-Type", "")
                        status_code = getattr(response, "status", 200)

                        if "json" not in content_type.lower():
                            body_text = await response.text()
                            headers_snapshot = dict(response.headers)
                            lower_body = body_text.lower()
                            captcha_detected = (
                                "captcha" in lower_body or status_code == 511
                            )
                            logger.error(
                                "eMAG API returned non-JSON response (status=%s, content_type=%s). "
                                "Body snippet: %r | Headers: %s",
                                status_code,
                                content_type,
                                body_text[:500],
                                headers_snapshot,
                                extra={
                                    "event": "emag.invalid_response",
                                    "status_code": status_code,
                                    "url": url,
                                    "payload": data,
                                    "params": params,
                                    "content_type": content_type,
                                    "response_body_snippet": body_text[:500],
                                    "response_headers": headers_snapshot,
                                    "captcha_detected": captcha_detected,
                                },
                            )
                            if captcha_detected:
                                self.captcha_blocked = True
                            raise EmagApiError(
                                (
                                    "Captcha challenge encountered"
                                    if captcha_detected
                                    else "Invalid API response: expected JSON body"
                                ),
                                status_code,
                                {
                                    "content_type": content_type,
                                    "raw_body": body_text,
                                    "captcha_required": captcha_detected,
                                    "response_headers": headers_snapshot,
                                },
                            )

                        json_val = response.json()
                        response_data = (
                            await json_val
                            if inspect.isawaitable(json_val)
                            else json_val
                        )
                except TypeError:
                    # Fallback: treat req_obj as response directly
                    response = req_obj
                    content_type = response.headers.get("Content-Type", "")
                    status_code = getattr(response, "status", 200)
                    if "json" not in content_type.lower():
                        body_text = await response.text()
                        headers_snapshot = dict(response.headers)
                        lower_body = body_text.lower()
                        captcha_detected = "captcha" in lower_body or status_code == 511
                        logger.error(
                            "eMAG API returned non-JSON response (status=%s, content_type=%s). "
                            "Body snippet: %r | Headers: %s",
                            status_code,
                            content_type,
                            body_text[:500],
                            headers_snapshot,
                            extra={
                                "event": "emag.invalid_response",
                                "status_code": status_code,
                                "url": url,
                                "payload": data,
                                "params": params,
                                "content_type": content_type,
                                "response_body_snippet": body_text[:500],
                                "response_headers": headers_snapshot,
                                "captcha_detected": captcha_detected,
                            },
                        )
                        if captcha_detected:
                            self.captcha_blocked = True
                        raise EmagApiError(
                            "Captcha challenge encountered" if captcha_detected else "Invalid API response: expected JSON body",
                            status_code,
                            {
                                "content_type": content_type,
                                "raw_body": body_text,
                                "captcha_required": captcha_detected,
                                "response_headers": headers_snapshot,
                            },
                        ) from None

                    json_val = response.json()
                    response_data = (
                        await json_val if inspect.isawaitable(json_val) else json_val
                    )

                self._request_count += 1

                status_code = getattr(response, "status", 200)

                response_data = self._normalize_response_payload(
                    response_data,
                    status_code,
                    url,
                    data,
                    params,
                )

                # If isError is true, it's an error
                if response_data.get("isError", False):
                    error_msg = response_data.get("messages", ["Unknown error"])[0]
                    raise EmagApiError(
                        f"eMAG API error: {error_msg}",
                        status_code,
                        response_data,
                    )

                # Handle HTTP errors
                if status_code >= 400:
                    if allowed_status_codes and status_code in allowed_status_codes:
                        logger.debug(
                            "eMAG API returned allowed HTTP status %s for %s; treating as success",
                            status_code,
                            url,
                        )
                        return response_data
                    if status_code == 429:  # Rate limit exceeded
                        if retry_count < max_retries:
                            # Exponential backoff with jitter using cryptographic RNG
                            wait_time = (2**retry_count) + secrets.SystemRandom().uniform(0, 1)
                            logger.warning(
                                "Rate limit hit, retrying in %.2fs", wait_time
                            )
                            await asyncio.sleep(wait_time)
                            retry_count += 1
                            continue
                    elif status_code == 401:
                        # Token might be invalid, try re-authenticating once
                        if retry_count == 0:
                            await self.authenticate()
                            headers["Authorization"] = self.access_token
                            retry_count += 1
                            continue

                    # Extract more detailed error information
                    error_messages = response_data.get("messages", ["Unknown error"])
                    error_text = (
                        error_messages[0] if error_messages else "Unknown error"
                    )

                    # Log detailed error for debugging
                    logger.error(
                        f"eMAG API HTTP error {status_code}: {error_text}. "
                        f"URL: {url}, Method: {method}, Full response: {response_data}"
                    )

                    # Provide more context in the error message
                    detailed_error = f"HTTP {status_code} - {error_text}"
                    if len(error_messages) > 1:
                        detailed_error += (
                            f" (Additional messages: {', '.join(error_messages[1:])})"
                        )

                    raise EmagApiError(
                        message=f"API request failed: {detailed_error}",
                        status_code=status_code,
                        details={"response_data": response_data},
                    )

                return response_data

            except EmagApiError as e:
                captcha_required = False
                if isinstance(getattr(e, "details", None), dict):
                    captcha_required = bool(e.details.get("captcha_required"))

                if captcha_required or getattr(e, "status_code", None) == 511:
                    logger.error(
                        "Captcha challenge detected from eMAG API; manual intervention required before continuing."  # noqa: E501
                    )
                    raise

                if retry_count < max_retries:
                    wait_time = self.config.retry_delay * (2**retry_count)
                    logger.warning(
                        "eMAG API error (attempt %d/%d), retrying in %.2fs: %s",
                        retry_count + 1,
                        max_retries + 1,
                        wait_time,
                        e,
                    )
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                    continue

                raise

            except aiohttp.ClientError as e:
                if retry_count < max_retries:
                    wait_time = self.config.retry_delay * (2**retry_count)
                    logger.warning(
                        f"Request failed (attempt {retry_count + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time:.2f}s: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                    continue

                # Log detailed error information
                logger.error(
                    f"eMAG API request failed permanently after {max_retries + 1} attempts. "
                    f"URL: {url}, Method: {method}, Error: {type(e).__name__}: {e}"
                )
                raise EmagApiError(
                    message=f"Request failed after {max_retries + 1} attempts: {type(e).__name__}: {e}",
                    status_code=0,
                    details={"error_type": type(e).__name__, "error_message": str(e)},
                ) from e

            except Exception as e:
                logger.error(
                    f"Unexpected error in eMAG API request. "
                    f"URL: {url}, Method: {method}, Error: {type(e).__name__}: {e}"
                )
                if retry_count < max_retries:
                    wait_time = self.config.retry_delay * (2**retry_count)
                    logger.warning(
                        f"Retrying in {wait_time:.2f}s due to unexpected error"
                    )
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                    continue

                raise EmagApiError(
                    message=f"Unexpected error after {max_retries + 1} attempts: {type(e).__name__}: {e}",
                    status_code=0,
                    details={"error_type": type(e).__name__, "error_message": str(e)},
                ) from e

        # This should never be reached, but just in case
        logger.error(
            f"eMAG API request exhausted all {max_retries + 1} attempts without resolution"
        )
        raise EmagApiError(
            message=f"Request failed after {max_retries + 1} attempts - no response received",
            status_code=0,
            details={"error_type": "MaxRetriesExceeded", "attempts": max_retries + 1},
        )

    def _normalize_response_payload(
        self,
        payload: Any,
        status_code: int,
        url: str,
        data: dict[str, Any] | None,
        params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Normalize eMAG responses to include an `isError` flag.

        Some eMAG endpoints occasionally omit the `isError` field or return a
        raw list payload. To keep higher-level logic simple, coerce these
        responses into the usual structure while preserving the original data in
        the `data` key.
        """

        if isinstance(payload, dict):
            if "isError" not in payload:
                logger.warning(
                    "eMAG API response missing 'isError' field; assuming success",
                    extra={
                        "event": "emag.response_missing_iserror",
                        "status_code": status_code,
                        "url": url,
                        "payload_keys": list(payload.keys()),
                        "params": params,
                    },
                )
                normalized = {"isError": False, "data": payload}
                if "messages" in payload:
                    normalized["messages"] = payload["messages"]
                return normalized
            return payload

        if payload is None:
            logger.warning(
                "eMAG API returned null payload; assuming success",
                extra={
                    "event": "emag.response_null",
                    "status_code": status_code,
                    "url": url,
                    "params": params,
                },
            )
            return {"isError": False, "data": None}

        if isinstance(payload, list):
            logger.warning(
                "eMAG API returned list payload; wrapping in standard structure",
                extra={
                    "event": "emag.response_list",
                    "status_code": status_code,
                    "url": url,
                    "params": params,
                },
            )
            return {"isError": False, "data": payload}

        logger.error(
            "eMAG API returned unsupported payload type",
            extra={
                "event": "emag.invalid_response_type",
                "status_code": status_code,
                "url": url,
                "payload_type": type(payload).__name__,
                "payload_repr": repr(payload)[:500],
                "params": params,
            },
        )
        raise EmagApiError(
            "Invalid API response: unsupported payload type",
            status_code,
            {"raw_response": payload, "payload_type": type(payload).__name__},
        )

    async def request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Public helper to execute raw eMAG API requests."""

        return await self._make_request(
            method,
            endpoint,
            data=data,
            params=params,
        )

    def _get_resource_type(self, endpoint: str) -> str:
        """Determine resource type for rate limiting based on endpoint."""
        # eMAG API v4.4.8 rate limiting rules:
        # - ORDERS endpoints: max 12 req/s (order/read, order/save, order/count, order/acknowledge, order/unlock-courier)
        # - All other endpoints: max 3 req/s

        orders_endpoints = [
            "/order/read",
            "/order/save",
            "/order/count",
            "/order/acknowledge",
            "/order/unlock-courier",
        ]

        if any(order_endpoint in endpoint for order_endpoint in orders_endpoints):
            return "orders"

        return "other"

    async def get_products(self, page: int = 1, limit: int = 50) -> dict[str, Any]:
        """Get products from eMAG."""
        return await self._make_request("GET", f"/products?page={page}&limit={limit}")

    async def create_product(self, product: EmagProduct) -> dict[str, Any]:
        """Create a new product on eMAG with v4.4.8 fields."""
        product_data = {
            "name": product.name,
            "sku": product.sku,
            "description": product.description,
            "price": product.price,
            "currency": product.currency,
            "stock": product.stock_quantity,
            "category_id": product.emag_category_id,
            "brand": product.brand,
            "images": product.images,
            "characteristics": product.emag_characteristics,
            "active": product.is_active,
        }

        # Add new v4.4.8 fields if provided
        if product.images_overwrite is not None:
            product_data["images_overwrite"] = product.images_overwrite

        if product.green_tax is not None:
            product_data["green_tax"] = product.green_tax

        if product.supply_lead_time is not None:
            product_data["supply_lead_time"] = product.supply_lead_time

        # GPSR fields
        if product.safety_information:
            product_data["safety_information"] = product.safety_information

        if product.manufacturer:
            product_data["manufacturer"] = product.manufacturer

        if product.eu_representative:
            product_data["eu_representative"] = product.eu_representative

        return await self._make_request("POST", "/products", data=product_data)

    async def update_product(
        self,
        product_id: str,
        product: EmagProduct,
    ) -> dict[str, Any]:
        """Update an existing product on eMAG with v4.4.8 fields."""
        product_data = {
            "name": product.name,
            "sku": product.sku,
            "description": product.description,
            "price": product.price,
            "currency": product.currency,
            "stock": product.stock_quantity,
            "category_id": product.emag_category_id,
            "brand": product.brand,
            "images": product.images,
            "characteristics": product.emag_characteristics,
            "active": product.is_active,
        }

        # Add new v4.4.8 fields if provided
        if product.images_overwrite is not None:
            product_data["images_overwrite"] = product.images_overwrite

        if product.green_tax is not None:
            product_data["green_tax"] = product.green_tax

        if product.supply_lead_time is not None:
            product_data["supply_lead_time"] = product.supply_lead_time

        # GPSR fields
        if product.safety_information:
            product_data["safety_information"] = product.safety_information

        if product.manufacturer:
            product_data["manufacturer"] = product.manufacturer

        if product.eu_representative:
            product_data["eu_representative"] = product.eu_representative

        return await self._make_request(
            "PUT",
            f"/products/{product_id}",
            data=product_data,
        )

    async def delete_product(self, product_id: str) -> bool:
        """Delete a product from eMAG."""
        try:
            await self._make_request("DELETE", f"/products/{product_id}")
            return True
        except EmagApiError:
            return False

    async def get_orders(
        self,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get orders from eMAG Marketplace API."""

        filters: dict[str, Any] = {}

        if status:
            filters["status"] = status
        if start_date:
            filters["startDate"] = start_date.isoformat()
        if end_date:
            filters["endDate"] = end_date.isoformat()

        payload: dict[str, Any] = {
            "data": {
                "currentPage": page,
                "itemsPerPage": limit,
            }
        }

        if filters:
            payload["data"]["filters"] = filters

        return await self._make_request("POST", "/order/read", data=payload)

    async def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
        """
        Get a specific order by ID from eMAG Marketplace API.

        Args:
            order_id: eMAG order ID

        Returns:
            Order details or None if not found
        """
        try:
            response = await self._make_request("POST", "/order/read", data={
                "data": {
                    "currentPage": 1,
                    "itemsPerPage": 1,
                    "filters": {
                        "id": order_id
                    }
                }
            })

            # Extract order from response
            if response and "results" in response and response["results"]:
                return response["results"][0]

            return None

        except EmagApiError as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            return None

    async def update_order_status(self, order_id: str, status: str) -> dict[str, Any]:
        """Update order status on eMAG."""
        return await self._make_request(
            "PUT",
            f"/orders/{order_id}/status",
            data={"status": status},
        )

    async def get_categories(self, parent_id: str = None) -> dict[str, Any]:
        """Get product categories from eMAG."""
        params = {}
        if parent_id:
            params["parent_id"] = parent_id

        return await self._make_request("GET", "/categories", params=params)

    async def sync_inventory(self, sku: str, quantity: int) -> dict[str, Any]:
        """Sync inventory for a specific product."""
        return await self._make_request(
            "PUT",
            f"/inventory/{sku}",
            data={"quantity": quantity},
        )

    async def bulk_update_inventory(
        self,
        inventory_updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Bulk update inventory for multiple products."""
        return await self._make_request(
            "PUT",
            "/inventory/bulk",
            data={"updates": inventory_updates},
        )

    async def smart_deals_price_check(self, product_id: str) -> dict[str, Any]:
        """Check Smart Deals target price for a product (v4.4.8 feature)."""
        try:
            if not self:
                raise EmagApiError("eMAG API client not initialized")

            return await self._make_request(
                "GET",
                f"/smart-deals-price-check?productId={product_id}",
            )

        except Exception as e:
            logger.error(
                "Failed to get Smart Deals price check for product %s: %s",
                product_id,
                e,
            )
            raise EmagApiError(f"Smart Deals price check failed: {e}") from e

    # EmagIntegrationService class is defined earlier in the file

    def _normalize_environment(self, environment: Any) -> EmagApiEnvironment:
        """Normalize environment names from settings.

        Accepts values like "production", "prod", "sandbox", "sand", or the
        enum itself. Raises a ``ConfigurationError`` for unsupported values to
        surface misconfiguration early.
        """

        if isinstance(environment, EmagApiEnvironment):
            return environment

        if isinstance(environment, str):
            normalized = environment.strip().lower()
            aliases = {
                "production": EmagApiEnvironment.PRODUCTION,
                "prod": EmagApiEnvironment.PRODUCTION,
                "live": EmagApiEnvironment.PRODUCTION,
                "sandbox": EmagApiEnvironment.SANDBOX,
                "sand": EmagApiEnvironment.SANDBOX,
                "test": EmagApiEnvironment.SANDBOX,
                "development": EmagApiEnvironment.SANDBOX,
                "dev": EmagApiEnvironment.SANDBOX,
            }

            if normalized in aliases:
                return aliases[normalized]

        raise ConfigurationError(
            "Invalid EMAG_ENVIRONMENT value. Expected one of: "
            "production, prod, live, sandbox, sand, test, development, dev."
        )

    def _load_config(self, account_type: str) -> EmagApiConfig:
        """Load eMAG API configuration."""
        settings = self.context.settings

        # Get configuration from settings
        environment = getattr(settings, "EMAG_ENVIRONMENT", "production")
        logger.debug(
            f"Initializing eMAG client - Environment: {environment}, Account: {account_type}"
        )

        def _resolve_credentials() -> tuple[str, str]:
            if account_type == "fbe":
                # Try both naming conventions for FBE account
                username = (
                    getattr(settings, "EMAG_USERNAME_FBE", "")
                    or getattr(settings, "EMAG_FBE_USERNAME", "")
                    or getattr(settings, "EMAG_FBE_API_USERNAME", "")
                )
                password = (
                    getattr(settings, "EMAG_PASSWORD_FBE", "")
                    or getattr(settings, "EMAG_FBE_PASSWORD", "")
                    or getattr(settings, "EMAG_FBE_API_PASSWORD", "")
                )
                if username:
                    logger.debug(f"FBE credentials found: username={username[:3]}***")
                else:
                    logger.warning("FBE credentials not found in environment")
            else:  # main or default
                # Try both naming conventions for main account
                username = (
                    getattr(settings, "EMAG_USERNAME", "")
                    or getattr(settings, "EMAG_MAIN_USERNAME", "")
                    or getattr(settings, "EMAG_API_USERNAME", "")
                )
                password = (
                    getattr(settings, "EMAG_PASSWORD", "")
                    or getattr(settings, "EMAG_MAIN_PASSWORD", "")
                    or getattr(settings, "EMAG_API_PASSWORD", "")
                )
                if username:
                    logger.debug(f"MAIN credentials found: username={username[:3]}***")
                else:
                    logger.warning("MAIN credentials not found in environment")

            if not username or not password:
                error_msg = (
                    f"eMAG API username and password are required for Basic Auth. "
                    f"Set EMAG_{account_type.upper()}_USERNAME and EMAG_{account_type.upper()}_PASSWORD in environment variables. "
                    f"Current values - Username: {'Set' if username else 'Not set'}, Password: {'Set' if password else 'Not set'}"
                )
                logger.error(error_msg)
                raise ConfigurationError(error_msg)

            return username, password

        api_username, api_password = _resolve_credentials()

        api_timeout = getattr(settings, "EMAG_REQUEST_TIMEOUT", 30)
        orders_rate_rps = getattr(settings, "EMAG_RATE_ORDERS_RPS", 12)
        other_rate_rps = getattr(settings, "EMAG_RATE_OTHER_RPS", 3)
        base_url = getattr(settings, "EMAG_BASE_URL", "")

        try:
            return EmagApiConfig(
                environment=self._normalize_environment(environment),
                api_username=api_username,
                api_password=api_password,
                api_timeout=api_timeout,
                orders_rate_rps=orders_rate_rps,
                other_rate_rps=other_rate_rps,
                base_url=base_url,
            )
        except ConfigurationError as e:
            logger.error("Failed to load eMAG configuration: %s", e)
            raise ConfigurationError(f"eMAG integration not properly configured: {e}") from e

    async def cleanup(self):
        """Cleanup eMAG integration service."""
        if self.client:
            await self.client.close()

        # Cancel any running sync tasks
        for task in self._sync_tasks.values():
            task.cancel()

        self._sync_tasks.clear()
        logger.info("eMAG integration service cleaned up")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Delegate HTTP requests to the underlying API client.

        Prefers a public request helper on the client when available,
        otherwise safely falls back to the protected `_make_request`
        implementation to maintain compatibility with the existing client
        contract without duplicating logic in this service.
        """

        if not self.client:
            raise EmagApiError("eMAG API client not initialized")

        # Prefer a public request helper when available to avoid relying on
        # internals of the API client.
        request_fn = getattr(self.client, "request", None)
        if request_fn:
            return await request_fn(method, endpoint, data=data, params=params)

        return await self.client._request(  # pylint: disable=protected-access
            method,
            endpoint,
            data=data,
            params=params,
        )

    @performance_monitor("EmagIntegrationService.sync_products")
    async def update_inventory(self, sku: str, quantity: int) -> bool:
        """Update inventory for a specific product."""
        try:
            if not self.client:
                raise EmagApiError("eMAG API client not initialized")

            result = await self.client.sync_inventory(sku, quantity)
            return result.get("success", False)

        except Exception as e:
            logger.error("Inventory update failed for SKU %s: %s", sku, e)
            return False

    async def create_product_with_retry(
        self,
        product: "EmagProduct",
        max_attempts: int = 3,
        initial_delay: float = 0.5,
    ) -> dict[str, Any]:
        """Create a product with retry logic for transient failures.

        Handles both exceptions (e.g. network issues) and eMAG error payloads
        such as rate-limit responses by retrying with exponential backoff.
        """

        if not self.client:
            raise EmagApiError("eMAG API client not initialized")

        attempt = 1
        delay = max(0.0, initial_delay)

        while attempt <= max_attempts:
            try:
                response = await self.client.create_product(product)

                if isinstance(response, dict) and not response.get("isError", False):
                    return response

                # Treat error payloads as transient failures and retry
                error_messages = []
                if isinstance(response, dict):
                    error_messages = response.get("messages", [])

                logger.warning(
                    "Create product attempt %s/%s failed for %s: %s",
                    attempt,
                    max_attempts,
                    getattr(product, "sku", getattr(product, "id", "unknown")),
                    ", ".join(error_messages) or "Unknown API error",
                )
                raise EmagApiError("eMAG API returned error payload", response=response)

            except Exception as exc:
                if attempt >= max_attempts:
                    logger.error(
                        "Create product exhausted retries for %s: %s",
                        getattr(product, "sku", getattr(product, "id", "unknown")),
                        exc,
                    )
                    raise

                logger.warning(
                    "Create product attempt %s/%s failed for %s: %s. Retrying in %.2fs",
                    attempt,
                    max_attempts,
                    getattr(product, "sku", getattr(product, "id", "unknown")),
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                attempt += 1
                delay = delay * 2 if delay else 0.5

        # This line should not be reached, but keeps type checkers happy
        raise EmagApiError("Unable to create product after retries")

    async def _execute_bulk_operation(
        self,
        items: list[Any],
        operation_func: Callable[[list[Any]], Awaitable[dict[str, Any]]],
        operation_name: str,
        chunk_size: int | None = None,
        validate_item: Callable[[Any], bool] | None = None,
    ) -> dict[str, Any]:
        """Generic bulk operation executor with proper chunking and validation."""

        if not items:
            return {
                "message": f"No {operation_name} items to process",
                "processed": 0,
                "total_processed": 0,
                "total_errors": 0,
                "chunks_processed": 0,
                "results": [],
            }

        # Validate items if validator provided
        valid_items = []
        invalid_count = 0

        if validate_item:
            for item in items:
                if validate_item(item):
                    valid_items.append(item)
                else:
                    invalid_count += 1
                    logger.warning(
                        f"Invalid {operation_name} item filtered out: {item}"
                    )
        else:
            valid_items = items

        if not valid_items:
            return {
                "message": f"All {operation_name} items were invalid",
                "processed": 0,
                "total_processed": 0,
                "total_errors": len(items),
                "chunks_processed": 0,
                "results": [],
            }

        chunk_size = chunk_size or self.config.bulk_max_entities
        chunks = [
            valid_items[i : i + chunk_size]
            for i in range(0, len(valid_items), chunk_size)
        ]

        total_processed = 0
        total_errors = invalid_count  # Start with validation errors
        results = []

        for i, chunk in enumerate(chunks):
            try:
                logger.info(
                    f"Processing {operation_name} chunk {i + 1}/{len(chunks)} with {len(chunk)} items"
                )

                # Execute the operation on this chunk
                chunk_result = await operation_func(chunk)
                results.append(chunk_result)
                total_processed += len(chunk)

                # Add small delay between chunks to avoid overwhelming the API
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to process {operation_name} chunk {i + 1}: {e}")
                total_errors += len(chunk)
                results.append({"error": str(e), "chunk": i + 1})

        return {
            "message": f"Processed {total_processed} {operation_name} items in {len(chunks)} chunks",
            "total_processed": total_processed,
            "total_errors": total_errors,
            "chunks_processed": len(chunks),
            "results": results,
        }

    async def start_auto_sync(self, sync_interval: int = 300) -> str:
        """Start automatic synchronization with eMAG."""
        task_id = f"emag_sync_{datetime.now().isoformat()}"

        async def sync_task():
            while True:
                try:
                    # Sync products
                    product_results = await self.sync_products()
                    logger.info("Product sync completed: %s", product_results)

                    # Sync orders
                    order_results = await self.sync_orders()
                    logger.info("Order sync completed: %s", order_results)

                    # Sync inventory
                    inventory_updates = await self._get_inventory_updates()
                    if inventory_updates:
                        inventory_results = await self.bulk_update_inventory(
                            inventory_updates,
                        )
                        logger.info("Inventory sync completed: %s", inventory_results)

                except Exception as e:
                    logger.error("Auto sync failed: %s", e)

                await asyncio.sleep(sync_interval)

        task = asyncio.create_task(sync_task())
        self._sync_tasks[task_id] = task

        logger.info("Started eMAG auto sync with %d second interval", sync_interval)
        return task_id

    async def stop_auto_sync(self, task_id: str) -> bool:
        """Stop automatic synchronization."""
        if task_id in self._sync_tasks:
            task = self._sync_tasks[task_id]
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

            del self._sync_tasks[task_id]
            logger.info("Stopped eMAG auto sync task: %s", task_id)
            return True

        return False

    # Private helper methods
    async def _get_emag_products(self) -> list[EmagProduct]:
        """Get products from eMAG API."""
        try:
            response = await self.client.get_products()
            products_data = response.get("products", [])

            products = []
            for product_data in products_data:
                product = EmagProduct(
                    id=product_data.get("id"),
                    name=product_data.get("name", ""),
                    sku=product_data.get("sku", ""),
                    description=product_data.get("description", ""),
                    price=float(product_data.get("price", 0)),
                    currency=product_data.get("currency", "RON"),
                    stock_quantity=int(product_data.get("stock", 0)),
                    emag_category_id=product_data.get("category_id"),
                    brand=product_data.get("brand", ""),
                    images=product_data.get("images", []),
                    emag_characteristics=product_data.get("characteristics", {}),
                )
                products.append(product)

            return products

        except Exception as e:
            logger.error("Failed to get products from eMAG: %s", e)
            raise

    async def _get_erp_products(self) -> list[EmagProduct]:
        """Get products from ERP system."""
        try:
            # Get products from repository
            products = await self.product_repository.get_all()

            erp_products = []
            for product in products:
                erp_product = EmagProduct(
                    id=str(product.id),
                    name=product.name,
                    sku=product.sku,
                    description=product.description or "",
                    price=float(product.price),
                    currency="RON",
                    stock_quantity=product.stock_quantity,
                    is_active=product.is_active,
                )
                erp_products.append(erp_product)

            return erp_products

        except Exception as e:
            logger.error("Failed to get products from ERP: %s", e)
            raise

    async def _create_erp_product(self, emag_product: EmagProduct):
        """Create product in ERP system."""
        try:
            product_data = {
                "name": emag_product.name,
                "sku": emag_product.sku,
                "description": emag_product.description,
                "price": emag_product.price,
                "stock_quantity": emag_product.stock_quantity,
                "is_active": emag_product.is_active,
            }

            await self.product_repository.create(product_data)

        except Exception as e:
            logger.error("Failed to create product in ERP: %s", e)
            raise

    async def _update_erp_product(
        self,
        erp_product: EmagProduct,
        emag_product: EmagProduct,
    ):
        """Update product in ERP system."""
        try:
            update_data = {
                "name": emag_product.name,
                "description": emag_product.description,
                "price": emag_product.price,
                "stock_quantity": emag_product.stock_quantity,
                "is_active": emag_product.is_active,
            }

            await self.product_repository.update(erp_product.id, update_data)

        except Exception as e:
            logger.error("Failed to update product in ERP: %s", e)
            raise

    async def _handle_missing_emag_product(self, sku: str):
        """Handle products that exist in ERP but not in eMAG."""
        # For now, just log the issue
        # In production, this might create the product on eMAG or mark it as inactive
        logger.warning("Product %s exists in ERP but not in eMAG", sku)

    async def _get_emag_orders(self) -> list[EmagOrder]:
        """Get orders from eMAG API."""
        try:
            response = await self.client.get_orders()
            orders_data = response.get("orders", [])

            orders = []
            for order_data in orders_data:
                orders.append(self._build_emag_order(order_data))

            return orders

        except Exception as e:
            logger.error("Failed to get orders from eMAG: %s", e)
            raise

    def _build_emag_order(self, order_data: dict[str, Any]) -> EmagOrder:
        """Create an `EmagOrder` instance from raw API payload with robust parsing."""
        return EmagOrder(
            id=str(order_data.get("id", "")),
            emag_order_id=str(
                order_data.get("emag_order_id") or order_data.get("id", "")
            ),
            status=order_data.get("status", ""),
            customer_name=order_data.get("customer_name", ""),
            customer_email=order_data.get("customer_email", ""),
            total_amount=float(order_data.get("total_amount", 0) or 0),
            currency=order_data.get("currency", "RON"),
            order_date=self._parse_emag_datetime(order_data.get("order_date")),
            items=list(order_data.get("items", [])),
            shipping_address=dict(order_data.get("shipping_address", {})),
            billing_address=dict(order_data.get("billing_address", {})),
            payment_method=order_data.get("payment_method", ""),
            shipping_cost=float(order_data.get("shipping_cost", 0) or 0),
        )

    def _parse_emag_datetime(self, value: Any) -> datetime | None:
        """Parse eMAG datetime formats safely.

        Supports ISO 8601 strings (with or without timezone or trailing Z) and Unix
        timestamps. Returns `None` when parsing fails instead of raising to avoid
        aborting the entire sync.
        """
        if isinstance(value, datetime):
            return value

        if value is None:
            return None

        # Handle numeric timestamps (seconds since epoch)
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=UTC)
            except (OverflowError, OSError, ValueError) as exc:
                logger.warning("Invalid timestamp for eMAG order date: %s", exc)
                return None

        if not isinstance(value, str):
            logger.warning("Unexpected eMAG order date type: %r", value)
            return None

        trimmed = value.strip()
        if not trimmed:
            return None

        iso_candidate = trimmed.replace("Z", "+00:00")

        try:
            return datetime.fromisoformat(iso_candidate)
        except ValueError:
            pass

        fallback_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in fallback_formats:
            try:
                parsed = datetime.strptime(iso_candidate, fmt)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=UTC)
                return parsed
            except ValueError:
                continue

        logger.warning("Failed to parse eMAG order date: %s", value)
        return None

    async def _map_order_payload(self, emag_order: EmagOrder) -> dict[str, Any]:
        """Prepare create/update payloads for ERP order persistence."""

        customer_id = await self._resolve_customer_id(emag_order)
        order_lines = await self._map_order_lines(emag_order.items)

        create_payload = {
            "customer_id": customer_id,
            "total_amount": emag_order.total_amount,
            "status": self._map_emag_order_status(emag_order.status),
            "order_date": emag_order.order_date or datetime.now(UTC),
            "fulfillment_channel": self.account_type,
        }

        update_payload = {
            "total_amount": emag_order.total_amount,
            "status": self._map_emag_order_status(emag_order.status),
            "fulfillment_channel": self.account_type,
        }

        if order_lines:
            create_payload["order_lines_data"] = order_lines

        if order_lines:
            update_payload["order_lines_data"] = order_lines

        existing = await self.order_repository.get_by_external_id(
            external_id=emag_order.emag_order_id or emag_order.id,
            external_source=f"emag:{self.account_type}",
        )

        return {
            "create": create_payload,
            "update": update_payload,
            "is_update": existing is not None,
        }

    async def _map_order_lines(
        self, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        mapped: list[dict[str, Any]] = []
        for item in items:
            product_id = await self._resolve_product_id(item)
            mapped.append(
                {
                    "product_id": product_id,
                    "quantity": item.get("quantity") or 1,
                    "unit_price": float(item.get("price") or 0.0),
                }
            )
        return mapped

    async def _resolve_customer_id(self, emag_order: EmagOrder) -> int:
        # Placeholder: in production map eMAG customer to ERP user/customer entity
        return 1

    async def _resolve_product_id(self, item: dict[str, Any]) -> int | None:
        sku = item.get("sku")
        if not sku:
            return None
        product = await self.product_repository.get_by_sku(sku)
        return product.id if product else None

    async def _get_inventory_updates(self) -> list[dict[str, Any]]:
        """Get inventory updates that need to be synced to eMAG."""
        try:
            # Get products with low stock or recent updates
            products = await self.product_repository.get_all()

            updates = []
            for product in products:
                if product.stock_quantity <= 10:  # Low stock threshold
                    updates.append(
                        {"sku": product.sku, "quantity": product.stock_quantity},
                    )

            return updates

        except Exception as e:
            logger.error("Failed to get inventory updates: %s", e)
            return []

    def _map_emag_order_status(self, emag_status: str) -> str:
        """Map eMAG order status to ERP status."""
        status_mapping = {
            "new": "pending",
            "confirmed": "confirmed",
            "in_progress": "processing",
            "shipped": "shipped",
            "delivered": "delivered",
            "cancelled": "cancelled",
            "returned": "returned",
        }
        return status_mapping.get(emag_status, "pending")

    async def get_product_offers(
        self,
        account_type: str,
        status: str = None,
        category_id: str = None,
        brand: str = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get product offers from eMAG."""
        try:
            if not self.client:
                raise EmagApiError("eMAG API client not initialized")

            # Build query parameters
            params = {"page": page, "limit": limit, "account_type": account_type}

            if status:
                params["status"] = status
            if category_id:
                params["category_id"] = category_id
            if brand:
                params["brand"] = brand

            return await self._make_request("GET", "/product_offers", params=params)

        except Exception as e:
            logger.error(
                "Failed to get product offers from eMAG %s: %s",
                account_type,
                e,
            )
            raise

    async def search_product_offers(
        self,
        query: str,
        account_type: str = None,
        category_id: str = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search for product offers on eMAG."""
        try:
            if not self.client:
                raise EmagApiError("eMAG API client not initialized")

            # Build query parameters
            params = {"q": query, "page": page, "limit": limit}

            if account_type:
                params["account_type"] = account_type
            if category_id:
                params["category_id"] = category_id

            return await self._make_request(
                "GET",
                "/product_offers/search",
                params=params,
            )

        except Exception as e:
            logger.error("Failed to search product offers on eMAG: %s", e)
            raise

    async def get_offer_details(
        self,
        offer_id: str,
        account_type: str,
    ) -> dict[str, Any]:
        """Get detailed information for a specific offer."""
        try:
            if not self.client:
                raise EmagApiError("eMAG API client not initialized")

            return await self._make_request(
                "GET",
                f"/product_offers/{offer_id}",
                params={"account_type": account_type},
            )

        except Exception as e:
            logger.error(
                "Failed to get offer details for %s from eMAG %s: %s",
                offer_id,
                account_type,
                e,
            )
            raise

    async def sync_with_progress_callback(
        self,
        progress_callback: Callable[[dict[str, Any]], Awaitable[None]],
        account_type: str,
        max_pages: int = 100,
    ) -> dict[str, Any]:
        """Sync products with real-time progress callback."""
        try:
            total_synced = 0
            page = 1

            await progress_callback(
                {
                    "status": "started",
                    "account_type": account_type,
                    "message": f"Starting sync for {account_type} account",
                },
            )

            while page <= max_pages:
                try:
                    # Get products for current page
                    response = await self.client.get_products(page=page, limit=100)

                    products = response.get("products", [])
                    if not products:
                        break

                    total_synced += len(products)

                    # Process products in batches
                    await self._process_products_batch(products)

                    # Send progress update
                    await progress_callback(
                        {
                            "status": "in_progress",
                            "account_type": account_type,
                            "current_page": page,
                            "total_synced": total_synced,
                            "percentage": min((page / max_pages) * 100, 100),
                            "message": f"Synced {total_synced} products from {account_type}",
                        },
                    )

                    page += 1

                    # Rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    await progress_callback(
                        {
                            "status": "error",
                            "account_type": account_type,
                            "error": str(e),
                            "message": f"Error on page {page}: {e}",
                        },
                    )
                    break

            await progress_callback(
                {
                    "status": "completed",
                    "account_type": account_type,
                    "total_synced": total_synced,
                    "message": f"Completed sync for {account_type}: {total_synced} products",
                },
            )

            return {"total_synced": total_synced}

        except Exception as e:
            await progress_callback(
                {
                    "status": "failed",
                    "account_type": account_type,
                    "error": str(e),
                    "message": f"Sync failed for {account_type}: {e}",
                },
            )
            raise

    async def get_all_products_sync(
        self,
        account_type: str,
        max_pages: int = 100,
        delay_between_requests: float = 0.1,
    ) -> list[dict[str, Any]]:
        """Get all products from eMAG account with pagination."""
        try:
            if not self.client:
                raise EmagApiError("eMAG API client not initialized")

            all_products = []
            page = 1
            total_pages = 1

            logger.info(f"Starting full product sync for {account_type}")

            while page <= total_pages and page <= max_pages:
                try:
                    # Get products for current page
                    response = await self.client.get_products(
                        page=page,
                        limit=100,  # Maximum allowed by eMAG API
                    )

                    products = response.get("products", [])
                    _total_count = response.get("total_count", 0)
                    total_pages = response.get("total_pages", 1)

                    if not products:
                        logger.info(f"No more products found on page {page}")
                        break

                    all_products.extend(products)
                    logger.info(
                        f"Retrieved {len(products)} products from page {page}/{total_pages} ({len(all_products)} total)",
                    )

                    page += 1

                    # Rate limiting - respect eMAG API limits
                    await asyncio.sleep(delay_between_requests)

                except Exception as e:
                    logger.error(f"Error retrieving products from page {page}: {e}")
                    # Continue with next page even if one fails
                    page += 1
                    continue

            logger.info(
                f"Completed full product sync for {account_type}: {len(all_products)} products retrieved",
            )
            return all_products

        except Exception as e:
            logger.error(f"Failed to get all products from eMAG {account_type}: {e}")
            raise

    async def get_all_products(
        self,
        account_type: str,
        max_pages: int = 100,
        delay_between_requests: float = 0.1,
    ) -> list[dict[str, Any]]:
        """Get all offers from eMAG account with pagination."""
        try:
            if not self.client:
                raise EmagApiError("eMAG API client not initialized")

            all_offers = []
            page = 1
            total_pages = 1

            logger.info(f"Starting full offers sync for {account_type}")

            while page <= total_pages and page <= max_pages:
                try:
                    # Get offers for current page
                    response = await self.get_product_offers(
                        account_type=account_type,
                        page=page,
                        limit=100,
                    )

                    offers = response.get("offers", [])
                    _total_count = response.get("total_count", 0)
                    total_pages = response.get("total_pages", 1)

                    if not offers:
                        logger.info(f"No more offers found on page {page}")
                        break

                    all_offers.extend(offers)
                    logger.info(
                        f"Retrieved {len(offers)} offers from page {page}/{total_pages} ({len(all_offers)} total)",
                    )

                    page += 1

                    # Rate limiting
                    if delay_between_requests > 0:
                        await asyncio.sleep(delay_between_requests)

                except Exception as e:
                    logger.error(f"Error retrieving offers from page {page}: {e}")
                    page += 1
                    continue

            logger.info(
                f"Completed full offers sync for {account_type}: {len(all_offers)} offers retrieved",
            )
            return all_offers

        except Exception as e:
            logger.error(f"Failed to get all offers from eMAG {account_type}: {e}")
            raise

    async def sync_all_products_from_both_accounts(
        self,
        max_pages_per_account: int = 100,
        delay_between_requests: float = 0.1,
    ) -> dict[str, Any]:
        """Sync products from both MAIN and FBE accounts with duplicate detection."""
        try:
            logger.info(
                "Starting products sync from both accounts with duplicate detection",
            )

            # Sync from MAIN account
            logger.info("Syncing from MAIN account...")
            main_products = await self.get_all_products(
                "main",
                max_pages_per_account,
                delay_between_requests,
            )

            # Sync from FBE account
            logger.info("Syncing from FBE account...")
            fbe_products = await self.get_all_products(
                "fbe",
                max_pages_per_account,
                delay_between_requests,
            )

            # Combine products and detect duplicates
            logger.info("Combining products and detecting duplicates...")
            combined_result = await self._combine_products_with_duplicate_detection(
                main_products,
                fbe_products,
            )

            # Store sync result
            sync_result = {
                "main_account": {
                    "products_count": len(main_products),
                    "pages_processed": max_pages_per_account,
                    "sync_duration_seconds": 0,  # Would be calculated
                },
                "fbe_account": {
                    "products_count": len(fbe_products),
                    "pages_processed": max_pages_per_account,
                    "sync_duration_seconds": 0,
                },
                "combined": combined_result,
                "sync_timestamp": datetime.now(UTC).isoformat(),
                "duplicate_detection_enabled": True,
            }

            logger.info(
                f"Products sync completed. Total: {combined_result['total_products']}, Duplicates detected: {combined_result['duplicates_detected']}",
            )

            return sync_result

        except Exception as e:
            logger.error(f"Failed to sync products from both accounts: {e}")
            raise

    async def _combine_products_with_duplicate_detection(
        self,
        main_products: list[dict[str, Any]],
        fbe_products: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Combine products from both accounts with duplicate detection."""
        try:
            all_products = []
            duplicates_info = []
            sku_map = {}  # sku -> [products]

            # Process MAIN products
            for product in main_products:
                sku = product.get("sku")
                if sku:
                    if sku not in sku_map:
                        sku_map[sku] = []
                    sku_map[sku].append(
                        {
                            "product": product,
                            "account": "main",
                            "first_seen": product.get(
                                "updated_at",
                                datetime.now(UTC).isoformat(),
                            ),
                        },
                    )

            # Process FBE products
            for product in fbe_products:
                sku = product.get("sku")
                if sku:
                    if sku not in sku_map:
                        sku_map[sku] = []
                    sku_map[sku].append(
                        {
                            "product": product,
                            "account": "fbe",
                            "first_seen": product.get(
                                "updated_at",
                                datetime.now(UTC).isoformat(),
                            ),
                        },
                    )

            # Analyze duplicates and prepare results
            _unique_products = []
            total_duplicates = 0

            for sku, sku_data in sku_map.items():
                if len(sku_data) > 1:
                    # Duplicate found - mark all as duplicates
                    total_duplicates += len(sku_data)

                    for item in sku_data:
                        product = item["product"].copy()
                        product["_is_duplicate"] = True
                        product["_duplicate_accounts"] = [
                            d["account"] for d in sku_data
                        ]
                        product["_duplicate_count"] = len(sku_data)
                        product["_first_account"] = sku_data[0]["account"]
                        all_products.append(product)

                        # Add to duplicates info
                        duplicates_info.append(
                            {
                                "sku": sku,
                                "duplicate_accounts": [d["account"] for d in sku_data],
                                "product_count": len(sku_data),
                                "accounts_involved": list(
                                    {d["account"] for d in sku_data},
                                ),
                            },
                        )
                else:
                    # No duplicate - mark as unique
                    product = sku_data[0]["product"].copy()
                    product["_is_duplicate"] = False
                    product["_duplicate_accounts"] = []
                    product["_duplicate_count"] = 1
                    product["_first_account"] = sku_data[0]["account"]
                    all_products.append(product)

            return {
                "total_products": len(all_products),
                "unique_products": len(
                    [p for p in all_products if not p.get("_is_duplicate", False)],
                ),
                "duplicate_products": len(
                    [p for p in all_products if p.get("_is_duplicate", False)],
                ),
                "duplicates_detected": len(duplicates_info),
                "duplicate_skus": duplicates_info,
                "all_products": all_products,
                "products_by_account": {
                    "main": len(
                        [p for p in all_products if p.get("_first_account") == "main"],
                    ),
                    "fbe": len(
                        [p for p in all_products if p.get("_first_account") == "fbe"],
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Failed to combine products with duplicate detection: {e}")
            raise

    async def sync_all_offers_from_both_accounts(
        self,
        max_pages_per_account: int = 100,
        delay_between_requests: float = 0.1,
    ) -> dict[str, Any]:
        """Sync all offers from both MAIN and FBE accounts."""
        try:
            logger.info("Starting full offers sync from both eMAG accounts")

            # Sync from MAIN account
            main_offers = await self.get_all_offers(
                account_type="main",
                max_pages=max_pages_per_account,
                delay_between_requests=delay_between_requests,
            )

            # Sync from FBE account
            fbe_offers = await self.get_all_offers(
                account_type="fbe",
                max_pages=max_pages_per_account,
                delay_between_requests=delay_between_requests,
            )

            # Combine and deduplicate offers
            all_offers = main_offers + fbe_offers

            # Create lookup for easy access
            offers_by_sku = {}
            for offer in all_offers:
                sku = offer.get("sku")
                if sku:
                    offers_by_sku[sku] = offer

            # Convert back to list
            combined_offers = list(offers_by_sku.values())

            result = {
                "main_account": {
                    "offers_count": len(main_offers),
                    "offers": main_offers,
                },
                "fbe_account": {"offers_count": len(fbe_offers), "offers": fbe_offers},
                "combined": {
                    "offers_count": len(combined_offers),
                    "offers": combined_offers,
                    "unique_skus": len(offers_by_sku),
                },
                "sync_timestamp": datetime.now(UTC).isoformat(),
                "total_offers_processed": len(all_offers),
            }

            logger.info(
                f"Completed full offers sync: MAIN={len(main_offers)}, FBE={len(fbe_offers)}, "
                f"Combined={len(combined_offers)} unique offers",
            )

            return result

        except Exception as e:
            logger.error(f"Failed to sync all offers from both accounts: {e}")
            raise

    async def get_product_details(
        self,
        product_id: str,
        account_type: str,
    ) -> dict[str, Any]:
        """Get detailed information for a specific product."""
        try:
            if not self.client:
                raise EmagApiError("eMAG API client not initialized")

            return await self._make_request(
                "GET",
                f"/products/{product_id}",
                params={"account_type": account_type},
            )

        except Exception as e:
            logger.error(
                f"Failed to get product details for {product_id} from eMAG {account_type}: {e}",
            )
            raise
