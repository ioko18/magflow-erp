"""
Cache management endpoints for eMAG integration.

Provides endpoints to manage and monitor cache.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_active_user
from app.core.cache_config import get_all_cache_stats, invalidate_cache
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/cache", tags=["emag-cache"])


@router.get("/stats")
async def get_cache_stats(
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get cache statistics for all caches.

    Returns:
        Dictionary with cache statistics
    """
    try:
        stats = get_all_cache_stats()

        return {
            "success": True,
            "caches": stats,
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}",
        )


@router.post("/invalidate/{cache_name}")
async def invalidate_cache_endpoint(
    cache_name: str,
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Invalidate a specific cache.

    Args:
        cache_name: Name of the cache to invalidate

    Returns:
        Success message
    """
    try:
        valid_caches = [
            "emag_products",
            "emag_orders",
            "emag_sync_status",
            "product_count",
        ]

        if cache_name not in valid_caches:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cache name. Valid caches: {', '.join(valid_caches)}",
            )

        invalidate_cache(cache_name)

        return {
            "success": True,
            "message": f"Cache '{cache_name}' invalidated successfully",
            "cache_name": cache_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}",
        )


@router.post("/invalidate-all")
async def invalidate_all_caches(
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Invalidate all caches.

    Returns:
        Success message
    """
    try:
        caches = ["emag_products", "emag_orders", "emag_sync_status", "product_count"]

        for cache_name in caches:
            invalidate_cache(cache_name)

        return {
            "success": True,
            "message": "All caches invalidated successfully",
            "invalidated_caches": caches,
        }

    except Exception as e:
        logger.error(f"Error invalidating all caches: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate all caches: {str(e)}",
        )
