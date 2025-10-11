"""
eMAG AWB (Air Waybill) Management Service for MagFlow ERP.

This service handles complete AWB lifecycle management including:
- AWB generation for orders
- Courier account management
- Shipment tracking
- Automatic order status updates
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


class EmagAWBService:
    """Complete AWB management service for eMAG integration."""

    def __init__(
        self, account_type: str = "main", db_session: AsyncSession | None = None
    ):
        """Initialize the eMAG AWB service.

        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
            db_session: Optional database session
        """
        self.account_type = account_type.lower()
        self.config = get_emag_config(self.account_type)
        self.client: EmagApiClient | None = None
        self.db_session = db_session
        self._metrics = {
            "awbs_generated": 0,
            "awbs_failed": 0,
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

        logger.info("Initialized eMAG AWB service for %s account", self.account_type)

    async def close(self):
        """Close the eMAG API client."""
        if self.client:
            await self.client.close()
            self.client = None

    async def get_courier_accounts(self) -> dict[str, Any]:
        """Get available courier accounts for seller.

        Returns:
            Dictionary with courier accounts list
        """
        logger.info("Fetching courier accounts for %s account", self.account_type)

        try:
            result = await self.client.get_courier_accounts()

            couriers = result.get("results", [])

            return {
                "success": True,
                "account_type": self.account_type,
                "couriers": couriers,
                "count": len(couriers),
            }

        except EmagApiError as e:
            logger.error("Failed to fetch courier accounts: %s", str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to fetch courier accounts: {str(e)}")

    async def generate_awb(
        self,
        order_id: int,
        courier_account_id: int,
        packages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate AWB for order shipment.

        Automatically moves order to status 4 (finalized).

        Args:
            order_id: eMAG order ID
            courier_account_id: Courier service ID
            packages: Optional package details (auto-calculated if not provided)

        Returns:
            Dictionary with AWB details
        """
        logger.info(
            "Generating AWB for order %d with courier %d", order_id, courier_account_id
        )

        try:
            # Get order details if packages not provided
            if not packages:
                packages = await self._calculate_packages_from_order(order_id)

            # Generate AWB via API
            result = await self.client.create_awb(
                order_id=order_id,
                courier_account_id=courier_account_id,
                packages=packages,
            )

            # Extract AWB number from response
            awb_data = result.get("results", [{}])[0] if result.get("results") else {}
            awb_number = awb_data.get("awb_number") or awb_data.get("awb")

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
                    order.awb_number = awb_number
                    order.courier_name = awb_data.get("courier_name")
                    order.status = 4  # Finalized
                    order.status_name = "finalized"
                    order.finalized_at = datetime.now(UTC)
                    order.updated_at = datetime.now(UTC)
                    await session.commit()

            self._metrics["awbs_generated"] += 1
            self._metrics["orders_finalized"] += 1

            return {
                "success": True,
                "order_id": order_id,
                "awb_number": awb_number,
                "courier_account_id": courier_account_id,
                "status": "finalized",
                "message": f"AWB {awb_number} generated successfully",
            }

        except EmagApiError as e:
            logger.error("Failed to generate AWB for order %d: %s", order_id, str(e))
            self._metrics["awbs_failed"] += 1
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to generate AWB: {str(e)}")

    async def get_awb_details(self, awb_number: str) -> dict[str, Any]:
        """Get AWB tracking details.

        Args:
            awb_number: AWB tracking number

        Returns:
            Dictionary with AWB tracking information
        """
        logger.info("Fetching AWB details for %s", awb_number)

        try:
            result = await self.client.get_awb(awb_number)

            awb_data = result.get("results", [{}])[0] if result.get("results") else {}

            return {"success": True, "awb_number": awb_number, "data": awb_data}

        except EmagApiError as e:
            logger.error("Failed to fetch AWB details: %s", str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to fetch AWB details: {str(e)}")

    async def _calculate_packages_from_order(
        self, order_id: int
    ) -> list[dict[str, Any]]:
        """Calculate package details from order products.

        Args:
            order_id: eMAG order ID

        Returns:
            List of package dictionaries
        """
        # Get order from database
        async with async_session_factory() as session:
            stmt = select(EmagOrder).where(
                and_(
                    EmagOrder.emag_order_id == order_id,
                    EmagOrder.account_type == self.account_type,
                )
            )
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                raise ServiceError(f"Order {order_id} not found")

            # Calculate total weight and dimensions from products
            products = order.products or []
            total_weight = 0.0
            total_value = 0.0

            for product in products:
                quantity = int(product.get("quantity", 1))
                weight = float(product.get("weight", 0.5))  # Default 500g
                price = float(product.get("sale_price", 0))

                total_weight += weight * quantity
                total_value += price * quantity

            # Default package if no weight calculated
            if total_weight == 0:
                total_weight = 1.0  # 1kg default

            # Create package structure
            package = {
                "weight": round(total_weight, 2),
                "length": 30,  # Default dimensions in cm
                "width": 20,
                "height": 10,
                "value": round(total_value, 2),
                "currency": order.currency or "RON",
            }

            return [package]

    async def bulk_generate_awbs(
        self, orders: list[dict[str, Any]], courier_account_id: int
    ) -> dict[str, Any]:
        """Generate AWBs for multiple orders.

        Args:
            orders: List of order dictionaries with order_id and optional packages
            courier_account_id: Courier service ID

        Returns:
            Dictionary with bulk generation results
        """
        logger.info(
            "Bulk generating AWBs for %d orders with courier %d",
            len(orders),
            courier_account_id,
        )

        results = {"success": [], "failed": [], "total": len(orders)}

        for order_data in orders:
            order_id = order_data.get("order_id")
            packages = order_data.get("packages")

            try:
                result = await self.generate_awb(
                    order_id=order_id,
                    courier_account_id=courier_account_id,
                    packages=packages,
                )
                results["success"].append(result)

                # Small delay between requests
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(
                    "Failed to generate AWB for order %d: %s", order_id, str(e)
                )
                results["failed"].append({"order_id": order_id, "error": str(e)})

        return {
            "success": True,
            "results": results,
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
        }

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics."""
        return {"account_type": self.account_type, "metrics": self._metrics.copy()}
