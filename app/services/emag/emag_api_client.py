"""
Enhanced eMAG API Client with improved error handling and retry logic.
"""

import logging
from typing import Any

import aiohttp
from aiohttp import ClientResponseError, ClientSession
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.emag_errors import RateLimitError as NewRateLimitError
from app.core.emag_rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class EmagApiError(Exception):
    """Base exception for eMAG API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict | None = None,
        error_code: str | None = None,
    ):
        self.status_code = status_code
        self.response = response
        self.error_code = error_code
        super().__init__(message)

    @property
    def is_rate_limit_error(self) -> bool:
        """Check if this is a rate limit error."""
        return self.status_code == 429 or self.error_code == "RATE_LIMIT_EXCEEDED"

    @property
    def is_auth_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.status_code in (401, 403) or self.error_code in (
            "AUTH_INVALID_CREDENTIALS",
            "AUTH_IP_NOT_WHITELISTED",
        )

    @property
    def is_validation_error(self) -> bool:
        """Check if this is a validation error."""
        return self.status_code == 400 or (
            self.error_code and self.error_code.startswith("VALIDATION_")
        )


class EmagApiClient:
    """eMAG API client with retry and rate limiting support."""

    # Default retry policy (can be overridden in __init__)
    _default_retry_policy = {
        "stop": stop_after_attempt(3),
        "wait": wait_exponential(multiplier=1, min=4, max=10),
        "retry": retry_if_exception_type(
            (
                aiohttp.ClientError,
                TimeoutError,
            )
        ),
        "before_sleep": before_sleep_log(logger, logging.WARNING),
        "reraise": True,
    }

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://marketplace-api.emag.ro/api-3",
        timeout: int = 60,
        max_retries: int = 3,
        use_rate_limiter: bool = True,
    ):
        """Initialize the eMAG API client.

        Args:
            username: eMAG API username/email
            password: eMAG API password
            base_url: Base URL for the eMAG API
            timeout: Request timeout in seconds (default 60s for large product lists)
            max_retries: Maximum number of retry attempts
            use_rate_limiter: Whether to use the new rate limiter
        """
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=10, sock_read=timeout)
        self.max_retries = max_retries
        self._session: ClientSession | None = None
        self._auth = aiohttp.BasicAuth(username, password)
        self.use_rate_limiter = use_rate_limiter
        self._rate_limiter = get_rate_limiter() if use_rate_limiter else None

        # Configure retry policy
        self.retry_policy = self._default_retry_policy.copy()
        self.retry_policy["stop"] = stop_after_attempt(max_retries)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Initialize the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                auth=self._auth,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make an HTTP request with retry logic."""
        if self._session is None or self._session.closed:
            await self.start()

        # Apply rate limiting if enabled
        if self._rate_limiter:
            # Determine operation type based on endpoint
            operation_type = "orders" if "/order" in endpoint.lower() else "other"
            try:
                await self._rate_limiter.acquire(operation_type, timeout=30.0)
            except NewRateLimitError as e:
                logger.warning(f"Rate limit exceeded: {e}")
                raise

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Log request details for debugging
        request_data = kwargs.get('json', {})
        logger.debug(
            f"eMAG API Request: {method} {url}\n"
            f"Payload: {request_data}"
        )

        try:
            async with self._session.request(method, url, **kwargs) as response:
                response.raise_for_status()

                # Handle empty responses
                content = await response.text()
                if not content.strip():
                    return {}

                data = await response.json()

                # Check for eMAG API errors
                if isinstance(data, dict) and data.get("isError", False):
                    messages = data.get("messages", [])
                    error_msg = "Unknown error"
                    error_code = None

                    if messages and isinstance(messages, list):
                        first_msg = messages[0]
                        if isinstance(first_msg, dict):
                            error_msg = first_msg.get("message", "Unknown error")
                            error_code = first_msg.get("code")
                        elif isinstance(first_msg, str):
                            error_msg = first_msg

                    raise EmagApiError(
                        f"eMAG API error: {error_msg}",
                        status_code=response.status,
                        response=data,
                        error_code=error_code,
                    )

                return data

        except ClientResponseError as e:
            error_msg = str(e)
            # Try to parse error response, but don't fail if connection is closed
            try:
                if hasattr(response, 'json'):
                    error_data = await response.json()
                    if (
                        isinstance(error_data, dict)
                        and "messages" in error_data
                        and error_data["messages"]
                    ):
                        error_msg = error_data["messages"][0]
                    elif isinstance(error_data, dict) and "message" in error_data:
                        error_msg = error_data["message"]
                    elif isinstance(error_data, str):
                        error_msg = error_data
            except (
                aiohttp.ClientError,
                ValueError,
                KeyError,
                IndexError,
                AttributeError,
            ) as parse_error:
                # Connection closed or other parsing error - use original error message
                logger.debug(f"Could not parse error response: {parse_error}")

            raise EmagApiError(
                f"HTTP {e.status}: {error_msg}",
                status_code=e.status,
                response=getattr(e, "response", None),
            ) from e

        except TimeoutError as e:
            # Provide detailed timeout error message
            error_msg = (
                f"Request timeout after {self.timeout.total}s for {method} {endpoint}. "
                "The eMAG API did not respond in time. This may be due to high server load or "
                "network issues. Please try again later or contact support if the issue persists."
            )
            logger.error(error_msg)
            raise EmagApiError(error_msg, status_code=408) from e
        except aiohttp.ClientError as e:
            # Provide detailed client error message
            error_msg = (
                f"Network error for {method} {endpoint}: {type(e).__name__} - "
                f"{str(e) or 'Connection failed'}. "
                "Please check your network connection and try again."
            )
            logger.error(error_msg)
            raise EmagApiError(error_msg) from e

    async def get_products(
        self,
        page: int = 1,
        items_per_page: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get a list of products from eMAG.

        CRITICAL: eMAG API requires POST method with JSON body, not GET with params!
        See: docs/EMAG_API_REFERENCE.md section 3.1
        """
        data = {
            "currentPage": page,
            "itemsPerPage": items_per_page,
        }

        # Add filters if provided
        if filters:
            # Handle status filter
            if "status" in filters:
                status_value = filters["status"]
                if status_value == "all":
                    # Don't add status filter to get all products
                    pass
                elif status_value == "active":
                    data["status"] = 1  # eMAG uses 1 for active
                elif status_value == "inactive":
                    data["status"] = 0  # eMAG uses 0 for inactive
                else:
                    data["status"] = status_value

            # Add other filters
            for key, value in filters.items():
                if key != "status":  # Already handled above
                    data[key] = value

        # FIXED: Use POST with JSON body instead of GET with params
        return await self._request("POST", "product_offer/read", json=data)

    async def get_orders(
        self,
        page: int = 1,
        items_per_page: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get a list of orders from eMAG.

        CRITICAL: eMAG API requires POST method with JSON body, not GET with params!

        Args:
            page: Page number for pagination
            items_per_page: Number of items per page
            filters: Optional filters dict (status, date_range, etc.)

        Returns:
            Dictionary containing the API response
        """
        data = {
            "currentPage": page,
            "itemsPerPage": items_per_page,
        }

        # Add filters if provided
        if filters:
            data.update(filters)

        # FIXED: Use POST with JSON body instead of GET with params
        return await self._request("POST", "order/read", json=data)

    async def update_stock(self, product_id: str, quantity: int) -> dict[str, Any]:
        """Update product stock in eMAG."""
        data = [
            {
                "id": product_id,
                "sale_stock": quantity,
            }
        ]
        return await self._request("POST", "stock_offer/save", json=data)

    # ========== NEW API v4.4.9 Methods ==========

    async def update_offer_light(
        self,
        product_id: int,
        sale_price: float | None = None,
        recommended_price: float | None = None,
        min_sale_price: float | None = None,
        max_sale_price: float | None = None,
        stock: list | None = None,
        handling_time: list | None = None,
        vat_id: int | None = None,
        status: int | None = None,
        currency_type: str | None = None,
    ) -> dict[str, Any]:
        """Update existing offer using Light Offer API (v4.4.9).

        This is the simplified endpoint for updating EXISTING offers only.
        Cannot create new offers or modify product information.

        Args:
            product_id: Seller internal product ID (required)
            sale_price: Sale price without VAT
            recommended_price: Recommended retail price without VAT
            min_sale_price: Minimum sale price
            max_sale_price: Maximum sale price
            stock: Stock array [{"warehouse_id": 1, "value": 25}]
            handling_time: Handling time array [{"warehouse_id": 1, "value": 1}]
            vat_id: VAT rate ID
            status: Offer status (0=inactive, 1=active, 2=end of life)
            currency_type: Currency (EUR or PLN)

        Returns:
            Dictionary containing the API response

        Example:
            await client.update_offer_light(
                product_id=243409,
                sale_price=179.99,
                stock=[{"warehouse_id": 1, "value": 25}]
            )
        """
        data = {"id": product_id}

        # Only include fields that are provided
        if sale_price is not None:
            data["sale_price"] = sale_price
        if recommended_price is not None:
            data["recommended_price"] = recommended_price
        if min_sale_price is not None:
            data["min_sale_price"] = min_sale_price
        if max_sale_price is not None:
            data["max_sale_price"] = max_sale_price
        if stock is not None:
            data["stock"] = stock
        if handling_time is not None:
            data["handling_time"] = handling_time
        if vat_id is not None:
            data["vat_id"] = vat_id
        if status is not None:
            data["status"] = status
        if currency_type is not None:
            data["currency_type"] = currency_type

        # IMPORTANT: Light Offer API expects an ARRAY of offers, not a single dict
        payload = [data]
        logger.info(f"Sending to offer/save endpoint: {payload}")
        return await self._request("POST", "offer/save", json=payload)

    async def update_product_offer(
        self,
        product_id: int,
        sale_price: float | None = None,
        recommended_price: float | None = None,
        min_sale_price: float | None = None,
        max_sale_price: float | None = None,
        stock: list | None = None,
        handling_time: list | None = None,
        vat_id: int | None = None,
        status: int | None = None,
    ) -> dict[str, Any]:
        """Update existing offer using Traditional API (product_offer/save).

        This is the traditional endpoint that wraps payload in array format.
        More reliable than Light API for price updates.

        Args:
            product_id: Seller internal product ID (required)
            sale_price: Sale price without VAT
            recommended_price: Recommended retail price without VAT
            min_sale_price: Minimum sale price
            max_sale_price: Maximum sale price
            stock: Stock array [{"warehouse_id": 1, "value": 25}]
            handling_time: Handling time array [{"warehouse_id": 1, "value": 1}]
            vat_id: VAT rate ID
            status: Offer status (0=inactive, 1=active, 2=end of life)

        Returns:
            Dictionary containing the API response

        Example:
            await client.update_product_offer(
                product_id=243409,
                sale_price=179.99,
                status=1,
                vat_id=1,
                stock=[{"warehouse_id": 1, "value": 25}],
                handling_time=[{"warehouse_id": 1, "value": 1}]
            )
        """
        # Build payload (array format for product_offer/save)
        payload_item = {"id": product_id}

        # Only include fields that are provided
        if sale_price is not None:
            payload_item["sale_price"] = round(float(sale_price), 4)
        if recommended_price is not None:
            payload_item["recommended_price"] = round(float(recommended_price), 4)
        if min_sale_price is not None:
            payload_item["min_sale_price"] = round(float(min_sale_price), 4)
        if max_sale_price is not None:
            payload_item["max_sale_price"] = round(float(max_sale_price), 4)
        if stock is not None:
            payload_item["stock"] = stock
        if handling_time is not None:
            payload_item["handling_time"] = handling_time
        if vat_id is not None:
            payload_item["vat_id"] = int(vat_id)
        if status is not None:
            payload_item["status"] = int(status)

        # Wrap in array (required by product_offer/save)
        payload = [payload_item]

        logger.debug(f"Sending to product_offer/save endpoint: {payload}")
        return await self._request("POST", "product_offer/save", json=payload)

    async def find_products_by_eans(self, eans: list[str]) -> dict[str, Any]:
        """Search products by EAN codes (v4.4.9).

        New API endpoint to simplify and speed up offer association process.
        Search directly by EAN codes to check if products already exist on eMAG.

        Args:
            eans: List of EAN codes to search (max 100 per request)

        Returns:
            Dictionary containing matched products with:
            - eans: European Article Number
            - part_number_key: eMAG part_number_key
            - product_name: Product name
            - brand_name: Brand name
            - category_name: Category name
            - doc_category_id: Category ID
            - site_url: eMAG product URL
            - allow_to_add_offer: Whether seller can add offer
            - vendor_has_offer: Whether seller already has offer
            - hotness: Product performance indicator
            - product_image: Main image URL

        Rate Limits:
            - 5 requests/second
            - 200 requests/minute
            - 5,000 requests/day

        Example:
            result = await client.find_products_by_eans(
                ["7086812930967", "5904862975146"]
            )
        """
        if len(eans) > 100:
            logger.warning(
                f"EAN list exceeds 100 items ({len(eans)}). Only first 100 will be processed."
            )
            eans = eans[:100]

        # Build query parameters
        params = {}
        for i, ean in enumerate(eans):
            params[f"eans[{i}]"] = ean

        return await self._request("GET", "documentation/find_by_eans", params=params)

    async def save_measurements(
        self,
        product_id: int,
        length: float,
        width: float,
        height: float,
        weight: float,
    ) -> dict[str, Any]:
        """Save volume measurements (dimensions and weight) for a product.

        Args:
            product_id: Seller internal product ID
            length: Product length in millimeters (mm)
            width: Product width in millimeters (mm)
            height: Product height in millimeters (mm)
            weight: Product weight in grams (g)

        Returns:
            Dictionary containing the API response

        Example:
            await client.save_measurements(
                product_id=243409,
                length=200.00,
                width=150.50,
                height=80.00,
                weight=450.75
            )
        """
        data = {
            "id": product_id,
            "length": round(length, 2),
            "width": round(width, 2),
            "height": round(height, 2),
            "weight": round(weight, 2),
        }

        return await self._request("POST", "measurements/save", json=data)

    async def get_categories(
        self,
        category_id: int | None = None,
        page: int = 1,
        items_per_page: int = 100,
        language: str = "ro",
    ) -> dict[str, Any]:
        """Get eMAG categories with characteristics and family types.

        Args:
            category_id: Specific category ID to get detailed info (optional)
            page: Page number for pagination
            items_per_page: Number of items per page (max 100)
            language: Response language (en, ro, hu, bg, pl, gr, de)

        Returns:
            Dictionary containing categories with:
            - id: Category ID
            - name: Category name
            - is_allowed: Whether seller can post in this category
            - parent_id: Parent category ID
            - is_ean_mandatory: Whether EAN is mandatory
            - is_warranty_mandatory: Whether warranty is mandatory
            - characteristics: List of characteristics (only for specific category)
            - family_types: List of family types (only for specific category)

        Example:
            # Get all categories
            categories = await client.get_categories()

            # Get specific category with characteristics
            category = await client.get_categories(category_id=506)
        """
        params = {
            "currentPage": page,
            "itemsPerPage": items_per_page,
        }

        if category_id:
            params["id"] = category_id

        endpoint = f"category/read?language={language}"
        return await self._request("POST", endpoint, json=params)

    async def get_vat_rates(self) -> dict[str, Any]:
        """Get available VAT rates from eMAG.

        Returns:
            Dictionary containing available VAT rates and their IDs
        """
        return await self._request("POST", "vat/read", json={})

    async def get_handling_times(self) -> dict[str, Any]:
        """Get available handling time values from eMAG.

        Returns:
            Dictionary containing available handling_time values
        """
        return await self._request("POST", "handling_time/read", json={})

    # ========== Stock Management (PATCH Endpoint) ==========

    async def update_stock_only(
        self, product_id: int, warehouse_id: int, stock_value: int
    ) -> dict[str, Any]:
        """Update ONLY stock using PATCH endpoint (fastest method).

        This is the fastest way to sync inventory without modifying other offer details.

        Args:
            product_id: Seller internal product ID
            warehouse_id: Warehouse ID (usually 1)
            stock_value: New stock quantity

        Returns:
            Dictionary containing the API response

        Example:
            await client.update_stock_only(
                product_id=243409,
                warehouse_id=1,
                stock_value=50
            )
        """
        endpoint = f"offer_stock/{product_id}"
        data = {"stock": [{"warehouse_id": warehouse_id, "value": stock_value}]}

        # Use PATCH method for stock-only updates
        return await self._request("PATCH", endpoint, json=data)

    # ========== Order Management ==========

    async def get_order_by_id(self, order_id: int) -> dict[str, Any]:
        """Get detailed information about a specific order.

        Args:
            order_id: eMAG order ID

        Returns:
            Dictionary containing complete order details
        """
        data = {"id": order_id}
        return await self._request("POST", "order/read", json=data)

    async def acknowledge_order(self, order_id: int) -> dict[str, Any]:
        """Acknowledge order (moves from status 1 'new' to status 2 'in progress').

        Critical: Must be done to stop notifications!
        Only available for 3P (third-party) orders.

        Args:
            order_id: eMAG order ID

        Returns:
            Dictionary containing the API response

        Example:
            await client.acknowledge_order(939393)
        """
        endpoint = f"order/acknowledge/{order_id}"
        return await self._request("POST", endpoint, json={})

    async def save_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing order (status, products, etc.).

        Important: Send ALL fields you initially read for that order.

        Args:
            order_data: Complete order data including all fields

        Returns:
            Dictionary containing the API response
        """
        return await self._request("POST", "order/save", json=order_data)

    async def attach_invoice(
        self,
        order_id: int,
        invoice_url: str,
        invoice_name: str | None = None,
        force_download: bool = False,
    ) -> dict[str, Any]:
        """Attach invoice PDF to finalized order.

        Required when moving order to status 4 (finalized).

        Args:
            order_id: eMAG order ID
            invoice_url: Public URL of invoice PDF
            invoice_name: Display name for customer (optional)
            force_download: Force redownload if URL unchanged

        Returns:
            Dictionary containing the API response
        """
        data = {
            "order_id": order_id,
            "name": invoice_name or f"Invoice #{order_id}",
            "url": invoice_url,
            "type": 1,  # Invoice type
            "force_download": 1 if force_download else 0,
        }

        return await self._request("POST", "order/attachments/save", json=data)

    async def attach_warranty(
        self,
        order_product_id: int,
        warranty_url: str,
        warranty_name: str | None = None,
    ) -> dict[str, Any]:
        """Attach warranty certificate to product line in order.

        Args:
            order_product_id: Product line ID from order (products.id)
            warranty_url: Public URL of warranty PDF
            warranty_name: Display name (optional)

        Returns:
            Dictionary containing the API response
        """
        data = {
            "order_product_id": order_product_id,
            "name": warranty_name or "Warranty Certificate",
            "url": warranty_url,
            "type": 3,  # Warranty type
        }

        return await self._request("POST", "order/attachments/save", json=data)

    # ========== AWB (Air Waybill) Management ==========

    async def create_awb(
        self,
        order_id: int | None = None,
        rma_id: int | None = None,
        sender: dict[str, Any] | None = None,
        receiver: dict[str, Any] | None = None,
        envelope_number: int = 0,
        parcel_number: int = 1,
        cod: float = 0.0,
        is_oversize: int = 0,
        date: str | None = None,
        courier_account_id: int | None = None,
        packages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate AWB for order shipment or return (UPDATED in v4.4.9).

        Automatically moves order to status 4 (finalized).

        NEW in v4.4.9: Support for address_id in sender/receiver objects.
        When address_id is provided, the saved address is used regardless of other fields.

        Args:
            order_id: eMAG order ID (for orders)
            rma_id: RMA ID (for returns)
            sender: Sender details dict with optional 'address_id' (NEW v4.4.9)
                - address_id: Saved address ID (0-21 chars) - NEW v4.4.9
                - name: Sender name (required)
                - contact: Contact person (required)
                - phone1: Primary phone (required)
                - phone2: Secondary phone (optional)
                - locality_id: Locality ID (required if no address_id)
                - street: Street address (required if no address_id)
                - zipcode: Postal code (optional)
            receiver: Receiver details dict with optional 'address_id' (NEW v4.4.9)
                Same structure as sender
            envelope_number: Number of envelopes
            parcel_number: Number of parcels
            cod: Cash on delivery amount
            is_oversize: Whether package is oversize (0 or 1)
            date: Pickup date for returns (YYYY-MM-DD)
            courier_account_id: Courier service ID (legacy parameter)
            packages: List of package details (legacy parameter)

        Returns:
            Dictionary containing AWB number and tracking details

        Example (Order with saved address):
            await client.create_awb(
                order_id=123456,
                sender={'address_id': '12345', 'name': 'My Company',
                        'contact': 'John Doe', 'phone1': '0721234567'},
                receiver={'name': 'Customer', 'contact': 'Customer',
                         'phone1': '0729876543', 'locality_id': 8801,
                         'street': 'Str. Customer, Nr. 5', 'legal_entity': 0},
                envelope_number=0,
                parcel_number=1,
                cod=199.99,
                is_oversize=0
            )

        Example (Return with saved address):
            await client.create_awb(
                rma_id=789012,
                sender={'name': 'Customer', 'contact': 'Customer',
                       'phone1': '0729876543', 'locality_id': 8801,
                       'street': 'Str. Customer, Nr. 5'},
                receiver={'address_id': '12345', 'name': 'My Company',
                         'contact': 'John Doe', 'phone1': '0721234567'},
                envelope_number=0,
                parcel_number=1,
                cod=0,
                is_oversize=0,
                date='2025-10-02'
            )
        """
        data = {}

        # Order or RMA
        if order_id:
            data["order_id"] = order_id
        if rma_id:
            data["rma_id"] = rma_id

        # Sender and receiver
        if sender:
            data["sender"] = sender
        if receiver:
            data["receiver"] = receiver

        # Package details
        data["envelope_number"] = envelope_number
        data["parcel_number"] = parcel_number
        data["cod"] = cod
        data["is_oversize"] = is_oversize

        # Optional fields
        if date:
            data["date"] = date

        # Legacy support
        if courier_account_id:
            data["courier_account_id"] = courier_account_id
        if packages:
            data["packages"] = packages

        return await self._request("POST", "awb/save", json=data)

    async def get_awb(self, awb_number: str) -> dict[str, Any]:
        """Get AWB details by AWB number.

        Args:
            awb_number: AWB tracking number

        Returns:
            Dictionary containing AWB details
        """
        data = {"awb_number": awb_number}
        return await self._request("POST", "awb/read", json=data)

    async def get_courier_accounts(self) -> dict[str, Any]:
        """Get available courier accounts for seller.

        Returns:
            Dictionary containing list of courier accounts
        """
        return await self._request("POST", "courier_accounts/read", json={})

    # ========== Campaign Management ==========

    async def propose_to_campaign(
        self,
        product_id: int,
        campaign_id: int,
        sale_price: float,
        stock: int,
        max_qty_per_order: int | None = None,
        voucher_discount: int | None = None,
        post_campaign_sale_price: float | None = None,
        not_available_post_campaign: bool = False,
        date_intervals: list | None = None,
    ) -> dict[str, Any]:
        """Propose product to eMAG campaign.

        Args:
            product_id: Seller internal product ID
            campaign_id: eMAG campaign ID
            sale_price: Campaign price (no VAT)
            stock: Reserved stock for campaign
            max_qty_per_order: Max quantity per customer (required for Stock-in-site)
            voucher_discount: Discount percentage 10-100
            post_campaign_sale_price: Price after campaign ends
            not_available_post_campaign: Deactivate offer after campaign
            date_intervals: Required for MultiDeals campaigns

        Returns:
            Dictionary containing the API response
        """
        data = {
            "id": product_id,
            "sale_price": sale_price,
            "stock": stock,
            "campaign_id": campaign_id,
        }

        if max_qty_per_order is not None:
            data["max_qty_per_order"] = max_qty_per_order
        if voucher_discount is not None:
            data["voucher_discount"] = voucher_discount
        if post_campaign_sale_price is not None:
            data["post_campaign_sale_price"] = post_campaign_sale_price
        if not_available_post_campaign:
            data["not_available_post_campaign"] = 1
        if date_intervals is not None:
            data["date_intervals"] = date_intervals

        return await self._request("POST", "campaign_proposals/save", json=data)

    async def check_smart_deals_eligibility(self, product_id: int) -> dict[str, Any]:
        """Check if product qualifies for Smart Deals badge.

        Returns target price needed for eligibility.

        Args:
            product_id: Seller internal product ID

        Returns:
            Dictionary containing:
            - productId: Product identifier
            - currentPrice: Current sale price
            - targetPrice: Price needed for Smart Deals
            - discount: Required discount percentage
            - isEligible: Whether currently qualifies
        """
        params = {"productId": product_id}
        return await self._request("GET", "smart-deals-price-check", params=params)

    # ========== Commission Calculator ==========

    async def get_commission_estimate(self, product_id: int) -> dict[str, Any]:
        """Get estimated commission for product.

        Args:
            product_id: Seller internal product ID (ext_id)

        Returns:
            Dictionary containing:
            - value: Estimated commission amount
            - id: Product ID
            - created: Timestamp when estimate was generated
            - end_date: Expiration timestamp (nullable)
        """
        endpoint = f"api/v1/commission/estimate/{product_id}"
        return await self._request("GET", endpoint)

    async def search_product_by_ean(self, ean: str) -> dict[str, Any]:
        """Search for product ext_ids by EAN code.

        Useful for finding product ID before getting commission.

        Args:
            ean: EAN barcode

        Returns:
            Dictionary containing list of ext_ids for products with that EAN
        """
        params = {"ean": ean}
        return await self._request("GET", "api/v1/product/search-by-ean", params=params)

    # ========== RMA (Returns) Management ==========

    async def get_rma_requests(
        self,
        page: int = 1,
        items_per_page: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get RMA (return) requests.

        Args:
            page: Page number
            items_per_page: Items per page
            filters: Optional filters for RMA requests

        Returns:
            Dictionary containing RMA requests
        """
        data = {"currentPage": page, "itemsPerPage": items_per_page}

        if filters:
            data.update(filters)

        return await self._request("POST", "rma/read", json=data)

    async def save_rma(self, rma_data: dict[str, Any]) -> dict[str, Any]:
        """Update RMA request.

        Args:
            rma_data: RMA request data

        Returns:
            Dictionary containing the API response
        """
        return await self._request("POST", "rma/save", json=rma_data)

    # ========== Addresses Management - NEW in v4.4.9 ==========

    async def get_addresses(
        self, page: int = 1, items_per_page: int = 100
    ) -> dict[str, Any]:
        """Get saved addresses for pickup and return locations (NEW in v4.4.9).

        This endpoint retrieves your saved addresses that can be used when issuing AWBs.

        Args:
            page: Page number for pagination
            items_per_page: Number of items per page (max 100)

        Returns:
            Dictionary containing addresses with:
            - address_id: Unique identifier (0-21 chars)
            - country_id: Country ID
            - country_code: Country Alpha-2 code (e.g., RO, BG)
            - address_type_id: Type (1=Return, 2=Pickup, 3=Invoice HQ, 4=Delivery estimates)
            - locality_id: Locality ID
            - suburb: County
            - city: City name
            - address: Street, number, etc.
            - zipcode: Postal code
            - quarter: Quarter/district
            - floor: Floor number
            - is_default: Whether this is the default address

        Example:
            addresses = await client.get_addresses()
            pickup_addresses = [a for a in addresses['results'] if a['address_type_id'] == 2]
        """
        data = {"currentPage": page, "itemsPerPage": items_per_page}

        return await self._request("POST", "addresses/read", json=data)

    # ========== Localities (Cities/Regions) ==========

    async def get_localities(
        self,
        page: int = 1,
        items_per_page: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get localities (cities/regions) for address validation.

        Args:
            page: Page number
            items_per_page: Items per page
            filters: Optional filters

        Returns:
            Dictionary containing localities
        """
        data = {"currentPage": page, "itemsPerPage": items_per_page}

        if filters:
            data.update(filters)

        return await self._request("POST", "locality/read", json=data)


# Example usage:
# async def example():
#     async with EmagApiClient('username', 'password') as client:
#         try:
#             # Get products
#             products = await client.get_products()
#             logger.info(f"Found {len(products.get('results', []))} products")
#
#             # Update stock quickly
#             await client.update_stock_only(243409, 1, 50)
#
#             # Get new orders
#             orders = await client.get_orders(status="new")
#
#             # Acknowledge order
#             await client.acknowledge_order(939393)
#         except EmagApiError as e:
#             logger.error(f"Error: {e}")
