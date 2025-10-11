"""
eMAG Order Management Service for MagFlow ERP.

This service handles complete order lifecycle management including:
- Order synchronization from eMAG
- Order acknowledgment
- Status updates
- Invoice and warranty attachment
- AWB generation
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.emag_config import get_emag_config
from app.core.database import async_session_factory
from app.core.exceptions import ServiceError
from app.core.logging import get_logger
from app.models.emag_models import EmagOrder
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError

logger = get_logger(__name__)


# Order status constants
ORDER_STATUS = {
    0: "canceled",
    1: "new",
    2: "in_progress",
    3: "prepared",
    4: "finalized",
    5: "returned",
}

# Payment method constants
PAYMENT_METHODS = {
    1: "COD",  # Cash on Delivery
    2: "bank_transfer",
    3: "online_card",
}


class EmagOrderService:
    """Complete order management service for eMAG integration."""

    def __init__(
        self, account_type: str = "main", db_session: AsyncSession | None = None
    ):
        """Initialize the eMAG order service.

        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
            db_session: Optional database session
        """
        self.account_type = account_type.lower()
        self.config = get_emag_config(self.account_type)
        self.client: EmagApiClient | None = None
        self.db_session = db_session
        self._metrics = {
            "orders_synced": 0,
            "orders_acknowledged": 0,
            "orders_finalized": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

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

        logger.info("Initialized eMAG order service for %s account", self.account_type)

    async def close(self):
        """Close the eMAG API client."""
        if self.client:
            await self.client.close()
            self.client = None

    async def sync_new_orders(
        self,
        status_filter: int | None = 1,  # 1 = new orders
        max_pages: int = 10,
        days_back: int | None = None,
    ) -> dict[str, Any]:
        """Sync new orders from eMAG.

        Order Statuses:
        - 0: Canceled
        - 1: New (awaiting acknowledgment)
        - 2: In Progress
        - 3: Prepared
        - 4: Finalized
        - 5: Returned

        Args:
            status_filter: Order status to filter (default: 1 for new orders)
            max_pages: Maximum pages to fetch
            days_back: Number of days to look back for orders (optional)

        Returns:
            Dictionary with sync results
        """
        logger.info(
            "Syncing orders from %s account with status=%s, days_back=%s",
            self.account_type,
            status_filter,
            days_back,
        )

        orders = []
        page = 1
        created_count = 0
        updated_count = 0

        while page <= max_pages:
            try:
                # Build filters
                filters = {}
                if status_filter is not None:
                    filters["status"] = status_filter

                # Note: eMAG API doesn't support date filtering directly
                # We'll filter after fetching if days_back is specified

                # Get orders page
                response = await self.client.get_orders(
                    page=page, items_per_page=100, filters=filters
                )

                if not response or "results" not in response:
                    logger.warning("No results in response for page %d", page)
                    break

                page_orders = response["results"]
                if not page_orders:
                    break

                orders.extend(page_orders)

                logger.info(
                    "Fetched page %d with %d orders from %s account (total so far: %d)",
                    page,
                    len(page_orders),
                    self.account_type,
                    len(orders),
                )

                # Check pagination
                pagination = response.get("pagination", {})
                total_pages = pagination.get("totalPages", 1)
                current_page = pagination.get("currentPage", page)

                logger.info(
                    "Pagination info: currentPage=%d, totalPages=%d, max_pages=%d, orders_in_page=%d",
                    current_page,
                    total_pages,
                    max_pages,
                    len(page_orders),
                )

                # Check if we've reached max_pages limit
                if page >= max_pages:
                    logger.info("Reached max_pages limit (%d)", max_pages)
                    break

                # Continue to next page if current page was full (100 items)
                # eMAG API doesn't return correct totalPages, so we rely on page size
                if len(page_orders) < 100:
                    logger.info(
                        "Last page detected: only %d orders (less than 100)",
                        len(page_orders),
                    )
                    break

                page += 1

                # Small delay between requests
                await asyncio.sleep(0.5)

            except EmagApiError as e:
                logger.error("API error on page %d: %s", page, str(e))
                self._metrics["errors"] += 1
                break

        # Filter by date if days_back is specified
        if days_back is not None:
            from datetime import datetime, timedelta

            cutoff_date = datetime.now() - timedelta(days=days_back)
            filtered_orders = []
            for order in orders:
                order_date_str = order.get("date")
                if order_date_str:
                    try:
                        order_date = datetime.strptime(
                            order_date_str, "%Y-%m-%d %H:%M:%S"
                        )
                        if order_date >= cutoff_date:
                            filtered_orders.append(order)
                    except ValueError:
                        # If date parsing fails, include the order
                        filtered_orders.append(order)
                else:
                    # If no date, include the order
                    filtered_orders.append(order)

            logger.info(
                "Filtered orders by date: %d -> %d (last %d days)",
                len(orders),
                len(filtered_orders),
                days_back,
            )
            orders = filtered_orders

        # Save orders to database
        for order_data in orders:
            try:
                is_new = await self._save_order_to_db(order_data)
                if is_new:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as save_error:
                logger.error(
                    "Error saving order %s: %s",
                    order_data.get("id"),
                    str(save_error),
                    exc_info=True,
                )
                self._metrics["errors"] += 1

        self._metrics["orders_synced"] = created_count + updated_count

        return {
            "account_type": self.account_type,
            "synced": created_count + updated_count,
            "created": created_count,
            "updated": updated_count,
            "orders_fetched": len(orders),
            "new_orders": len([o for o in orders if o.get("status") == 1]),
            "pages_processed": page - 1,
        }

    async def _save_order_to_db(self, order_data: dict[str, Any]) -> bool:
        """Save order to database.

        Returns:
            True if order was created (new), False if updated (existing)
        """
        emag_order_id = order_data.get("id")
        if not emag_order_id:
            return False

        # Use a new session for each order to avoid conflicts
        async with async_session_factory() as session:
            try:
                # Check if order exists
                stmt = select(EmagOrder).where(
                    and_(
                        EmagOrder.emag_order_id == emag_order_id,
                        EmagOrder.account_type == self.account_type,
                    )
                )
                result = await session.execute(stmt)
                existing_order = result.scalar_one_or_none()

                # Extract customer info
                customer = order_data.get("customer", {})

                # Prepare order data
                order_dict = {
                    "emag_order_id": emag_order_id,
                    "account_type": self.account_type,
                    "status": order_data.get("status"),
                    "status_name": ORDER_STATUS.get(
                        order_data.get("status"), "unknown"
                    ),
                    "customer_id": customer.get("id"),
                    "customer_name": customer.get("name"),
                    "customer_email": customer.get("email"),
                    "customer_phone": customer.get("phone_1"),
                    "order_date": self._parse_datetime(order_data.get("date")),
                    "total_amount": self._calculate_order_total(order_data),
                    "currency": order_data.get("currency", "RON"),
                    "payment_method": PAYMENT_METHODS.get(
                        order_data.get("payment_mode_id"), "unknown"
                    ),
                    "payment_status": order_data.get("payment_status"),
                    "delivery_mode": order_data.get("delivery_mode"),
                    "shipping_address": {
                        "contact": customer.get("shipping_contact"),
                        "phone": customer.get("shipping_phone"),
                        "country": customer.get("shipping_country"),
                        "city": customer.get("shipping_city"),
                        "street": customer.get("shipping_street"),
                        "postal_code": customer.get("shipping_postal_code"),
                    },
                    "billing_address": {
                        "name": customer.get("billing_name"),
                        "phone": customer.get("billing_phone"),
                        "country": customer.get("billing_country"),
                        "city": customer.get("billing_city"),
                        "street": customer.get("billing_street"),
                        "postal_code": customer.get("billing_postal_code"),
                    },
                    "products": order_data.get("products", []),
                    "sync_status": "synced",
                    "last_synced_at": datetime.now(UTC),
                }

                is_new = False
                if existing_order:
                    # Update existing order
                    for key, value in order_dict.items():
                        if key not in ["emag_order_id", "account_type"]:
                            setattr(existing_order, key, value)
                    existing_order.updated_at = datetime.now(UTC)
                    is_new = False
                else:
                    # Create new order
                    new_order = EmagOrder(**order_dict)
                    session.add(new_order)
                    is_new = True

                await session.commit()
                return is_new

            except Exception:
                await session.rollback()
                raise

    async def acknowledge_order(self, order_id: int) -> dict[str, Any]:
        """Acknowledge order (moves from status 1 to 2).

        Critical: Must be done to stop notifications!

        Args:
            order_id: eMAG order ID

        Returns:
            Dictionary with acknowledgment result
        """
        logger.info(
            "Acknowledging order %d from %s account", order_id, self.account_type
        )

        try:
            # Acknowledge via API
            await self.client.acknowledge_order(order_id)

            # Update local database
            async with async_session_factory() as session:
                stmt = select(EmagOrder).where(
                    and_(
                        EmagOrder.emag_order_id == order_id,
                        EmagOrder.account_type == self.account_type,
                    )
                )
                db_result = await session.execute(stmt)
                order = db_result.scalar_one_or_none()

                if order:
                    order.status = 2
                    order.status_name = "in_progress"
                    order.acknowledged_at = datetime.now(UTC)
                    order.updated_at = datetime.now(UTC)
                    await session.commit()

            self._metrics["orders_acknowledged"] += 1

            return {
                "success": True,
                "order_id": order_id,
                "new_status": 2,
                "message": "Order acknowledged successfully",
            }

        except EmagApiError as e:
            logger.error("Failed to acknowledge order %d: %s", order_id, str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to acknowledge order: {str(e)}")

    async def update_order_status(
        self, order_id: int, new_status: int, products: list[dict] | None = None
    ) -> dict[str, Any]:
        """Update order status and optionally modify products.

        Status transitions:
        - 1 → 2: Via acknowledge only
        - 2 → 3: Prepared
        - 2 → 4: Finalized
        - 3 → 4: Finalized
        - 4 → 5: Returned (within RT+5 days)

        Args:
            order_id: eMAG order ID
            new_status: New status code (0-5)
            products: Optional product list modifications

        Returns:
            Dictionary with update result
        """
        logger.info(
            "Updating order %d status to %d (%s)",
            order_id,
            new_status,
            ORDER_STATUS.get(new_status, "unknown"),
        )

        try:
            # Read current order from API
            response = await self.client.get_order_by_id(order_id)
            current_order = response.get("results", [{}])[0]

            if not current_order:
                raise ServiceError(f"Order {order_id} not found")

            # Update status
            current_order["status"] = new_status

            # Update products if provided
            if products:
                current_order["products"] = products

            # Save order via API
            await self.client.save_order(current_order)

            # Update local database
            async with async_session_factory() as session:
                stmt = select(EmagOrder).where(
                    and_(
                        EmagOrder.emag_order_id == order_id,
                        EmagOrder.account_type == self.account_type,
                    )
                )
                db_result = await session.execute(stmt)
                order = db_result.scalar_one_or_none()

                if order:
                    order.status = new_status
                    order.status_name = ORDER_STATUS.get(new_status, "unknown")
                    order.updated_at = datetime.now(UTC)

                    if new_status == 4:
                        order.finalized_at = datetime.now(UTC)

                    await session.commit()

            if new_status == 4:
                self._metrics["orders_finalized"] += 1

            return {
                "success": True,
                "order_id": order_id,
                "new_status": new_status,
                "status_name": ORDER_STATUS.get(new_status),
                "message": f"Order status updated to {ORDER_STATUS.get(new_status)}",
            }

        except EmagApiError as e:
            logger.error("Failed to update order %d: %s", order_id, str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to update order status: {str(e)}")

    async def attach_invoice(
        self, order_id: int, invoice_url: str, invoice_name: str | None = None
    ) -> dict[str, Any]:
        """Attach invoice PDF to finalized order.

        Required when moving to status 4.

        Args:
            order_id: eMAG order ID
            invoice_url: Public URL of invoice PDF
            invoice_name: Display name for customer

        Returns:
            Dictionary with attachment result
        """
        logger.info("Attaching invoice to order %d", order_id)

        try:
            await self.client.attach_invoice(
                order_id=order_id, invoice_url=invoice_url, invoice_name=invoice_name
            )

            # Update local database
            async with async_session_factory() as session:
                stmt = select(EmagOrder).where(
                    and_(
                        EmagOrder.emag_order_id == order_id,
                        EmagOrder.account_type == self.account_type,
                    )
                )
                db_result = await session.execute(stmt)
                order = db_result.scalar_one_or_none()

                if order:
                    order.invoice_url = invoice_url
                    order.invoice_uploaded_at = datetime.now(UTC)
                    order.updated_at = datetime.now(UTC)
                    await session.commit()

            return {
                "success": True,
                "order_id": order_id,
                "invoice_url": invoice_url,
                "message": "Invoice attached successfully",
            }

        except EmagApiError as e:
            logger.error("Failed to attach invoice to order %d: %s", order_id, str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to attach invoice: {str(e)}")

    def _calculate_order_total(self, order_data: dict[str, Any]) -> float:
        """Calculate total order amount from products."""
        total = 0.0
        products = order_data.get("products", [])

        for product in products:
            price = float(product.get("sale_price", 0))
            quantity = int(product.get("quantity", 0))
            total += price * quantity

        # Add shipping tax if present
        shipping_tax = order_data.get("shipping_tax", 0)
        if shipping_tax:
            total += float(shipping_tax)

        return round(total, 2)

    def _parse_datetime(self, date_str: str | None) -> datetime | None:
        """Parse datetime string from eMAG API."""
        if not date_str:
            return None

        try:
            # eMAG format: "YYYY-mm-dd HH:ii:ss"
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            logger.warning("Failed to parse datetime: %s", date_str)
            return None

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics."""
        return {"account_type": self.account_type, "metrics": self._metrics.copy()}
