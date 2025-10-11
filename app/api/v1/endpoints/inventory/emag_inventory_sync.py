"""
eMag FBE Inventory Synchronization API

Endpoint for synchronizing eMag FBE stock to inventory_items table.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.inventory import InventoryItem, Warehouse
from app.models.product import Product

logger = get_logger(__name__)
router = APIRouter(prefix="/emag-inventory-sync", tags=["inventory", "emag"])


async def _sync_emag_to_inventory(
    db: AsyncSession, account_type: str = "fbe"
) -> dict[str, Any]:
    """
    Synchronize eMag stock to inventory_items.

    Args:
        db: Database session
        account_type: eMag account type (default: fbe)

    Returns:
        Sync statistics
    """
    from app.models.emag_models import EmagProductV2

    stats = {
        "warehouse_created": False,
        "products_synced": 0,
        "created": 0,
        "updated": 0,
        "errors": 0,
        "low_stock_count": 0,
        "skipped_no_product": 0,
    }

    try:
        # Step 1: Get or create eMag warehouse based on account type
        warehouse_code = "EMAG-FBE" if account_type.lower() == "fbe" else "EMAG-MAIN"
        warehouse_name = (
            "eMag FBE (Fulfillment by eMag)"
            if account_type.lower() == "fbe"
            else "eMag MAIN (Seller Fulfilled)"
        )

        result = await db.execute(
            select(Warehouse).where(Warehouse.code == warehouse_code)
        )
        warehouse = result.scalar_one_or_none()

        if not warehouse:
            warehouse = Warehouse(
                name=warehouse_name,
                code=warehouse_code,
                address="eMag Fulfillment Center"
                if account_type.lower() == "fbe"
                else "Main Warehouse",
                city="București",
                country="Romania",
                is_active=True,
            )
            db.add(warehouse)
            await db.flush()
            stats["warehouse_created"] = True
            logger.info(f"Created {warehouse_code} warehouse (ID: {warehouse.id})")

        # Step 2: Get eMag stock data from emag_products_v2
        query = (
            select(
                EmagProductV2.id,
                EmagProductV2.sku,
                EmagProductV2.name,
                EmagProductV2.stock_quantity,
                EmagProductV2.price,
                EmagProductV2.currency,
                EmagProductV2.is_active,
                EmagProductV2.status,
                Product.id.label("product_id"),
            )
            .select_from(EmagProductV2)
            .outerjoin(Product, EmagProductV2.sku == Product.sku)
            .where(
                and_(
                    EmagProductV2.account_type == account_type.lower(),
                    EmagProductV2.is_active.is_(True),
                )
            )
        )

        result = await db.execute(query)
        emag_stock_data = result.all()

        if not emag_stock_data:
            logger.warning(f"No eMag {account_type} products found for sync")
            return stats

        logger.info(
            f"Found {len(emag_stock_data)} eMag {account_type} products to sync"
        )

        # Step 3: Sync each product
        for row in emag_stock_data:
            try:
                # Skip if no matching product in products table
                if not row.product_id:
                    logger.debug(
                        f"Skipping {row.sku} - no matching product in products table"
                    )
                    stats["skipped_no_product"] += 1
                    continue

                stock = row.stock_quantity or 0

                # Calculate stock levels
                if stock == 0:
                    minimum_stock = 5
                    reorder_point = 10
                    maximum_stock = 100
                elif stock < 10:
                    minimum_stock = 10
                    reorder_point = 20
                    maximum_stock = 100
                elif stock < 50:
                    minimum_stock = max(int(stock * 0.2), 10)
                    reorder_point = max(int(stock * 0.3), 20)
                    maximum_stock = 100
                else:
                    minimum_stock = max(int(stock * 0.2), 10)
                    reorder_point = max(int(stock * 0.3), 20)
                    maximum_stock = stock * 2

                # Estimate unit cost (70% of price)
                unit_cost = row.price * 0.7 if row.price else 0

                # Upsert inventory item
                stmt = (
                    insert(InventoryItem)
                    .values(
                        product_id=row.product_id,
                        warehouse_id=warehouse.id,
                        quantity=stock,
                        reserved_quantity=0,
                        available_quantity=stock,
                        minimum_stock=minimum_stock,
                        reorder_point=reorder_point,
                        maximum_stock=maximum_stock,
                        unit_cost=unit_cost,
                        location=f"eMag {account_type.upper()}",
                        is_active=row.is_active,
                    )
                    .on_conflict_do_update(
                        constraint="uq_inventory_items_product_warehouse",
                        set_={
                            "quantity": stock,
                            "available_quantity": stock,
                            "minimum_stock": minimum_stock,
                            "reorder_point": reorder_point,
                            "maximum_stock": maximum_stock,
                            "unit_cost": unit_cost,
                            "location": f"eMag {account_type.upper()}",
                            "is_active": row.is_active,
                        },
                    )
                )

                await db.execute(stmt)
                stats["products_synced"] += 1

            except Exception as e:
                logger.error(f"Error syncing product {row.sku}: {e}", exc_info=True)
                stats["errors"] += 1

        # Commit changes
        await db.commit()

        # Step 4: Get low stock count
        result = await db.execute(
            select(func.count(InventoryItem.id)).where(
                and_(
                    InventoryItem.warehouse_id == warehouse.id,
                    InventoryItem.available_quantity <= InventoryItem.reorder_point,
                )
            )
        )
        stats["low_stock_count"] = result.scalar()

        logger.info(
            f"eMag inventory sync completed: {stats['products_synced']} synced, "
            f"{stats['low_stock_count']} low stock, {stats['errors']} errors"
        )

        return stats

    except Exception as e:
        logger.error(f"eMag inventory sync failed: {e}", exc_info=True)
        await db.rollback()
        raise


@router.post("/sync")
async def sync_emag_inventory(
    background_tasks: BackgroundTasks,
    account_type: str = Query("fbe", description="eMag account type (fbe or main)"),
    async_mode: bool = Query(False, description="Run in background"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Synchronize eMag FBE stock to inventory_items.

    This endpoint:
    1. Creates eMag FBE warehouse if not exists
    2. Fetches stock from emag_product_offers
    3. Syncs to inventory_items table
    4. Returns sync statistics

    Args:
        account_type: eMag account type (default: fbe)
        async_mode: Run in background (default: False)

    Returns:
        Sync status and statistics
    """
    try:
        if async_mode:
            # Run in background
            async def _background_sync():
                async with db.begin():
                    await _sync_emag_to_inventory(db, account_type)

            background_tasks.add_task(_background_sync)

            return {
                "success": True,
                "message": "eMag inventory synchronization started in background",
                "account_type": account_type,
                "async_mode": True,
            }
        else:
            # Run synchronously
            stats = await _sync_emag_to_inventory(db, account_type)

            return {
                "success": True,
                "message": "eMag inventory synchronization completed",
                "account_type": account_type,
                "async_mode": False,
                "stats": stats,
            }

    except Exception as e:
        logger.error(f"Error in eMag inventory sync endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synchronize eMag inventory: {str(e)}",
        )


@router.get("/status")
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get current eMag inventory sync status.

    Returns:
        Current inventory statistics for eMag FBE warehouse
    """
    try:
        # Get warehouse
        result = await db.execute(select(Warehouse).where(Warehouse.code == "EMAG-FBE"))
        warehouse = result.scalar_one_or_none()

        if not warehouse:
            return {
                "warehouse_exists": False,
                "message": "eMag FBE warehouse not found. Run sync first.",
            }

        # Get statistics
        result = await db.execute(
            select(
                func.count(InventoryItem.id).label("total_items"),
                func.sum(InventoryItem.quantity).label("total_quantity"),
                func.count(InventoryItem.id)
                .filter(InventoryItem.available_quantity == 0)
                .label("out_of_stock"),
                func.count(InventoryItem.id)
                .filter(
                    and_(
                        InventoryItem.available_quantity > 0,
                        InventoryItem.available_quantity <= InventoryItem.minimum_stock,
                    )
                )
                .label("critical"),
                func.count(InventoryItem.id)
                .filter(
                    and_(
                        InventoryItem.available_quantity > InventoryItem.minimum_stock,
                        InventoryItem.available_quantity <= InventoryItem.reorder_point,
                    )
                )
                .label("low_stock"),
            ).where(InventoryItem.warehouse_id == warehouse.id)
        )
        row = result.one()

        return {
            "warehouse_exists": True,
            "warehouse": {
                "id": warehouse.id,
                "name": warehouse.name,
                "code": warehouse.code,
            },
            "statistics": {
                "total_items": row.total_items or 0,
                "total_quantity": int(row.total_quantity or 0),
                "out_of_stock": row.out_of_stock or 0,
                "critical": row.critical or 0,
                "low_stock": row.low_stock or 0,
                "needs_reorder": (row.out_of_stock or 0)
                + (row.critical or 0)
                + (row.low_stock or 0),
            },
        }

    except Exception as e:
        logger.error(f"Error getting sync status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}",
        )
