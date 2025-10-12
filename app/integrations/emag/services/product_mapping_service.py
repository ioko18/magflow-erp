"""Service for managing product mappings between internal system and eMAG."""

import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import generate_uuid
from app.models.mapping import (
    MappingConfiguration,
    MappingStatus,
    ProductMapping,
    SyncHistory,
)

logger = logging.getLogger(__name__)


class ProductMappingError(Exception):
    """Exception raised for product mapping errors."""


class MappingResult(BaseModel):
    """Result of a mapping operation."""

    success: bool = Field(..., description="Whether the mapping was successful")
    internal_id: str = Field(..., description="Internal product ID")
    emag_id: str | None = Field(None, description="eMAG product ID if mapped")
    emag_offer_id: int | None = Field(None, description="eMAG offer ID if mapped")
    message: str | None = Field(None, description="Status message")
    errors: list[str] = Field(default_factory=list, description="List of errors if any")


class BulkMappingResult(BaseModel):
    """Result of bulk mapping operations."""

    total: int = Field(0, description="Total number of items processed")
    successful: int = Field(0, description="Number of successful mappings")
    failed: int = Field(0, description="Number of failed mappings")
    results: list[MappingResult] = Field(
        default_factory=list,
        description="Individual mapping results",
    )


class ProductMappingService:
    """Service for managing product mappings between internal system and eMAG."""

    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session.

        Args:
            db: Async SQLAlchemy session

        """
        self.db = db

    async def get_mapping_configuration(
        self,
        name: str = "default",
    ) -> MappingConfiguration | None:
        """Get mapping configuration by name.

        Args:
            name: Name of the configuration (default: "default")

        Returns:
            Mapping configuration or None if not found

        """
        stmt = (
            select(MappingConfiguration)
            .where(MappingConfiguration.name == name)
            .where(MappingConfiguration.is_active == True)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_product_mapping(
        self,
        internal_id: str,
        emag_id: str | None = None,
        **kwargs,
    ) -> ProductMapping:
        """Create a new product mapping.

        Args:
            internal_id: Internal product ID
            emag_id: eMAG product ID (optional)
            **kwargs: Additional fields to set on the mapping

        Returns:
            The created ProductMapping instance

        """
        mapping = ProductMapping(
            internal_id=internal_id,
            emag_id=emag_id,
            status=MappingStatus.PENDING if not emag_id else MappingStatus.ACTIVE,
            **kwargs,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def get_product_mapping(
        self,
        internal_id: str | None = None,
        emag_id: str | None = None,
    ) -> ProductMapping | None:
        """Get a product mapping by internal ID or eMAG ID.

        Args:
            internal_id: Internal product ID
            emag_id: eMAG product ID

        Returns:
            ProductMapping if found, None otherwise

        Raises:
            ValueError: If neither internal_id nor emag_id is provided

        """
        if not internal_id and not emag_id:
            raise ValueError("Either internal_id or emag_id must be provided")

        stmt = select(ProductMapping)

        if internal_id and emag_id:
            stmt = stmt.where(
                or_(
                    ProductMapping.internal_id == internal_id,
                    ProductMapping.emag_id == emag_id,
                ),
            )
        elif internal_id:
            stmt = stmt.where(ProductMapping.internal_id == internal_id)
        else:
            stmt = stmt.where(ProductMapping.emag_id == emag_id)

        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_product_mapping(
        self,
        mapping_id: int,
        **update_data,
    ) -> ProductMapping | None:
        """Update a product mapping.

        Args:
            mapping_id: ID of the mapping to update
            **update_data: Fields to update

        Returns:
            Updated ProductMapping if found, None otherwise

        """
        stmt = select(ProductMapping).where(ProductMapping.id == mapping_id)
        result = await self.db.execute(stmt)
        mapping = result.scalars().first()

        if not mapping:
            return None

        for key, value in update_data.items():
            setattr(mapping, key, value)

        mapping.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def sync_product_to_emag(
        self,
        product_data: dict[str, Any],
        force_update: bool = False,
    ) -> MappingResult:
        """Synchronize a product to eMAG.

        Args:
            product_data: Product data in internal format
            force_update: Whether to force update even if no changes detected

        Returns:
            MappingResult with the result of the operation

        """
        internal_id = str(product_data.get("id"))
        if not internal_id:
            return MappingResult(
                success=False,
                internal_id="",
                message="Product ID is required",
                errors=["Product ID is required"],
            )

        # Check if we already have a mapping for this product
        mapping = await self.get_product_mapping(internal_id=internal_id)

        try:
            if mapping:
                # Update existing mapping
                if not force_update and not self._has_product_changed(
                    mapping,
                    product_data,
                ):
                    return MappingResult(
                        success=True,
                        internal_id=internal_id,
                        emag_id=mapping.emag_id,
                        emag_offer_id=mapping.emag_offer_id,
                        message="No changes detected, skipping update",
                    )

                # TODO: Implement actual eMAG API call to update product
                # For now, just update the mapping
                mapping.last_synced_at = datetime.now(UTC)
                mapping.status = MappingStatus.ACTIVE
                await self.db.commit()

                return MappingResult(
                    success=True,
                    internal_id=internal_id,
                    emag_id=mapping.emag_id,
                    emag_offer_id=mapping.emag_offer_id,
                    message="Product updated successfully",
                )
            # Create new mapping
            # TODO: Implement actual eMAG API call to create product
            # For now, just create the mapping with a dummy eMAG ID
            emag_id = f"emag_{generate_uuid()}"
            mapping = await self.create_product_mapping(
                internal_id=internal_id,
                emag_id=emag_id,
                status=MappingStatus.ACTIVE,
                last_synced_at=datetime.now(UTC),
            )

            return MappingResult(
                success=True,
                internal_id=internal_id,
                emag_id=emag_id,
                message="Product created successfully",
            )

        except Exception as e:
            logger.error(
                f"Error syncing product {internal_id} to eMAG: {e!s}",
                exc_info=True,
            )

            # Update mapping with error if it exists
            if mapping:
                mapping.status = MappingStatus.INACTIVE
                mapping.sync_errors = mapping.sync_errors or []
                mapping.sync_errors.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "error": str(e),
                        "product_data": product_data,
                    },
                )
                await self.db.commit()

            return MappingResult(
                success=False,
                internal_id=internal_id,
                emag_id=getattr(mapping, "emag_id", None),
                message=f"Error syncing product: {e!s}",
                errors=[str(e)],
            )

    async def bulk_sync_products(
        self,
        products_data: list[dict[str, Any]],
        batch_size: int = 50,
    ) -> BulkMappingResult:
        """Synchronize multiple products to eMAG in batches.

        Args:
            products_data: List of product data in internal format
            batch_size: Number of products to process in each batch

        Returns:
            BulkMappingResult with the results of all operations

        """
        result = BulkMappingResult()

        for i in range(0, len(products_data), batch_size):
            batch = products_data[i : i + batch_size]
            for product_data in batch:
                try:
                    sync_result = await self.sync_product_to_emag(product_data)
                    result.results.append(sync_result)

                    if sync_result.success:
                        result.successful += 1
                    else:
                        result.failed += 1

                except Exception as e:
                    logger.error(
                        f"Error processing product batch: {e!s}",
                        exc_info=True,
                    )
                    result.failed += 1

            # Commit after each batch
            try:
                await self.db.commit()
            except Exception as e:
                await self.db.rollback()
                logger.error(f"Error committing batch {i // batch_size + 1}: {e!s}")

        result.total = len(products_data)
        return result

    async def _has_product_changed(
        self,
        local_product: dict[str, Any],
        emag_product: dict[str, Any],
    ) -> bool:
        """Check if a product has changed since last sync using intelligent comparison.

        Args:
            local_product: Local product data
            emag_product: eMAG product data

        Returns:
            bool: True if product has changed, False otherwise

        """
        # Define critical fields that should trigger sync
        critical_fields = [
            "name",
            "price",
            "sale_price",
            "stock",
            "status",
            "description",
            "brand",
            "ean",
            "part_number",
        ]

        # Define fields with tolerance (for floating point comparison)
        price_fields = ["price", "sale_price", "recommended_price"]
        price_tolerance = 0.01  # 1 cent tolerance

        # Check critical fields
        for field in critical_fields:
            local_value = local_product.get(field)
            emag_value = emag_product.get(field)

            # Handle None values
            if local_value is None and emag_value is None:
                continue
            if local_value is None or emag_value is None:
                return True

            # Price fields with tolerance
            if field in price_fields:
                try:
                    local_float = float(local_value)
                    emag_float = float(emag_value)
                    if abs(local_float - emag_float) > price_tolerance:
                        logger.debug(
                            f"Price field '{field}' changed: {local_float} -> {emag_float}"
                        )
                        return True
                except (ValueError, TypeError):
                    if local_value != emag_value:
                        return True
            else:
                # String comparison (case-insensitive for text fields)
                if isinstance(local_value, str) and isinstance(emag_value, str):
                    if local_value.strip().lower() != emag_value.strip().lower():
                        logger.debug(
                            f"Field '{field}' changed: '{local_value}' -> '{emag_value}'"
                        )
                        return True
                elif local_value != emag_value:
                    logger.debug(
                        f"Field '{field}' changed: {local_value} -> {emag_value}"
                    )
                    return True

        # Check images if present
        local_images = local_product.get("images", [])
        emag_images = emag_product.get("images", [])
        if len(local_images) != len(emag_images):
            logger.debug(
                f"Image count changed: {len(local_images)} -> {len(emag_images)}"
            )
            return True

        # Check specifications/attributes if present
        local_specs = local_product.get("specifications", {})
        emag_specs = emag_product.get("specifications", {})
        if set(local_specs.keys()) != set(emag_specs.keys()):
            logger.debug("Specifications keys changed")
            return True

        # No significant changes detected
        logger.debug("No significant changes detected")
        return False

    async def log_sync_operation(
        self,
        operation: str,
        status: str,
        product_mapping_id: int | None = None,
        items_processed: int = 0,
        items_succeeded: int = 0,
        items_failed: int = 0,
        errors: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SyncHistory:
        """Log a synchronization operation.

        Args:
            operation: Type of operation (e.g., 'create', 'update', 'delete', 'sync')
            status: Status of the operation ('success', 'partial', 'failed')
            product_mapping_id: ID of the product mapping (if applicable)
            items_processed: Number of items processed
            items_succeeded: Number of items successfully processed
            items_failed: Number of items that failed
            errors: List of error details
            metadata: Additional metadata

        Returns:
            SyncHistory: The created sync history record

        """
        sync = SyncHistory(
            product_mapping_id=product_mapping_id,
            operation=operation,
            status=status,
            items_processed=items_processed,
            items_succeeded=items_succeeded,
            items_failed=items_failed,
            errors=errors or [],
            metadata=metadata or {},
        )

        self.db.add(sync)
        await self.db.commit()
        await self.db.refresh(sync)
        return sync
