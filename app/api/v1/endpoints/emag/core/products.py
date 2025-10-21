"""
eMAG Products API endpoints.

Handles product-related operations for eMAG marketplace integration.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_active_user
from app.core.config import get_settings
from app.core.dependency_injection import ServiceContext
from app.core.logging import get_logger
from app.services.emag.emag_integration_service import EmagIntegrationService

logger = get_logger(__name__)
router = APIRouter(prefix="/products", tags=["emag-products"])


@router.get("/all")
async def get_all_emag_products(
    account_type: str = Query("main", description="Account type: main or fbe"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get all products from eMAG API.

    Args:
        account_type: Account type (main or fbe)
        limit: Maximum number of products to return
        offset: Offset for pagination

    Returns:
        Dictionary with products and pagination info
    """
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        # Initialize the service
        await service.initialize()

        logger.info(
            "Fetching products from eMAG - account: %s, limit: %s, offset: %s",
            account_type,
            limit,
            offset,
        )

        try:
            # Get products from eMAG API
            products = await service.get_products(limit=limit, offset=offset)

            return {
                "success": True,
                "account_type": account_type,
                "count": len(products),
                "limit": limit,
                "offset": offset,
                "products": products,
            }
        finally:
            # Clean up the service
            await service.close()

    except Exception as e:
        logger.error(f"Error fetching products: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch products: {str(e)}",
        ) from e


@router.get("/{product_id}")
async def get_emag_product_by_id(
    product_id: int,
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get a specific product by ID from eMAG API.

    Args:
        product_id: eMAG product ID
        account_type: Account type (main or fbe)

    Returns:
        Product details
    """
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        # Initialize the service
        await service.initialize()

        logger.info(
            f"Fetching product {product_id} from eMAG - account: {account_type}"
        )

        try:
            product = await service.get_product_by_id(product_id)

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {product_id} not found",
                )

            return {
                "success": True,
                "account_type": account_type,
                "product": product,
            }
        finally:
            # Clean up the service
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch product: {str(e)}",
        ) from e


@router.get("/count")
async def get_products_count(
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get total count of products from eMAG API.

    Args:
        account_type: Account type (main or fbe)

    Returns:
        Total count of products
    """
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        # Initialize the service
        await service.initialize()

        logger.info(f"Getting products count from eMAG - account: {account_type}")

        try:
            count = await service.get_products_count()

            return {
                "success": True,
                "account_type": account_type,
                "total_count": count,
            }
        finally:
            # Clean up the service
            await service.close()

    except Exception as e:
        logger.error(f"Error getting products count: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products count: {str(e)}",
        ) from e
