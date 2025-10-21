"""Supplier management service for MagFlow ERP.

This service provides business logic for supplier operations including:
- Supplier CRUD operations
- Performance tracking and analytics
- Product matching and management
- Purchase order generation
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase import PurchaseOrder
from app.models.supplier import Supplier, SupplierPerformance, SupplierProduct

logger = logging.getLogger(__name__)


class SupplierService:
    """Service class for supplier management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_supplier(self, supplier_data: dict[str, Any]) -> Supplier:
        """Create a new supplier with validation."""

        # Check for duplicate supplier name in same country
        existing_query = select(Supplier).where(
            and_(
                Supplier.name == supplier_data["name"],
                Supplier.country == supplier_data.get("country", "China"),
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_supplier = existing_result.scalar_one_or_none()

        if existing_supplier:
            raise ValueError(
                f"Supplier '{supplier_data['name']}' already exists in "
                f"{supplier_data.get('country', 'China')}"
            )

        # Validate email format if provided
        if supplier_data.get("email") and "@" not in supplier_data["email"]:
            raise ValueError("Invalid email format")

        # Create supplier
        supplier = Supplier(**supplier_data)
        self.db.add(supplier)
        await self.db.flush()  # Get the ID

        logger.info(f"Created supplier: {supplier.name} (ID: {supplier.id})")
        return supplier

    async def update_supplier(
        self, supplier_id: int, update_data: dict[str, Any]
    ) -> Supplier:
        """Update supplier information with validation and audit logging."""

        query = select(Supplier).where(Supplier.id == supplier_id)
        result = await self.db.execute(query)
        supplier = result.scalar_one_or_none()

        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")

        # Track changes for audit log
        changes = {}

        # Validate currency if being updated
        if "currency" in update_data:
            valid_currencies = ["USD", "CNY", "EUR", "GBP", "JPY"]
            if update_data["currency"] not in valid_currencies:
                raise ValueError(
                    f"Invalid currency '{update_data['currency']}'. Must be one of: "
                    f"{', '.join(valid_currencies)}"
                )
            if supplier.currency != update_data["currency"]:
                changes["currency"] = {
                    "old": supplier.currency,
                    "new": update_data["currency"],
                }

        # Validate email format if provided
        if "email" in update_data and update_data["email"]:
            if "@" not in update_data["email"]:
                raise ValueError("Invalid email format")

        # Check for duplicate name if name is being updated
        if "name" in update_data:
            existing_query = select(Supplier).where(
                and_(
                    Supplier.name == update_data["name"],
                    Supplier.country == supplier.country,
                    Supplier.id != supplier_id,
                )
            )
            existing_result = await self.db.execute(existing_query)
            existing_supplier = existing_result.scalar_one_or_none()

            if existing_supplier:
                raise ValueError(
                    f"Supplier '{update_data['name']}' already exists in {supplier.country}"
                )

            if supplier.name != update_data["name"]:
                changes["name"] = {"old": supplier.name, "new": update_data["name"]}

        # Update fields
        for field, value in update_data.items():
            if hasattr(supplier, field):
                old_value = getattr(supplier, field)
                if old_value != value and field not in changes:
                    changes[field] = {"old": old_value, "new": value}
                setattr(supplier, field, value)

        logger.info(
            f"Updated supplier: {supplier.name} (ID: {supplier_id}), Changes: {changes}"
        )
        return supplier

    async def delete_supplier(self, supplier_id: int) -> None:
        """Soft delete a supplier."""

        query = select(Supplier).where(Supplier.id == supplier_id)
        result = await self.db.execute(query)
        supplier = result.scalar_one_or_none()

        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")

        supplier.is_active = False
        logger.info(f"Soft deleted supplier: {supplier.name} (ID: {supplier_id})")

    async def hard_delete_supplier(self, supplier_id: int) -> None:
        """Permanently delete a supplier (only if no orders exist)."""

        query = select(Supplier).where(Supplier.id == supplier_id)
        result = await self.db.execute(query)
        supplier = result.scalar_one_or_none()

        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")

        if supplier.total_orders > 0:
            raise ValueError(
                "Cannot permanently delete supplier with existing orders. Use soft delete instead."
            )

        # Get all raw product IDs for this supplier
        from app.models.supplier_matching import (
            ProductMatchingScore,
            SupplierRawProduct,
        )

        raw_products_query = select(SupplierRawProduct.id).where(
            SupplierRawProduct.supplier_id == supplier_id
        )
        raw_products_result = await self.db.execute(raw_products_query)
        raw_product_ids = [row[0] for row in raw_products_result.all()]

        # Delete all matching scores that reference these products
        if raw_product_ids:
            from sqlalchemy import or_

            matching_scores_query = select(ProductMatchingScore).where(
                or_(
                    ProductMatchingScore.product_a_id.in_(raw_product_ids),
                    ProductMatchingScore.product_b_id.in_(raw_product_ids),
                )
            )
            matching_scores_result = await self.db.execute(matching_scores_query)
            matching_scores = matching_scores_result.scalars().all()

            for score in matching_scores:
                await self.db.delete(score)

        # Delete all supplier raw products
        raw_products_delete_query = select(SupplierRawProduct).where(
            SupplierRawProduct.supplier_id == supplier_id
        )
        raw_products_delete_result = await self.db.execute(raw_products_delete_query)
        raw_products = raw_products_delete_result.scalars().all()

        for raw_product in raw_products:
            await self.db.delete(raw_product)

        # Delete all supplier products
        from app.models.supplier import SupplierProduct

        delete_products_query = select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id
        )
        products_result = await self.db.execute(delete_products_query)
        products = products_result.scalars().all()

        for product in products:
            await self.db.delete(product)

        # Now delete supplier (cascade will handle remaining related records)
        await self.db.delete(supplier)
        logger.info(
            "Permanently deleted supplier: %s (ID: %s) with %s matching scores, %s raw products "
            "and %s matched products",
            supplier.name,
            supplier_id,
            len(matching_scores) if raw_product_ids else 0,
            len(raw_products),
            len(products),
        )

    async def get_supplier_performance(
        self, supplier_id: int, period_days: int = 90
    ) -> dict[str, Any]:
        """Get comprehensive supplier performance metrics."""

        # Get supplier
        supplier_query = select(Supplier).where(Supplier.id == supplier_id)
        supplier_result = await self.db.execute(supplier_query)
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")

        # Calculate performance metrics
        cutoff_date = datetime.now(UTC) - timedelta(days=period_days)

        # Get recent purchase orders
        orders_query = select(PurchaseOrder).where(
            and_(
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.created_at >= cutoff_date,
            )
        )
        orders_result = await self.db.execute(orders_query)
        orders = orders_result.scalars().all()

        # Calculate metrics
        total_orders = len(orders)
        total_value = sum(order.total_value for order in orders)
        avg_order_value = total_value / total_orders if total_orders > 0 else 0

        # On-time delivery rate
        delivered_orders = [order for order in orders if order.status == "delivered"]
        on_time_orders = [
            order
            for order in delivered_orders
            if order.actual_delivery_date
            and order.expected_delivery_date
            and order.actual_delivery_date <= order.expected_delivery_date
        ]
        on_time_rate = (
            len(on_time_orders) / len(delivered_orders) if delivered_orders else 0
        )

        # Average lead time
        lead_times = []
        for order in delivered_orders:
            if order.actual_delivery_date and order.order_date:
                lead_time = (order.actual_delivery_date - order.order_date).days
                lead_times.append(lead_time)

        avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0

        # Get performance records
        perf_query = (
            select(SupplierPerformance)
            .where(
                and_(
                    SupplierPerformance.supplier_id == supplier_id,
                    SupplierPerformance.created_at >= cutoff_date,
                )
            )
            .order_by(desc(SupplierPerformance.created_at))
        )
        perf_result = await self.db.execute(perf_query)
        performance_records = perf_result.scalars().all()

        return {
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
                "rating": supplier.rating,
                "total_orders_all_time": supplier.total_orders,
            },
            "period_metrics": {
                "period_days": period_days,
                "total_orders": total_orders,
                "total_value": total_value,
                "avg_order_value": avg_order_value,
                "on_time_delivery_rate": on_time_rate,
                "avg_lead_time": avg_lead_time,
                "delivered_orders": len(delivered_orders),
            },
            "performance_records": [
                {
                    "metric_type": record.metric_type,
                    "metric_value": record.metric_value,
                    "created_at": record.created_at.isoformat()
                    if record.created_at
                    else None,
                    "notes": record.notes,
                }
                for record in performance_records
            ],
            "recent_orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "total_value": order.total_value,
                    "order_date": order.order_date.isoformat()
                    if order.order_date
                    else None,
                    "expected_delivery": order.expected_delivery_date.isoformat()
                    if order.expected_delivery_date
                    else None,
                    "actual_delivery": order.actual_delivery_date.isoformat()
                    if order.actual_delivery_date
                    else None,
                }
                for order in orders[:10]  # Last 10 orders
            ],
        }

    async def update_supplier_rating(
        self, supplier_id: int, order_id: int, rating_data: dict[str, Any]
    ):
        """Update supplier rating based on order completion."""

        # This would implement rating calculation logic
        # For now, just a placeholder
        logger.info(
            f"Updating rating for supplier {supplier_id} based on order {order_id}"
        )

        # Create performance record
        performance_record = SupplierPerformance(
            supplier_id=supplier_id,
            metric_type="order_rating",
            metric_value=rating_data.get("rating", 5.0),
            order_id=order_id,
            notes=rating_data.get("notes", ""),
        )
        self.db.add(performance_record)

    async def get_suppliers_by_country(self, country: str) -> list[Supplier]:
        """Get all suppliers from a specific country."""

        query = (
            select(Supplier)
            .where(and_(Supplier.country == country, Supplier.is_active))
            .order_by(Supplier.name)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_suppliers(self, search_term: str) -> list[Supplier]:
        """Search suppliers by name, contact person, or email."""

        search_filter = f"%{search_term}%"
        query = (
            select(Supplier)
            .where(
                and_(
                    Supplier.is_active,
                    or_(
                        Supplier.name.ilike(search_filter),
                        Supplier.contact_person.ilike(search_filter),
                        Supplier.email.ilike(search_filter),
                    ),
                )
            )
            .order_by(Supplier.name)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_supplier_products(self, supplier_id: int) -> list[SupplierProduct]:
        """Get all products mapped to a supplier."""

        query = (
            select(SupplierProduct)
            .where(
                and_(
                    SupplierProduct.supplier_id == supplier_id,
                    SupplierProduct.is_active,
                )
            )
            .options(selectinload(SupplierProduct.local_product))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_supplier_product_mapping(
        self,
        supplier_id: int,
        local_product_id: int,
        supplier_product_data: dict[str, Any],
    ) -> SupplierProduct:
        """Create a mapping between local product and supplier product."""

        # Check if mapping already exists
        existing_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.local_product_id == local_product_id,
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_mapping = existing_result.scalar_one_or_none()

        if existing_mapping:
            # Update existing mapping
            for field, value in supplier_product_data.items():
                if hasattr(existing_mapping, field):
                    setattr(existing_mapping, field, value)
            return existing_mapping

        # Create new mapping
        mapping = SupplierProduct(
            supplier_id=supplier_id,
            local_product_id=local_product_id,
            **supplier_product_data,
        )
        self.db.add(mapping)
        await self.db.flush()

        logger.info(
            f"Created supplier-product mapping: supplier={supplier_id}, product={local_product_id}"
        )
        return mapping

    async def update_supplier_product_price(
        self, supplier_product_id: int, new_price: float, currency: str = "CNY"
    ):
        """Update price for a supplier product and track history."""

        query = select(SupplierProduct).where(SupplierProduct.id == supplier_product_id)
        result = await self.db.execute(query)
        supplier_product = result.scalar_one_or_none()

        if not supplier_product:
            raise ValueError(
                f"Supplier product with ID {supplier_product_id} not found"
            )

        # Track price history
        if not supplier_product.price_history:
            supplier_product.price_history = []

        supplier_product.price_history.append(
            {
                "date": datetime.now(UTC).isoformat(),
                "price": supplier_product.supplier_price,
                "currency": supplier_product.supplier_currency,
            }
        )

        # Update current price
        supplier_product.supplier_price = new_price
        supplier_product.supplier_currency = currency
        supplier_product.last_price_update = datetime.now(UTC)

        logger.info(
            f"Updated price for supplier product {supplier_product_id}: {new_price} {currency}"
        )

    async def get_supplier_statistics(self) -> dict[str, Any]:
        """Get overall supplier statistics."""

        # Count suppliers by country
        country_query = (
            select(Supplier.country, func.count(Supplier.id))
            .where(Supplier.is_active)
            .group_by(Supplier.country)
        )
        country_result = await self.db.execute(country_query)
        suppliers_by_country = dict(country_result.all())

        # Get average ratings
        rating_query = select(func.avg(Supplier.rating)).where(Supplier.is_active)
        rating_result = await self.db.execute(rating_query)
        avg_rating = rating_result.scalar() or 0

        # Get total suppliers
        total_query = select(func.count(Supplier.id)).where(Supplier.is_active)
        total_result = await self.db.execute(total_query)
        total_suppliers = total_result.scalar()

        return {
            "total_suppliers": total_suppliers,
            "suppliers_by_country": suppliers_by_country,
            "average_rating": round(float(avg_rating), 2),
            "chinese_suppliers": suppliers_by_country.get("China", 0),
            "international_suppliers": total_suppliers
            - suppliers_by_country.get("China", 0),
        }
