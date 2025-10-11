"""Enhanced offer service with product mapping integration."""

import logging
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import uuid4

from ..exceptions import EmagAPIError
from ..models.mapping import (
    MappingConfiguration,
    ProductTransformationResult,
)
from ..models.requests.offer import (
    ProductOfferCreate,
    ProductOfferUpdate,
)
from ..models.responses.offer import (
    ProductOfferResponse,
    ProductOfferSyncResponse,
    ProductOfferSyncStatus,
)
from ..services.mapping_config import MappingConfigManager
from .mapping_service import ProductMappingService
from .offer_service import OfferService

logger = logging.getLogger(__name__)


class ProductSyncError(Exception):
    """Exception raised when product synchronization fails."""


T = TypeVar("T")


class OfferServiceWithMapping(OfferService):
    """Enhanced offer service with product mapping capabilities."""

    def __init__(
        self,
        http_client,
        rate_limiter,
        mapping_service: ProductMappingService | None = None,
        mapping_config: MappingConfiguration | None = None,
    ):
        """Initialize the enhanced offer service.

        Args:
            http_client: An HTTP client instance for making requests to the eMAG API.
            rate_limiter: A rate limiter instance for controlling request rates.
            mapping_service: Optional mapping service instance.
            mapping_config: Optional mapping configuration.

        """
        super().__init__(http_client, rate_limiter)

        # Initialize mapping service
        if mapping_service is None:
            config_manager = MappingConfigManager()
            if mapping_config is None:
                mapping_config = config_manager.load_config("default")
            mapping_service = ProductMappingService(mapping_config)

        self.mapping_service = mapping_service
        self.mapping_config = mapping_config

    # Enhanced methods with mapping support

    async def create_offer(self, offer_data) -> ProductOfferResponse:
        """Create a new product offer, accepting both dict and ProductOfferCreate.

        Args:
            offer_data: The product offer data as dict or ProductOfferCreate model.

        Returns:
            The created product offer.

        Raises:
            EmagAPIError: If the creation fails.

        """
        # Convert dict to ProductOfferCreate if needed
        if isinstance(offer_data, dict):
            offer_data = ProductOfferCreate(**offer_data)

        # Call the parent method
        return await super().create_offer(offer_data)

    async def create_offer_with_mapping(
        self,
        internal_product: dict[str, Any],
        auto_create_mappings: bool = True,
    ) -> ProductOfferResponse:
        """Create a product offer using mapping transformation.

        Args:
            internal_product: Internal product data dictionary
            auto_create_mappings: Whether to auto-create missing mappings

        Returns:
            Created product offer response

        Raises:
            EmagAPIError: If creation fails

        """
        # Transform internal product to eMAG format
        transformation_result = self.mapping_service.transform_product_for_emag(
            internal_product,
        )

        if not transformation_result.success:
            error_msg = f"Product transformation failed: {', '.join(transformation_result.validation_errors)}"
            logger.error(error_msg)
            raise EmagAPIError(error_msg, status_code=400)

        # Create the offer using transformed data
        try:
            offer_data = ProductOfferCreate(**transformation_result.emag_product)
            response = await self.create_offer(offer_data)

            # Update mapping with the created offer ID
            if response.id and response.product_id:
                self.mapping_service.add_product_mapping(
                    internal_id=response.product_id,
                    emag_id=str(response.emag_id),
                    emag_offer_id=response.id,
                )

            logger.info(f"Created offer with mapping for product {response.product_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to create offer: {e!s}")
            raise

    async def update_offer_with_mapping(
        self,
        internal_product_id: str,
        internal_product: dict[str, Any],
    ) -> ProductOfferResponse:
        """Update a product offer using mapping transformation.

        Args:
            internal_product_id: Internal product ID
            internal_product: Updated internal product data

        Returns:
            Updated product offer response

        Raises:
            EmagAPIError: If update fails

        """
        # Get existing mapping
        mapping = self.mapping_service.get_product_mapping(internal_product_id)
        if not mapping:
            raise EmagAPIError(
                f"No mapping found for product {internal_product_id}",
                status_code=404,
            )

        # Transform internal product to eMAG format
        transformation_result = self.mapping_service.transform_product_for_emag(
            internal_product,
        )

        if not transformation_result.success:
            error_msg = f"Product transformation failed: {', '.join(transformation_result.validation_errors)}"
            logger.error(error_msg)
            raise EmagAPIError(error_msg, status_code=400)

        # Update the offer using transformed data
        try:
            update_data = ProductOfferUpdate(**transformation_result.emag_product)
            response = await self.update_offer(mapping.emag_id, update_data)

            logger.info(f"Updated offer with mapping for product {internal_product_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to update offer: {e!s}")
            raise

    async def sync_products_with_mapping(
        self,
        internal_products: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> ProductOfferSyncResponse:
        """Synchronize multiple products using mapping transformations.

        Args:
            internal_products: List of internal product data dictionaries
            batch_size: Optional batch size override

        Returns:
            Sync response with detailed results

        """
        if batch_size is None:
            batch_size = self.mapping_config.max_sync_batch_size

        sync_id = str(uuid4())
        total_products = len(internal_products)
        processed = 0
        success_count = 0
        failure_count = 0
        sync_errors = []

        logger.info(f"Starting product sync with mapping for {total_products} products")

        # Transform all products first
        transformed_products = []
        for i, product in enumerate(internal_products):
            try:
                transformation = self.mapping_service.transform_product_for_emag(
                    product,
                )

                if transformation.success:
                    transformed_products.append(
                        {
                            "original": product,
                            "transformed": transformation.emag_product,
                            "product_id": product.get("id")
                            or product.get("product_id")
                            or f"product_{i}",
                        },
                    )
                    success_count += 1
                else:
                    sync_errors.append(
                        {
                            "product_id": product.get("id")
                            or product.get("product_id")
                            or f"product_{i}",
                            "error": f"Transformation failed: {', '.join(transformation.validation_errors)}",
                        },
                    )
                    failure_count += 1

            except Exception as e:
                sync_errors.append(
                    {
                        "product_id": product.get("id")
                        or product.get("product_id")
                        or f"product_{i}",
                        "error": f"Unexpected error: {e!s}",
                    },
                )
                failure_count += 1

        logger.info(
            f"Transformed {success_count} products successfully, {failure_count} failed",
        )

        # Process successful transformations in batches
        if transformed_products:
            # Convert to eMAG format for bulk operations
            emag_offers = []
            for item in transformed_products:
                try:
                    offer_data = ProductOfferCreate(**item["transformed"])
                    emag_offers.append(
                        {
                            "product_id": item["product_id"],
                            **offer_data.dict(exclude_none=True),
                        },
                    )
                except Exception as e:
                    sync_errors.append(
                        {
                            "product_id": item["product_id"],
                            "error": f"Offer creation failed: {e!s}",
                        },
                    )
                    failure_count += 1

            # Perform bulk sync
            try:
                bulk_result = await self.sync_offers(emag_offers, batch_size=batch_size)

                # Update mappings for successful operations
                for offer in emag_offers:
                    product_id = offer["product_id"]
                    # Note: In a real implementation, you'd get the actual eMAG IDs from the response
                    self.mapping_service.add_product_mapping(
                        internal_id=product_id,
                        emag_id=f"emag_{product_id}",  # Placeholder - would get from actual response
                    )

                processed = bulk_result.processed_items

            except Exception as e:
                logger.error(f"Bulk sync failed: {e!s}")
                sync_errors.append({"error": f"Bulk sync operation failed: {e!s}"})

        # Determine overall sync status
        if failure_count == 0:
            status = ProductOfferSyncStatus.COMPLETED
        elif success_count == 0:
            status = ProductOfferSyncStatus.FAILED
        else:
            status = (
                ProductOfferSyncStatus.FAILED
            )  # Partial failures still marked as failed

        return ProductOfferSyncResponse(
            sync_id=sync_id,
            status=status,
            processed_items=processed,
            total_items=total_products,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            errors=sync_errors,
        )

    async def get_offer_by_internal_id(
        self,
        internal_product_id: str,
    ) -> ProductOfferResponse:
        """Get a product offer using internal product ID mapping.

        Args:
            internal_product_id: Internal product ID

        Returns:
            Product offer response

        Raises:
            EmagAPIError: If offer not found or mapping doesn't exist

        """
        # Get mapping
        mapping = self.mapping_service.get_product_mapping(internal_product_id)
        if not mapping:
            raise EmagAPIError(
                f"No mapping found for product {internal_product_id}",
                status_code=404,
            )

        # Get offer using eMAG ID
        return await self.get_offer(mapping.emag_id)

    async def delete_offer_by_internal_id(self, internal_product_id: str) -> bool:
        """Delete a product offer using internal product ID mapping.

        Args:
            internal_product_id: Internal product ID

        Returns:
            True if deletion was successful

        Raises:
            EmagAPIError: If deletion fails or mapping doesn't exist

        """
        # Get mapping
        mapping = self.mapping_service.get_product_mapping(internal_product_id)
        if not mapping:
            raise EmagAPIError(
                f"No mapping found for product {internal_product_id}",
                status_code=404,
            )

        # Delete offer using eMAG ID
        success = await self.delete_offer(mapping.emag_id)

        if success:
            # Optionally remove the mapping
            logger.info(f"Successfully deleted offer for product {internal_product_id}")

        return success

    # Mapping management methods

    def add_product_mapping(
        self,
        internal_id: str,
        emag_id: str,
        emag_offer_id: int | None = None,
    ) -> None:
        """Add a product ID mapping.

        Args:
            internal_id: Internal product ID
            emag_id: eMAG product ID
            emag_offer_id: Optional eMAG offer ID

        """
        self.mapping_service.add_product_mapping(internal_id, emag_id, emag_offer_id)

    def add_category_mapping(
        self,
        internal_id: str,
        emag_id: int,
        internal_name: str,
        emag_name: str,
    ) -> None:
        """Add a category ID mapping.

        Args:
            internal_id: Internal category ID
            emag_id: eMAG category ID
            internal_name: Internal category name
            emag_name: eMAG category name

        """
        self.mapping_service.add_category_mapping(
            internal_id,
            emag_id,
            internal_name,
            emag_name,
        )

    def add_brand_mapping(
        self,
        internal_id: str,
        emag_id: int,
        internal_name: str,
        emag_name: str,
    ) -> None:
        """Add a brand ID mapping.

        Args:
            internal_id: Internal brand ID
            emag_id: eMAG brand ID
            internal_name: Internal brand name
            emag_name: eMAG brand name

        """
        self.mapping_service.add_brand_mapping(
            internal_id,
            emag_id,
            internal_name,
            emag_name,
        )

    def get_mapping_statistics(self) -> dict[str, int]:
        """Get statistics about current mappings.

        Returns:
            Dictionary with mapping counts

        """
        return self.mapping_service.get_mapping_statistics()

    def transform_product_preview(
        self,
        internal_product: dict[str, Any],
    ) -> ProductTransformationResult:
        """Preview how an internal product would be transformed.

        Args:
            internal_product: Internal product data

        Returns:
            Transformation result (without actually creating/updating)

        """
        return self.mapping_service.transform_product_for_emag(internal_product)
