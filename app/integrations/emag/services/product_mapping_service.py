"""Service for managing product mappings between internal system and eMAG."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.emag.models.mapping import (
    MappingConfiguration,
    MappingStatus,
    ProductMapping,
    SyncHistory,
)
from app.utils import generate_uuid

logger = logging.getLogger(__name__)


class ProductMappingError(Exception):
    """Exception raised for product mapping errors."""


class MappingResult(BaseModel):
    """Result of a mapping operation."""

    success: bool = Field(..., description="Whether the mapping was successful")
    internal_id: str = Field(..., description="Internal product ID")
    emag_id: Optional[str] = Field(None, description="eMAG product ID if mapped")
    emag_offer_id: Optional[int] = Field(None, description="eMAG offer ID if mapped")
    message: Optional[str] = Field(None, description="Status message")
    errors: List[str] = Field(default_factory=list, description="List of errors if any")


class BulkMappingResult(BaseModel):
    """Result of bulk mapping operations."""

    total: int = Field(0, description="Total number of items processed")
    successful: int = Field(0, description="Number of successful mappings")
    failed: int = Field(0, description="Number of failed mappings")
    results: List[MappingResult] = Field(
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
    ) -> Optional[MappingConfiguration]:
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
        emag_id: Optional[str] = None,
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
        internal_id: Optional[str] = None,
        emag_id: Optional[str] = None,
    ) -> Optional[ProductMapping]:
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
    ) -> Optional[ProductMapping]:
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

        mapping.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def sync_product_to_emag(
        self,
        product_data: Dict[str, Any],
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
                mapping.last_synced_at = datetime.now(timezone.utc)
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
                last_synced_at=datetime.now(timezone.utc),
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        products_data: List[Dict[str, Any]],
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
                logger.error(f"Error committing batch {i//batch_size + 1}: {e!s}")

        result.total = len(products_data)
        return result

    def _has_product_changed(
        self,
        mapping: ProductMapping,
        product_data: Dict[str, Any],
    ) -> bool:
        """Check if product data has changed since last sync.

        Args:
            mapping: Product mapping
            product_data: Current product data

        Returns:
            bool: True if product has changed, False otherwise

        """
        # TODO: Implement actual change detection logic
        # For now, always return True to force update
        return True

    async def log_sync_operation(
        self,
        operation: str,
        status: str,
        product_mapping_id: Optional[int] = None,
        items_processed: int = 0,
        items_succeeded: int = 0,
        items_failed: int = 0,
        errors: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
