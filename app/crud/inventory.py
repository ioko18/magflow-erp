"""CRUD operations for inventory management."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.inventory import (
    InventoryItem,
    StockMovement,
    StockReservation,
    StockTransfer,
    Warehouse,
)
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    StockMovementCreate,
    StockReservationCreate,
    StockReservationUpdate,
    StockTransferCreate,
    StockTransferUpdate,
    WarehouseCreate,
    WarehouseUpdate,
)


class CRUDWarehouse(CRUDBase[Warehouse, WarehouseCreate, WarehouseUpdate]):
    """CRUD operations for Warehouse model."""

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Warehouse]:
        """Get a warehouse by code."""
        result = await db.execute(select(Warehouse).where(Warehouse.code == code))
        return result.scalars().first()

    async def get_active(self, db: AsyncSession) -> List[Warehouse]:
        """Get all active warehouses."""
        result = await db.execute(select(Warehouse).where(Warehouse.is_active))
        return result.scalars().all()

    async def get_inventory_summary(
        self,
        db: AsyncSession,
        warehouse_id: int,
    ) -> Dict[str, Any]:
        """Get inventory summary for a warehouse."""
        # Get total items count
        total_items_result = await db.execute(
            select(func.count(InventoryItem.id))
            .where(InventoryItem.warehouse_id == warehouse_id)
            .where(InventoryItem.is_active),
        )
        total_items = total_items_result.scalar() or 0

        # Get total value
        total_value_result = await db.execute(
            select(func.sum(InventoryItem.quantity * InventoryItem.unit_cost))
            .where(InventoryItem.warehouse_id == warehouse_id)
            .where(InventoryItem.is_active),
        )
        total_value = total_value_result.scalar() or 0

        # Get low stock items
        low_stock_result = await db.execute(
            select(func.count(InventoryItem.id))
            .where(InventoryItem.warehouse_id == warehouse_id)
            .where(InventoryItem.is_active)
            .where(InventoryItem.available_quantity <= InventoryItem.minimum_stock),
        )
        low_stock_items = low_stock_result.scalar() or 0

        return {
            "warehouse_id": warehouse_id,
            "total_items": total_items,
            "total_value": total_value,
            "low_stock_items": low_stock_items,
        }


class CRUDInventoryItem(
    CRUDBase[InventoryItem, InventoryItemCreate, InventoryItemUpdate],
):
    """CRUD operations for InventoryItem model."""

    async def get_by_product_and_warehouse(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        warehouse_id: int,
    ) -> Optional[InventoryItem]:
        """Get inventory item by product and warehouse."""
        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.product_id == product_id)
            .where(InventoryItem.warehouse_id == warehouse_id)
            .where(InventoryItem.is_active),
        )
        return result.scalars().first()

    async def get_low_stock_items(
        self,
        db: AsyncSession,
        warehouse_id: Optional[int] = None,
    ) -> List[InventoryItem]:
        """Get inventory items that are low on stock."""
        query = (
            select(InventoryItem)
            .where(InventoryItem.is_active)
            .where(InventoryItem.available_quantity <= InventoryItem.minimum_stock)
        )

        if warehouse_id:
            query = query.where(InventoryItem.warehouse_id == warehouse_id)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_expiring_items(
        self,
        db: AsyncSession,
        days: int = 30,
        warehouse_id: Optional[int] = None,
    ) -> List[InventoryItem]:
        """Get inventory items expiring within specified days."""
        expiry_date = datetime.now() + timedelta(days=days)

        query = (
            select(InventoryItem)
            .where(InventoryItem.is_active)
            .where(InventoryItem.expiry_date <= expiry_date)
        )

        if warehouse_id:
            query = query.where(InventoryItem.warehouse_id == warehouse_id)

        result = await db.execute(query)
        return result.scalars().all()

    async def update_stock(
        self,
        db: AsyncSession,
        *,
        inventory_item: InventoryItem,
        new_quantity: int,
        movement_type: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        performed_by: Optional[int] = None,
    ) -> InventoryItem:
        """Update stock level and create stock movement record."""
        previous_quantity = inventory_item.quantity
        inventory_item.quantity = new_quantity
        inventory_item.available_quantity = (
            new_quantity - inventory_item.reserved_quantity
        )

        # Create stock movement
        stock_movement = StockMovement(
            inventory_item_id=inventory_item.id,
            warehouse_id=inventory_item.warehouse_id,
            movement_type=movement_type,
            quantity=abs(new_quantity - previous_quantity),
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
            unit_cost=inventory_item.unit_cost,
            total_value=inventory_item.unit_cost
            * abs(new_quantity - previous_quantity),
        )

        db.add(stock_movement)
        await db.commit()
        await db.refresh(inventory_item)

        return inventory_item

    async def reserve_stock(
        self,
        db: AsyncSession,
        *,
        inventory_item: InventoryItem,
        quantity: int,
        order_id: str,
        expires_at: Optional[datetime] = None,
    ) -> StockReservation:
        """Reserve stock for an order."""
        if inventory_item.available_quantity < quantity:
            raise ValueError("Insufficient available stock")

        # Create reservation
        reservation = StockReservation(
            inventory_item_id=inventory_item.id,
            order_id=order_id,
            quantity=quantity,
            reserved_at=datetime.now(),
            expires_at=expires_at or (datetime.now() + timedelta(hours=24)),
            is_active=True,
        )

        # Update inventory
        inventory_item.reserved_quantity += quantity
        inventory_item.available_quantity -= quantity

        db.add(reservation)
        await db.commit()
        await db.refresh(reservation)

        return reservation

    async def release_reservation(
        self,
        db: AsyncSession,
        *,
        reservation: StockReservation,
    ) -> None:
        """Release a stock reservation."""
        # Get inventory item
        inventory_item = await self.get(db, reservation.inventory_item_id)
        if not inventory_item:
            return

        # Update inventory
        inventory_item.reserved_quantity -= reservation.quantity
        inventory_item.available_quantity += reservation.quantity

        # Mark reservation as inactive
        reservation.is_active = False

        await db.commit()


class CRUDStockMovement(CRUDBase[StockMovement, StockMovementCreate, None]):
    """CRUD operations for StockMovement model."""

    async def get_by_inventory_item(
        self,
        db: AsyncSession,
        *,
        inventory_item_id: int,
        limit: int = 50,
    ) -> List[StockMovement]:
        """Get stock movements for an inventory item."""
        result = await db.execute(
            select(StockMovement)
            .where(StockMovement.inventory_item_id == inventory_item_id)
            .order_by(StockMovement.created_at.desc())
            .limit(limit),
        )
        return result.scalars().all()

    async def get_by_date_range(
        self,
        db: AsyncSession,
        *,
        start_date: datetime,
        end_date: datetime,
        warehouse_id: Optional[int] = None,
    ) -> List[StockMovement]:
        """Get stock movements within date range."""
        query = select(StockMovement).where(
            and_(
                StockMovement.created_at >= start_date,
                StockMovement.created_at <= end_date,
            ),
        )

        if warehouse_id:
            query = query.where(StockMovement.warehouse_id == warehouse_id)

        result = await db.execute(query.order_by(StockMovement.created_at.desc()))
        return result.scalars().all()


class CRUDStockReservation(
    CRUDBase[StockReservation, StockReservationCreate, StockReservationUpdate],
):
    """CRUD operations for StockReservation model."""

    async def get_expired_reservations(
        self,
        db: AsyncSession,
    ) -> List[StockReservation]:
        """Get expired reservations."""
        result = await db.execute(
            select(StockReservation)
            .where(StockReservation.is_active)
            .where(StockReservation.expires_at <= datetime.now()),
        )
        return result.scalars().all()

    async def get_by_order_id(
        self,
        db: AsyncSession,
        *,
        order_id: str,
    ) -> List[StockReservation]:
        """Get reservations for an order."""
        result = await db.execute(
            select(StockReservation)
            .where(StockReservation.order_id == order_id)
            .where(StockReservation.is_active),
        )
        return result.scalars().all()


class CRUDStockTransfer(
    CRUDBase[StockTransfer, StockTransferCreate, StockTransferUpdate],
):
    """CRUD operations for StockTransfer model."""

    async def get_pending_transfers(self, db: AsyncSession) -> List[StockTransfer]:
        """Get pending stock transfers."""
        result = await db.execute(
            select(StockTransfer)
            .where(StockTransfer.status == "pending")
            .order_by(StockTransfer.created_at.asc()),
        )
        return result.scalars().all()

    async def get_in_transit_transfers(self, db: AsyncSession) -> List[StockTransfer]:
        """Get in-transit stock transfers."""
        result = await db.execute(
            select(StockTransfer)
            .where(StockTransfer.status == "in_transit")
            .order_by(StockTransfer.created_at.asc()),
        )
        return result.scalars().all()

    async def approve_transfer(
        self,
        db: AsyncSession,
        *,
        transfer: StockTransfer,
        approved_by: int,
    ) -> StockTransfer:
        """Approve a stock transfer."""
        transfer.status = "in_transit"
        transfer.approved_by = approved_by

        await db.commit()
        await db.refresh(transfer)

        return transfer

    async def complete_transfer(
        self,
        db: AsyncSession,
        *,
        transfer: StockTransfer,
    ) -> StockTransfer:
        """Complete a stock transfer."""
        transfer.status = "completed"

        # Update inventory at destination warehouse
        # Get destination inventory item
        destination_item = await inventory_item.get_by_product_and_warehouse(
            db,
            product_id=transfer.inventory_item_id,
            warehouse_id=transfer.to_warehouse_id,
        )

        if destination_item:
            destination_item.quantity += transfer.quantity
            destination_item.available_quantity += transfer.quantity
        else:
            # Create new inventory item at destination
            destination_item = InventoryItem(
                product_id=transfer.inventory_item_id,
                warehouse_id=transfer.to_warehouse_id,
                quantity=transfer.quantity,
                available_quantity=transfer.quantity,
            )
            db.add(destination_item)

        # Update inventory at source warehouse
        source_item = await inventory_item.get_by_product_and_warehouse(
            db,
            product_id=transfer.inventory_item_id,
            warehouse_id=transfer.from_warehouse_id,
        )

        if source_item:
            source_item.quantity -= transfer.quantity
            source_item.available_quantity -= transfer.quantity

        await db.commit()
        await db.refresh(transfer)

        return transfer


# Create CRUD instances
warehouse = CRUDWarehouse(Warehouse)
inventory_item = CRUDInventoryItem(InventoryItem)
stock_movement = CRUDStockMovement(StockMovement)
stock_reservation = CRUDStockReservation(StockReservation)
stock_transfer = CRUDStockTransfer(StockTransfer)
