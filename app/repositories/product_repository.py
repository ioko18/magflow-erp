"""Product repository for database operations."""

from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository):
    """Repository for product-related database operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Product, db_session)

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get a product by SKU."""
        result = await self.db.execute(select(Product).where(Product.sku == sku))
        return result.scalars().first()

    async def get_by_emag_id(self, emag_id: str) -> Optional[Product]:
        """Get a product by eMAG ID."""
        result = await self.db.execute(
            select(Product).where(Product.emag_id == emag_id)
        )
        return result.scalars().first()

    async def bulk_upsert(
        self, products: List[Dict[str, Any]], update_fields: Optional[List[str]] = None
    ) -> int:
        """Bulk upsert products.

        Args:
            products: List of product dictionaries
            update_fields: List of fields to update on conflict

        Returns:
            int: Number of affected rows
        """
        if not products:
            return 0

        # Default fields to update if not specified
        if update_fields is None:
            update_fields = [
                "name",
                "description",
                "short_description",
                "base_price",
                "recommended_price",
                "currency",
                "brand",
                "manufacturer",
                "emag_part_number_key",
                "emag_category_id",
                "emag_brand_id",
                "emag_warranty_months",
                "characteristics",
                "images",
                "attachments",
                "is_active",
                "is_discontinued",
                "updated_at",
            ]

        # Generate the ON CONFLICT UPDATE clause
        update_dict = {field: getattr(Product, field) for field in update_fields}

        # Add current timestamp for updated_at if it's in update_fields
        if "updated_at" in update_fields:
            from sqlalchemy import func

            update_dict["updated_at"] = func.now()

        # Execute the bulk upsert
        stmt = (
            insert(Product)
            .values(products)
            .on_conflict_do_update(index_elements=[Product.sku], set_=update_dict)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_all(self) -> List[Product]:
        """Return all products."""

        result = await self.db.execute(select(Product))
        return result.scalars().all()

    async def update_by_sku(self, sku: str, values: Dict[str, Any]) -> int:
        """Update a product identified by SKU."""

        stmt = (
            update(Product)
            .where(Product.sku == sku)
            .values(**values)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount


# Factory function to get a product repository instance
def get_product_repository(db_session: Optional[AsyncSession] = None):
    """Get a product repository instance.

    Args:
        db_session: Optional database session. If not provided, a new one will be created.

    Returns:
        An instance of ProductRepository
    """
    from app.db.session import AsyncSessionLocal  # Import the async session factory

    if db_session is None:
        # Create a new async session
        db_session = AsyncSessionLocal()

    return ProductRepository(db_session)
