"""Order repository for database operations."""

from typing import Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderLine  # Importing Order and OrderLine models
from app.repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository):
    """Repository for order-related database operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Order, db_session)

    async def get_by_emag_id(self, emag_id: str) -> Order | None:
        """Get an order by eMAG ID."""
        result = await self.db.execute(select(Order).where(Order.emag_id == emag_id))
        return result.scalars().first()

    async def get_with_items(self, order_id: int) -> Order | None:
        """Get an order with its items."""
        result = await self.db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        return result.scalars().first()

    async def get_by_status(self, status: str) -> list[Order]:
        """Get orders by status."""
        result = await self.db.execute(
            select(Order)
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
        )
        return result.scalars().all()

    async def get_orders_by_customer(
        self, customer_id: int, limit: int = 100, offset: int = 0
    ) -> list[Order]:
        """Get orders by customer ID with pagination."""
        result = await self.db.execute(
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update_status(
        self, order_id: int, status: str, notes: str | None = None
    ) -> Order | None:
        """Update order status."""
        update_data = {"status": status}
        if notes:
            update_data["notes"] = notes

        await self.db.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(**update_data)
            .returning(Order)
        )
        await self.db.commit()
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalars().first()

    async def bulk_upsert_orders(
        self, orders: list[dict[str, Any]], update_fields: list[str] | None = None
    ) -> int:
        """Bulk upsert orders with their items.

        Args:
            orders: List of order dictionaries with nested items
            update_fields: List of fields to update on conflict

        Returns:
            int: Number of affected rows
        """
        if not orders:
            return 0

        # Default fields to update if not specified
        if update_fields is None:
            update_fields = [
                "status",
                "total_amount",
                "shipping_cost",
                "notes",
                "shipping_address",
                "billing_address",
                "updated_at",
            ]

        # Process orders and items
        order_data = []
        order_items_data = []

        for order in orders:
            # Extract items from order
            items = order.pop("items", [])
            order_data.append(order)

            # Add order_id to each item
            for item in items:
                item["order_id"] = order.get("emag_id")
                order_items_data.append(item)

        # Update the orders
        update_dict = {field: getattr(Order, field) for field in update_fields}

        # Add current timestamp for updated_at if it's in update_fields
        if "updated_at" in update_fields:
            from sqlalchemy import func

            update_dict["updated_at"] = func.now()

        # Execute the bulk upsert for orders
        stmt = (
            insert(Order)
            .values(order_data)
            .on_conflict_do_update(index_elements=["emag_id"], set_=update_dict)
            .returning(Order.id, Order.emag_id)
        )

        await self.db.execute(stmt)
        await self.db.commit()

        # Now handle order items if there are any
        if order_items_data:
            # First, delete existing items for these orders
            order_emag_ids = [order.get("emag_id") for order in orders]
            await self.db.execute(
                delete(OrderLine).where(OrderLine.order_id.in_(order_emag_ids))
            )

            # Then insert the new items
            if order_items_data:
                await self.db.execute(insert(OrderLine), order_items_data)
                await self.db.commit()

        return len(orders)


# Factory function to get an order repository instance
def get_order_repository(db_session: AsyncSession | None = None):
    """Get an order repository instance.

    Args:
        db_session: Optional database session. If not provided, a new one will be created.

    Returns:
        An instance of OrderRepository
    """
    from app.db.session import AsyncSessionLocal  # Import the async session factory

    if db_session is None:
        # Create a new async session
        db_session = AsyncSessionLocal()

    return OrderRepository(db_session)
