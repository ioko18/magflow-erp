"""eMAG Marketplace API Integration for MagFlow ERP.

This module provides comprehensive integration with the eMAG marketplace API,
enabling product synchronization, order management, inventory updates, and
real-time marketplace connectivity.
"""

import asyncio
import base64
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set
from urllib.parse import urljoin

import aiohttp

from app.core.dependency_injection import ServiceBase, ServiceContext
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


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


class EmagApiError(Exception):
    """Base exception for eMAG API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = None,
        details: Dict[str, Any] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


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
        if self.environment == EmagApiEnvironment.PRODUCTION:
            self.base_url = "https://api.emag.ro"
        else:
            self.base_url = "https://api-sandbox.emag.ro"

        # Validate required fields for Basic Auth
        if not self.api_username or not self.api_password:
            raise ConfigurationError(
                "eMAG API username and password are required for Basic Auth"
            )


@dataclass
class EmagRateLimiter:
    """Rate limiter for eMAG API with different limits per resource type."""

    orders_rps: int = 12  # 12 requests per second for orders
    other_rps: int = 3  # 3 requests per second for other endpoints
    jitter_max: float = 0.1  # Maximum jitter to avoid thundering herd
    window_seconds: float = 1.0  # Duration of the rate limit window
    sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep  # Injectable sleep function

    def __post_init__(self):
        self._last_request_times: Dict[str, float] = {}
        self._request_counts: Dict[str, int] = {}
        self._windows: Dict[str, float] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def acquire(self, resource_type: str = "other"):
        """Acquire permission to make a request.

        Args:
            resource_type: "orders" or "other"

        """
        rps_limit = self.orders_rps if resource_type == "orders" else self.other_rps
        window_duration = self.window_seconds

        # Lazily create a lock per resource type to synchronize concurrent callers
        lock = self._locks.setdefault(resource_type, asyncio.Lock())

        time_source = time.monotonic

        while True:
            async with lock:
                now = time_source()

                window_start = self._windows.get(resource_type)
                if window_start is None or now - window_start >= window_duration:
                    self._windows[resource_type] = now
                    self._request_counts[resource_type] = 0
                    window_start = now

                if self._request_counts[resource_type] < rps_limit:
                    self._request_counts[resource_type] += 1
                    self._last_request_times[resource_type] = now
                    return

                wait_time = window_duration - (now - window_start)
                if wait_time <= 0:
                    # Window already expired due to scheduling delays; reset and retry
                    self._windows[resource_type] = now
                    self._request_counts[resource_type] = 0
                    continue

                # Add jitter to avoid thundering herd effects when waiting
                import random

                sleep_duration = wait_time + random.uniform(0, self.jitter_max)

            await self.sleep_fn(sleep_duration)


@dataclass
class EmagProduct:
    """eMAG product data structure with v4.4.8 fields."""

    id: Optional[str] = None
    name: str = ""
    sku: str = ""
    description: str = ""
    price: float = 0.0
    currency: str = "RON"
    stock_quantity: int = 0
    category_id: Optional[str] = None
    brand: str = ""
    images: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    emag_category_id: Optional[str] = None
    emag_characteristics: Dict[str, Any] = field(default_factory=dict)

    # New v4.4.8 fields
    images_overwrite: bool = False  # Control append vs overwrite behavior
    green_tax: Optional[float] = None  # RO only, includes TVA
    supply_lead_time: Optional[int] = None  # 2,3,5,7,14,30,60,90,120 days

    # GPSR (General Product Safety Regulation) fields
    safety_information: Optional[str] = None
    manufacturer: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{name, address, email}]
    eu_representative: List[Dict[str, str]] = field(
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
    items: List[Dict[str, Any]] = field(default_factory=list)
    shipping_address: Dict[str, Any] = field(default_factory=dict)
    billing_address: Dict[str, Any] = field(default_factory=dict)
    payment_method: str = ""
    shipping_cost: float = 0.0


class EmagApiClient:
    """Client for eMAG Marketplace API integration."""

    def __init__(self, config: EmagApiConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = EmagRateLimiter(
            orders_rps=config.orders_rate_rps,
            other_rps=config.other_rate_rps,
        )
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._request_count = 0
        self._last_request_time = datetime.now()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize the API client."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.api_timeout),
        )

        # Authenticate to get access token
        await self.authenticate()

        logger.info(
            "eMAG API client initialized for %s environment",
            self.config.environment.value,
        )

    async def close(self):
        """Close the API client."""
        if self.session:
            await self.session.close()
        logger.info("eMAG API client closed")

    async def authenticate(self):
        """Authenticate with eMAG API and get access token."""
        # eMAG uses basic authentication, not OAuth2
        # Create basic auth header
        credentials = f"{self.config.api_username}:{self.config.api_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.access_token = f"Basic {encoded_credentials}"
        # For Basic auth, set a far-future expiry to avoid re-auth recursion
        self.token_expires_at = datetime.now() + timedelta(days=1)

        logger.info("Successfully prepared eMAG API authentication (using Basic Auth)")

        # Test the connection
        try:
            # Make a test request to verify credentials (but don't fail if it doesn't exist)
            await self._make_request("GET", "/test")
            logger.info("eMAG API authentication test successful")
        except Exception as e:
            logger.warning(
                "eMAG API authentication test failed (this is normal): %s",
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
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to eMAG API with proper rate limiting."""
        await self._ensure_authenticated()

        # Determine resource type for rate limiting
        resource_type = self._get_resource_type(endpoint)

        # Apply rate limiting
        await self.rate_limiter.acquire(resource_type)

        url = urljoin(self.config.base_url, endpoint)

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
                        json_val = response.json()
                        response_data = (
                            await json_val
                            if inspect.isawaitable(json_val)
                            else json_val
                        )
                except TypeError:
                    # Fallback: treat req_obj as response directly
                    response = req_obj
                    json_val = response.json()
                    response_data = (
                        await json_val if inspect.isawaitable(json_val) else json_val
                    )

                self._request_count += 1

                status_code = getattr(response, "status", 200)

                # Ensure we received a JSON object we can reason about
                if not isinstance(response_data, dict):
                    logger.warning(
                        "eMAG API response returned non-object JSON: %s", response_data
                    )
                    raise EmagApiError(
                        "Invalid API response: expected JSON object",
                        status_code,
                        {"raw_response": response_data},
                    )

                # Check for isError field - all responses must have it
                if "isError" not in response_data:
                    logger.warning(
                        "eMAG API response missing 'isError' field: %s", response_data
                    )
                    raise EmagApiError(
                        "Invalid API response: missing 'isError' field",
                        status_code,
                        response_data,
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
                    if status_code == 429:  # Rate limit exceeded
                        if retry_count < max_retries:
                            # Exponential backoff with jitter
                            import random

                            wait_time = (2**retry_count) + random.uniform(0, 1)
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

                    error_text = response_data.get("messages", ["Unknown error"])[0]
                    raise EmagApiError(
                        f"API request failed: {error_text}",
                        status_code,
                        response_data,
                    )

                return response_data

            except aiohttp.ClientError as e:
                if retry_count < max_retries:
                    wait_time = self.config.retry_delay * (2**retry_count)
                    logger.warning(f"Request failed, retrying in {wait_time:.2f}s: {e}")
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                    continue
                raise EmagApiError(f"Request failed after {max_retries} retries: {e}")

        raise EmagApiError(f"Request failed after {max_retries} retries")

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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

    async def get_products(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get products from eMAG."""
        return await self._make_request("GET", f"/products?page={page}&limit={limit}")

    async def create_product(self, product: EmagProduct) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
        """Get orders from eMAG."""
        params = {"page": page, "limit": limit}

        if status:
            params["status"] = status
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        return await self._make_request("GET", "/orders", params=params)

    async def update_order_status(self, order_id: str, status: str) -> Dict[str, Any]:
        """Update order status on eMAG."""
        return await self._make_request(
            "PUT",
            f"/orders/{order_id}/status",
            data={"status": status},
        )

    async def get_categories(self, parent_id: str = None) -> Dict[str, Any]:
        """Get product categories from eMAG."""
        params = {}
        if parent_id:
            params["parent_id"] = parent_id

        return await self._make_request("GET", "/categories", params=params)

    async def sync_inventory(self, sku: str, quantity: int) -> Dict[str, Any]:
        """Sync inventory for a specific product."""
        return await self._make_request(
            "PUT",
            f"/inventory/{sku}",
            data={"quantity": quantity},
        )

    async def bulk_update_inventory(
        self,
        inventory_updates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Bulk update inventory for multiple products."""
        return await self._make_request(
            "PUT",
            "/inventory/bulk",
            data={"updates": inventory_updates},
        )

    async def smart_deals_price_check(self, product_id: str) -> Dict[str, Any]:
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
            raise EmagApiError(f"Smart Deals price check failed: {e}")


class EmagIntegrationService(ServiceBase):
    """Service for managing eMAG marketplace integration."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self.config = self._load_config()
        self.api_client: Optional[EmagApiClient] = None
        # Temporarily disable repositories until service registry is properly initialized
        self.product_repository = None  # get_product_repository()
        self.order_repository = None  # get_order_repository()
        self._sync_tasks: Dict[str, asyncio.Task] = {}

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
            }

            if normalized in aliases:
                return aliases[normalized]

        raise ConfigurationError(
            "Invalid EMAG_ENVIRONMENT value. Expected one of: "
            "production, prod, live, sandbox, sand, test."
        )

    def _load_config(self) -> EmagApiConfig:
        """Load eMAG API configuration."""
        settings = self.context.settings

        # Get configuration from settings
        environment = getattr(settings, "EMAG_ENVIRONMENT", "production")

        # Use MAIN account credentials by default
        api_username = getattr(settings, "EMAG_MAIN_USERNAME", "") or getattr(
            settings, "EMAG_USERNAME", ""
        )
        api_password = getattr(settings, "EMAG_MAIN_PASSWORD", "") or getattr(
            settings, "EMAG_PASSWORD", ""
        )

        # If no credentials found, raise error
        if not api_username or not api_password:
            raise ConfigurationError(
                "eMAG API username and password are required for Basic Auth. "
                "Set EMAG_MAIN_USERNAME and EMAG_MAIN_PASSWORD in environment variables.",
            )

        api_timeout = getattr(settings, "EMAG_REQUEST_TIMEOUT", 30)
        orders_rate_rps = getattr(settings, "EMAG_RATE_ORDERS_RPS", 12)
        other_rate_rps = getattr(settings, "EMAG_RATE_OTHER_RPS", 3)

        try:
            return EmagApiConfig(
                environment=self._normalize_environment(environment),
                api_username=api_username,
                api_password=api_password,
                api_timeout=api_timeout,
                orders_rate_rps=orders_rate_rps,
                other_rate_rps=other_rate_rps,
            )
        except ConfigurationError as e:
            logger.error("Failed to load eMAG configuration: %s", e)
            raise ConfigurationError(f"eMAG integration not properly configured: {e}")

    async def initialize(self):
        """Initialize eMAG integration service."""
        try:
            self.api_client = EmagApiClient(self.config)
            await self.api_client.initialize()
            logger.info("eMAG integration service initialized")
        except Exception as e:
            logger.error("Failed to initialize eMAG integration service: %s", e)
            raise

    async def cleanup(self):
        """Cleanup eMAG integration service."""
        if self.api_client:
            await self.api_client.close()

        # Cancel any running sync tasks
        for task in self._sync_tasks.values():
            task.cancel()

        self._sync_tasks.clear()
        logger.info("eMAG integration service cleaned up")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Delegate HTTP requests to the underlying API client.

        Prefers a public request helper on the client when available,
        otherwise safely falls back to the protected `_make_request`
        implementation to maintain compatibility with the existing client
        contract without duplicating logic in this service.
        """

        if not self.api_client:
            raise EmagApiError("eMAG API client not initialized")

        # Prefer a public request helper when available to avoid relying on
        # internals of the API client.
        request_fn = getattr(self.api_client, "request", None)
        if request_fn:
            return await request_fn(method, endpoint, data=data, params=params)

        return await self.api_client._make_request(  # pylint: disable=protected-access
            method,
            endpoint,
            data=data,
            params=params,
        )

    @performance_monitor("EmagIntegrationService.sync_products")
    async def sync_products(self, full_sync: bool = False) -> Dict[str, Any]:
        """Sync products between ERP and eMAG."""
        try:
            if not self.api_client:
                raise EmagApiError("eMAG API client not initialized")

            # Get products from eMAG
            emag_products = await self._get_emag_products()

            # Get products from ERP
            erp_products = await self._get_erp_products()

            # Build SKU lookup map once to avoid repeated linear scans when
            # reconciling products. This dramatically reduces the complexity of
            # the sync from O(n^2) to O(n) for large catalogs.
            erp_products_by_sku = {}
            duplicate_erp_skus = set()

            for product in erp_products:
                if not product.sku:
                    continue

                if product.sku in erp_products_by_sku:
                    duplicate_erp_skus.add(product.sku)
                    continue

                erp_products_by_sku[product.sku] = product

            if duplicate_erp_skus:
                logger.warning(
                    "Duplicate SKU entries detected in ERP during sync: %s",
                    sorted(duplicate_erp_skus),
                )

            # Compare and sync
            sync_results = {"created": [], "updated": [], "deleted": [], "errors": []}

            # Process products
            for emag_product in emag_products:
                try:
                    erp_product = erp_products_by_sku.get(emag_product.sku)

                    if not erp_product:
                        # Create new product in ERP
                        await self._create_erp_product(emag_product)
                        sync_results["created"].append(emag_product.sku)
                    else:
                        # Update existing product
                        await self._update_erp_product(erp_product, emag_product)
                        sync_results["updated"].append(emag_product.sku)

                except Exception as e:
                    sync_results["errors"].append(
                        {"sku": emag_product.sku, "error": str(e)},
                    )

            # Handle products that exist in ERP but not in eMAG
            if full_sync:
                erp_skus = {p.sku for p in erp_products}
                emag_skus = {p.sku for p in emag_products}

                for sku in erp_skus - emag_skus:
                    try:
                        await self._handle_missing_emag_product(sku)
                        sync_results["deleted"].append(sku)
                    except Exception as e:
                        sync_results["errors"].append({"sku": sku, "error": str(e)})

            return sync_results

        except Exception as e:
            logger.error("Product sync failed: %s", e)
            raise EmagApiError(f"Product sync failed: {e}")

    @performance_monitor("EmagIntegrationService.sync_orders")
    async def sync_orders(self) -> Dict[str, Any]:
        """Sync orders between ERP and eMAG."""
        try:
            if not self.api_client:
                raise EmagApiError("eMAG API client not initialized")

            # Get orders from eMAG
            emag_orders = await self._get_emag_orders()

            sync_results = {"created": [], "updated": [], "errors": []}

            for emag_order in emag_orders:
                try:
                    # Check if order exists in ERP
                    erp_order = await self.order_repository.get_by_id(emag_order.id)

                    if not erp_order:
                        # Create new order in ERP
                        await self._create_erp_order(emag_order)
                        sync_results["created"].append(emag_order.id)
                    else:
                        # Update existing order
                        await self._update_erp_order(erp_order, emag_order)
                        sync_results["updated"].append(emag_order.id)

                except Exception as e:
                    sync_results["errors"].append(
                        {"order_id": emag_order.id, "error": str(e)},
                    )

            return sync_results

        except Exception as e:
            logger.error("Order sync failed: %s", e)
            raise EmagApiError(f"Order sync failed: {e}")

    async def update_inventory(self, sku: str, quantity: int) -> bool:
        """Update inventory for a specific product."""
        try:
            if not self.api_client:
                raise EmagApiError("eMAG API client not initialized")

            result = await self.api_client.sync_inventory(sku, quantity)
            return result.get("success", False)

        except Exception as e:
            logger.error("Inventory update failed for SKU %s: %s", sku, e)
            return False

    async def bulk_update_inventory(
        self,
        inventory_updates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Bulk update inventory for multiple products."""
        try:
            if not self.api_client:
                raise EmagApiError("eMAG API client not initialized")

            # Validate and filter inventory updates
            validated_updates: List[Dict[str, Any]] = []
            for update in inventory_updates:
                if (
                    not isinstance(update, dict)
                    or "sku" not in update
                    or "quantity" not in update
                ):
                    logger.warning(f"Invalid inventory update format: {update}")
                    continue
                validated_updates.append(
                    {
                        "sku": str(update["sku"]),
                        "quantity": update["quantity"],
                    }
                )

            deduped_updates: OrderedDict[str, Dict[str, Any]] = OrderedDict()
            duplicate_skus: Set[str] = set()

            for inventory_update in validated_updates:
                sku = inventory_update["sku"]

                if sku in deduped_updates:
                    duplicate_skus.add(sku)
                    deduped_updates[sku] = inventory_update
                    deduped_updates.move_to_end(sku)
                else:
                    deduped_updates[sku] = inventory_update

            deduped_list = list(deduped_updates.values())
            duplicates_filtered = len(validated_updates) - len(deduped_list)

            if duplicate_skus:
                logger.info(
                    "Collapsed %d duplicate inventory updates for SKUs: %s",
                    duplicates_filtered,
                    sorted(duplicate_skus),
                )

            # Use generic bulk operation executor
            async def process_chunk(chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
                return await self.api_client.bulk_update_inventory(chunk)

            result = await self._execute_bulk_operation(
                deduped_list,
                process_chunk,
                "inventory",
            )

            result["duplicate_skus_filtered"] = sorted(duplicate_skus)
            result["total_duplicates_filtered"] = duplicates_filtered
            result["items_before_dedup"] = len(validated_updates)
            result["items_after_dedup"] = len(deduped_list)

            return result

        except Exception as e:
            logger.error("Bulk inventory update failed: %s", e)
            raise EmagApiError(f"Bulk inventory update failed: {e}")

    async def _execute_bulk_operation(
        self,
        items: List[Any],
        operation_func: Callable[[List[Any]], Awaitable[Dict[str, Any]]],
        operation_name: str,
        chunk_size: Optional[int] = None,
        validate_item: Optional[Callable[[Any], bool]] = None,
    ) -> Dict[str, Any]:
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
                    f"Processing {operation_name} chunk {i+1}/{len(chunks)} with {len(chunk)} items"
                )

                # Execute the operation on this chunk
                chunk_result = await operation_func(chunk)
                results.append(chunk_result)
                total_processed += len(chunk)

                # Add small delay between chunks to avoid overwhelming the API
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to process {operation_name} chunk {i+1}: {e}")
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

            try:
                await task
            except asyncio.CancelledError:
                pass

            del self._sync_tasks[task_id]
            logger.info("Stopped eMAG auto sync task: %s", task_id)
            return True

        return False

    # Private helper methods
    async def _get_emag_products(self) -> List[EmagProduct]:
        """Get products from eMAG API."""
        try:
            response = await self.api_client.get_products()
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

    async def _get_erp_products(self) -> List[EmagProduct]:
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

    async def _get_emag_orders(self) -> List[EmagOrder]:
        """Get orders from eMAG API."""
        try:
            response = await self.api_client.get_orders()
            orders_data = response.get("orders", [])

            orders = []
            for order_data in orders_data:
                orders.append(self._build_emag_order(order_data))

            return orders

        except Exception as e:
            logger.error("Failed to get orders from eMAG: %s", e)
            raise

    def _build_emag_order(self, order_data: Dict[str, Any]) -> EmagOrder:
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

    def _parse_emag_datetime(self, value: Any) -> Optional[datetime]:
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
                return datetime.fromtimestamp(value, tz=timezone.utc)
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
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                continue

        logger.warning("Failed to parse eMAG order date: %s", value)
        return None

    async def _create_erp_order(self, emag_order: EmagOrder):
        """Create order in ERP system."""
        try:
            order_data = {
                "customer_id": 1,  # This should be mapped from eMAG customer
                "total_amount": emag_order.total_amount,
                "status": self._map_emag_order_status(emag_order.status),
                "order_lines": emag_order.items,
            }

            await self.order_repository.create(order_data)

        except Exception as e:
            logger.error("Failed to create order in ERP: %s", e)
            raise

    async def _update_erp_order(self, erp_order: EmagOrder, emag_order: EmagOrder):
        """Update order in ERP system."""
        try:
            update_data = {"status": self._map_emag_order_status(emag_order.status)}

            await self.order_repository.update(erp_order.id, update_data)

        except Exception as e:
            logger.error("Failed to update order in ERP: %s", e)
            raise

    async def _get_inventory_updates(self) -> List[Dict[str, Any]]:
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
    ) -> Dict[str, Any]:
        """Get product offers from eMAG."""
        try:
            if not self.api_client:
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
    ) -> Dict[str, Any]:
        """Search for product offers on eMAG."""
        try:
            if not self.api_client:
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
    ) -> Dict[str, Any]:
        """Get detailed information for a specific offer."""
        try:
            if not self.api_client:
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
        progress_callback: Callable[[Dict[str, Any]], Awaitable[None]],
        account_type: str,
        max_pages: int = 100,
    ) -> Dict[str, Any]:
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
                    response = await self.api_client.get_products(page=page, limit=100)

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
    ) -> List[Dict[str, Any]]:
        """Get all products from eMAG account with pagination."""
        try:
            if not self.api_client:
                raise EmagApiError("eMAG API client not initialized")

            all_products = []
            page = 1
            total_pages = 1

            logger.info(f"Starting full product sync for {account_type}")

            while page <= total_pages and page <= max_pages:
                try:
                    # Get products for current page
                    response = await self.api_client.get_products(
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
    ) -> List[Dict[str, Any]]:
        """Get all offers from eMAG account with pagination."""
        try:
            if not self.api_client:
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
    ) -> Dict[str, Any]:
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
                "sync_timestamp": datetime.utcnow().isoformat(),
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
        main_products: List[Dict[str, Any]],
        fbe_products: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
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
                                datetime.utcnow().isoformat(),
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
                                datetime.utcnow().isoformat(),
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
                                    set(d["account"] for d in sku_data),
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
    ) -> Dict[str, Any]:
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
                "sync_timestamp": datetime.utcnow().isoformat(),
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
    ) -> Dict[str, Any]:
        """Get detailed information for a specific product."""
        try:
            if not self.api_client:
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
