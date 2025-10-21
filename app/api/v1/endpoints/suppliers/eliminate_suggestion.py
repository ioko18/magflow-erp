"""
Endpoint for eliminating product match suggestions.

This module provides the API endpoint to permanently eliminate incorrect
product match suggestions, preventing them from reappearing in future
automatic matching operations.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.eliminated_suggestion import EliminatedSuggestion
from app.models.product import Product
from app.models.supplier import SupplierProduct
from app.security.jwt import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete("/{supplier_id}/products/{product_id}/suggestions/{local_product_id}")
async def eliminate_suggestion(
    supplier_id: int,
    product_id: int,
    local_product_id: int,
    reason: str | None = Query(None, max_length=500, description="Optional reason for elimination"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Eliminate a product suggestion to prevent it from reappearing.

    This creates a record in eliminated_suggestions table that will be
    used to filter out this suggestion in future matching operations.

    Args:
        supplier_id: ID of the supplier
        product_id: ID of the supplier product
        local_product_id: ID of the local product to eliminate from suggestions
        reason: Optional reason for elimination
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success response with elimination details

    Raises:
        HTTPException: If supplier product or local product not found
    """
    try:
        # Verify supplier product exists
        sp_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.id == product_id,
                SupplierProduct.supplier_id == supplier_id,
            )
        )
        sp_result = await db.execute(sp_query)
        supplier_product = sp_result.scalar_one_or_none()

        if not supplier_product:
            raise HTTPException(status_code=404, detail="Supplier product not found")

        # Verify local product exists
        lp_query = select(Product).where(Product.id == local_product_id)
        lp_result = await db.execute(lp_query)
        local_product = lp_result.scalar_one_or_none()

        if not local_product:
            raise HTTPException(status_code=404, detail="Local product not found")

        # Check if already eliminated
        check_query = select(EliminatedSuggestion).where(
            and_(
                EliminatedSuggestion.supplier_product_id == product_id,
                EliminatedSuggestion.local_product_id == local_product_id,
            )
        )
        check_result = await db.execute(check_query)
        existing = check_result.scalar_one_or_none()

        if existing:
            logger.info(
                f"Suggestion already eliminated: supplier_product={product_id}, "
                f"local_product={local_product_id}"
            )
            return {
                "status": "success",
                "data": {
                    "message": "Suggestion already eliminated",
                    "id": existing.id,
                    "eliminated_at": existing.eliminated_at.isoformat(),
                    "already_existed": True,
                },
            }

        # Create elimination record
        elimination = EliminatedSuggestion(
            supplier_product_id=product_id,
            local_product_id=local_product_id,
            eliminated_by=current_user.id,
            reason=reason,
        )

        db.add(elimination)
        await db.commit()
        await db.refresh(elimination)

        logger.info(
            f"User {current_user.id} eliminated suggestion: "
            f"supplier_product={product_id}, local_product={local_product_id}, "
            f"reason={reason}"
        )

        return {
            "status": "success",
            "data": {
                "message": "Suggestion eliminated successfully",
                "id": elimination.id,
                "eliminated_at": elimination.eliminated_at.isoformat(),
                "already_existed": False,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminating suggestion: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{supplier_id}/products/{product_id}/eliminated-suggestions")
async def get_eliminated_suggestions(
    supplier_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get all eliminated suggestions for a supplier product.

    This endpoint returns the list of local products that have been
    eliminated as suggestions for the specified supplier product.

    Args:
        supplier_id: ID of the supplier
        product_id: ID of the supplier product
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of eliminated suggestions with details
    """
    try:
        # Verify supplier product exists
        sp_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.id == product_id,
                SupplierProduct.supplier_id == supplier_id,
            )
        )
        sp_result = await db.execute(sp_query)
        supplier_product = sp_result.scalar_one_or_none()

        if not supplier_product:
            raise HTTPException(status_code=404, detail="Supplier product not found")

        # Get eliminated suggestions
        query = select(EliminatedSuggestion).where(
            EliminatedSuggestion.supplier_product_id == product_id
        )
        result = await db.execute(query)
        eliminations = result.scalars().all()

        return {
            "status": "success",
            "data": {
                "supplier_product_id": product_id,
                "eliminated_count": len(eliminations),
                "eliminations": [
                    {
                        "id": e.id,
                        "local_product_id": e.local_product_id,
                        "eliminated_at": e.eliminated_at.isoformat(),
                        "eliminated_by": e.eliminated_by,
                        "reason": e.reason,
                    }
                    for e in eliminations
                ],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting eliminated suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
