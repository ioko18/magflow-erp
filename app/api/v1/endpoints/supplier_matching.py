"""API endpoints for supplier product matching and import.

Provides endpoints for:
- Importing supplier products from Excel files
- Running matching algorithms
- Viewing and managing matching groups
- Price comparison across suppliers
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session, get_current_active_user
from app.models.supplier_matching import (
    SupplierRawProduct,
    ProductMatchingGroup,
    MatchingStatus
)
from app.models.supplier import Supplier
from app.services.product_matching_service import ProductMatchingService
from app.services.supplier_import_service import SupplierImportService
from app.schemas.supplier_matching import (
    SupplierRawProductResponse,
    ProductMatchingGroupResponse,
    ProductMatchingGroupDetail,
    PriceComparisonResponse,
    ImportResponse,
    MatchingStatsResponse,
    MatchingRequest
)

router = APIRouter()


# ==================== IMPORT ENDPOINTS ====================

@router.post("/import/excel", response_model=ImportResponse)
async def import_products_from_excel(
    supplier_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Import supplier products from Excel file.
    
    Expected Excel columns:
    - Nume produs (Chinese product name)
    - Pret CNY (Price in CNY)
    - URL produs (Product URL from 1688.com)
    - URL imagine (Image URL)
    
    You can customize column names by providing a column_mapping parameter.
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )

    # Read file content
    content = await file.read()

    # Import products
    import_service = SupplierImportService(db)

    try:
        result = await import_service.import_from_excel(
            file_content=content,
            supplier_id=supplier_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/import/batches", response_model=List[dict])
async def get_import_batches(
    supplier_id: Optional[int] = None,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Get list of import batches."""

    stmt = select(
        SupplierRawProduct.import_batch_id,
        SupplierRawProduct.supplier_id,
        func.min(SupplierRawProduct.import_date).label('import_date'),
        func.count(SupplierRawProduct.id).label('product_count')
    ).group_by(
        SupplierRawProduct.import_batch_id,
        SupplierRawProduct.supplier_id
    )

    if supplier_id:
        stmt = stmt.where(SupplierRawProduct.supplier_id == supplier_id)

    stmt = stmt.order_by(func.min(SupplierRawProduct.import_date).desc())

    result = await db.execute(stmt)
    batches = result.all()

    return [
        {
            "batch_id": batch.import_batch_id,
            "supplier_id": batch.supplier_id,
            "import_date": batch.import_date,
            "product_count": batch.product_count
        }
        for batch in batches
    ]


@router.get("/import/summary", response_model=List[dict])
async def get_supplier_products_summary(
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Get summary of products per supplier."""

    import_service = SupplierImportService(db)
    summary = await import_service.get_supplier_products_summary()
    return summary


# ==================== MATCHING ENDPOINTS ====================

@router.post("/match/text", response_model=List[ProductMatchingGroupResponse])
async def match_products_by_text(
    request: MatchingRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Run text-based matching algorithm.
    
    Matches products based on Chinese name similarity using:
    - Jaccard similarity
    - N-gram similarity (bigrams and trigrams)
    """
    matching_service = ProductMatchingService(db)

    groups = await matching_service.match_products_by_text(
        threshold=request.threshold
    )

    return [
        ProductMatchingGroupResponse(
            id=group.id,
            group_name=group.group_name,
            group_name_en=group.group_name_en,
            product_count=group.product_count,
            min_price_cny=group.min_price_cny,
            max_price_cny=group.max_price_cny,
            avg_price_cny=group.avg_price_cny,
            confidence_score=group.confidence_score,
            matching_method=group.matching_method,
            status=group.status,
            created_at=group.created_at
        )
        for group in groups
    ]


@router.post("/match/image", response_model=List[ProductMatchingGroupResponse])
async def match_products_by_image(
    request: MatchingRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Run image-based matching algorithm.
    
    Matches products based on image similarity using perceptual hashing.
    Note: Requires image hashes to be pre-calculated.
    """
    matching_service = ProductMatchingService(db)

    groups = await matching_service.match_products_by_image(
        threshold=request.threshold
    )

    return [
        ProductMatchingGroupResponse(
            id=group.id,
            group_name=group.group_name,
            group_name_en=group.group_name_en,
            product_count=group.product_count,
            min_price_cny=group.min_price_cny,
            max_price_cny=group.max_price_cny,
            avg_price_cny=group.avg_price_cny,
            confidence_score=group.confidence_score,
            matching_method=group.matching_method,
            status=group.status,
            created_at=group.created_at
        )
        for group in groups
    ]


@router.post("/match/hybrid", response_model=List[ProductMatchingGroupResponse])
async def match_products_hybrid(
    request: MatchingRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Run hybrid matching algorithm (RECOMMENDED).
    
    Combines text and image similarity for best accuracy:
    - Text similarity: 60% weight
    - Image similarity: 40% weight
    """
    matching_service = ProductMatchingService(db)

    groups = await matching_service.match_products_hybrid(
        threshold=request.threshold
    )

    return [
        ProductMatchingGroupResponse(
            id=group.id,
            group_name=group.group_name,
            group_name_en=group.group_name_en,
            product_count=group.product_count,
            min_price_cny=group.min_price_cny,
            max_price_cny=group.max_price_cny,
            avg_price_cny=group.avg_price_cny,
            confidence_score=group.confidence_score,
            matching_method=group.matching_method,
            status=group.status,
            created_at=group.created_at
        )
        for group in groups
    ]


# ==================== GROUP MANAGEMENT ====================

@router.get("/groups", response_model=List[ProductMatchingGroupResponse])
async def get_matching_groups(
    status: Optional[str] = None,
    min_confidence: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Get list of matching groups with filters."""

    stmt = select(ProductMatchingGroup).where(
        ProductMatchingGroup.is_active
    )

    if status:
        stmt = stmt.where(ProductMatchingGroup.status == status)

    if min_confidence:
        stmt = stmt.where(ProductMatchingGroup.confidence_score >= min_confidence)

    stmt = stmt.order_by(ProductMatchingGroup.created_at.desc())
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    groups = result.scalars().all()

    return [
        ProductMatchingGroupResponse(
            id=group.id,
            group_name=group.group_name,
            group_name_en=group.group_name_en,
            product_count=group.product_count,
            min_price_cny=group.min_price_cny,
            max_price_cny=group.max_price_cny,
            avg_price_cny=group.avg_price_cny,
            confidence_score=group.confidence_score,
            matching_method=group.matching_method,
            status=group.status,
            created_at=group.created_at
        )
        for group in groups
    ]


@router.get("/groups/{group_id}", response_model=ProductMatchingGroupDetail)
async def get_matching_group_detail(
    group_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Get detailed information about a matching group."""

    # Get group
    stmt = select(ProductMatchingGroup).where(ProductMatchingGroup.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get products in group
    products_stmt = select(SupplierRawProduct, Supplier).join(
        Supplier,
        SupplierRawProduct.supplier_id == Supplier.id
    ).where(
        SupplierRawProduct.product_group_id == group_id
    ).order_by(SupplierRawProduct.price_cny.asc())

    products_result = await db.execute(products_stmt)
    products_data = products_result.all()

    products = [
        {
            "id": product.id,
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "chinese_name": product.chinese_name,
            "english_name": product.english_name,
            "price_cny": product.price_cny,
            "product_url": product.product_url,
            "image_url": product.image_url,
            "matching_status": product.matching_status
        }
        for product, supplier in products_data
    ]

    return ProductMatchingGroupDetail(
        id=group.id,
        group_name=group.group_name,
        group_name_en=group.group_name_en,
        description=group.description,
        representative_image_url=group.representative_image_url,
        product_count=group.product_count,
        min_price_cny=group.min_price_cny,
        max_price_cny=group.max_price_cny,
        avg_price_cny=group.avg_price_cny,
        best_supplier_id=group.best_supplier_id,
        confidence_score=group.confidence_score,
        matching_method=group.matching_method,
        status=group.status,
        verified_by=group.verified_by,
        verified_at=group.verified_at,
        created_at=group.created_at,
        products=products
    )


@router.post("/groups/{group_id}/confirm")
async def confirm_matching_group(
    group_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Manually confirm a matching group."""

    matching_service = ProductMatchingService(db)

    try:
        group = await matching_service.confirm_match(
            group_id=group_id,
            user_id=current_user.id
        )
        return {"success": True, "group_id": group.id, "status": group.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/groups/{group_id}/reject")
async def reject_matching_group(
    group_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Reject a matching group and unlink products."""

    matching_service = ProductMatchingService(db)

    try:
        await matching_service.reject_match(
            group_id=group_id,
            user_id=current_user.id
        )
        return {"success": True, "group_id": group_id, "status": "rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PRICE COMPARISON ====================

@router.get("/groups/{group_id}/price-comparison", response_model=PriceComparisonResponse)
async def get_price_comparison(
    group_id: int,
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Get detailed price comparison for a matching group.
    
    Args:
        group_id: ID of the matching group
        limit: Optional limit on number of products to return (useful for preview)
    """

    matching_service = ProductMatchingService(db)

    # Get group info
    stmt = select(ProductMatchingGroup).where(ProductMatchingGroup.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get price comparison
    comparisons = await matching_service.get_price_comparison(group_id)

    if not comparisons:
        raise HTTPException(status_code=404, detail="No products in group")

    # Apply limit if specified (useful for preview cards showing only 2 products)
    if limit and limit > 0:
        comparisons = comparisons[:limit]

    # Calculate savings (use full group data for accurate savings)
    best_price = comparisons[0]["price_cny"]
    worst_price = comparisons[-1]["price_cny"] if len(comparisons) > 1 else best_price
    savings_cny = worst_price - best_price
    savings_percent = (savings_cny / worst_price * 100) if worst_price > 0 else 0

    return PriceComparisonResponse(
        group_id=group_id,
        group_name=group.group_name,
        product_count=len(comparisons),
        best_price_cny=best_price,
        worst_price_cny=worst_price,
        avg_price_cny=group.avg_price_cny,
        savings_cny=savings_cny,
        savings_percent=savings_percent,
        products=comparisons
    )


# ==================== STATISTICS ====================

@router.get("/stats", response_model=MatchingStatsResponse)
async def get_matching_statistics(
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Get overall matching statistics."""

    # Count total products
    total_products_stmt = select(func.count(SupplierRawProduct.id)).where(
        SupplierRawProduct.is_active
    )
    total_products_result = await db.execute(total_products_stmt)
    total_products = total_products_result.scalar()

    # Count matched products
    matched_stmt = select(func.count(SupplierRawProduct.id)).where(
        and_(
            SupplierRawProduct.is_active,
            SupplierRawProduct.matching_status != MatchingStatus.PENDING
        )
    )
    matched_result = await db.execute(matched_stmt)
    matched_products = matched_result.scalar()

    # Count groups
    groups_stmt = select(func.count(ProductMatchingGroup.id)).where(
        ProductMatchingGroup.is_active
    )
    groups_result = await db.execute(groups_stmt)
    total_groups = groups_result.scalar()

    # Count verified groups
    verified_stmt = select(func.count(ProductMatchingGroup.id)).where(
        and_(
            ProductMatchingGroup.is_active,
            ProductMatchingGroup.status == MatchingStatus.MANUAL_MATCHED
        )
    )
    verified_result = await db.execute(verified_stmt)
    verified_groups = verified_result.scalar()

    # Count suppliers
    suppliers_stmt = select(func.count(func.distinct(SupplierRawProduct.supplier_id))).where(
        SupplierRawProduct.is_active
    )
    suppliers_result = await db.execute(suppliers_stmt)
    active_suppliers = suppliers_result.scalar()

    return MatchingStatsResponse(
        total_products=total_products,
        matched_products=matched_products,
        pending_products=total_products - matched_products,
        total_groups=total_groups,
        verified_groups=verified_groups,
        pending_groups=total_groups - verified_groups,
        active_suppliers=active_suppliers,
        matching_rate=(matched_products / total_products * 100) if total_products > 0 else 0
    )


# ==================== RAW PRODUCTS ====================

@router.get("/products", response_model=List[SupplierRawProductResponse])
async def get_raw_products(
    supplier_id: Optional[int] = None,
    matching_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Get list of raw supplier products."""

    stmt = select(SupplierRawProduct).where(
        SupplierRawProduct.is_active
    )

    if supplier_id:
        stmt = stmt.where(SupplierRawProduct.supplier_id == supplier_id)

    if matching_status:
        stmt = stmt.where(SupplierRawProduct.matching_status == matching_status)

    stmt = stmt.order_by(SupplierRawProduct.created_at.desc())
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    products = result.scalars().all()

    return [
        SupplierRawProductResponse(
            id=product.id,
            supplier_id=product.supplier_id,
            chinese_name=product.chinese_name,
            english_name=product.english_name,
            price_cny=product.price_cny,
            product_url=product.product_url,
            image_url=product.image_url,
            matching_status=product.matching_status,
            product_group_id=product.product_group_id,
            import_batch_id=product.import_batch_id,
            created_at=product.created_at
        )
        for product in products
    ]


@router.delete("/products/{product_id}")
async def delete_supplier_product(
    product_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Delete a single supplier product (soft delete by setting is_active=False)."""
    
    # Check if product exists
    stmt = select(SupplierRawProduct).where(SupplierRawProduct.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Soft delete
    product.is_active = False
    await db.commit()
    
    return {
        "success": True,
        "message": f"Product {product_id} deleted successfully",
        "product_id": product_id
    }


@router.post("/products/delete-batch")
async def delete_supplier_products_batch(
    product_ids: List[int] = Body(..., embed=True),
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Delete multiple supplier products in batch (soft delete)."""
    
    if not product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided")
    
    # Update products to inactive
    stmt = (
        select(SupplierRawProduct)
        .where(SupplierRawProduct.id.in_(product_ids))
        .where(SupplierRawProduct.is_active)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()
    
    deleted_count = 0
    for product in products:
        product.is_active = False
        deleted_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Deleted {deleted_count} products successfully",
        "deleted_count": deleted_count,
        "requested_count": len(product_ids)
    }


@router.delete("/products/by-supplier/{supplier_id}")
async def delete_products_by_supplier(
    supplier_id: int,
    import_batch_id: Optional[str] = None,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Delete all products from a specific supplier, optionally filtered by import batch."""
    
    stmt = (
        select(SupplierRawProduct)
        .where(SupplierRawProduct.supplier_id == supplier_id)
        .where(SupplierRawProduct.is_active)
    )
    
    if import_batch_id:
        stmt = stmt.where(SupplierRawProduct.import_batch_id == import_batch_id)
    
    result = await db.execute(stmt)
    products = result.scalars().all()
    
    deleted_count = 0
    for product in products:
        product.is_active = False
        deleted_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Deleted {deleted_count} products from supplier {supplier_id}",
        "deleted_count": deleted_count,
        "supplier_id": supplier_id,
        "import_batch_id": import_batch_id
    }


@router.post("/cleanup/orphaned-groups")
async def cleanup_orphaned_matching_groups(
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """Cleanup matching groups that have no active products.
    
    This endpoint will:
    1. Find all groups with zero active products
    2. Soft delete them (set is_active=False)
    3. Return count of cleaned groups
    
    Use this after deleting products to clean up orphaned groups.
    """
    
    # Subquery to check if group has active products
    has_active_products = (
        select(SupplierRawProduct.id)
        .where(SupplierRawProduct.product_group_id == ProductMatchingGroup.id)
        .where(SupplierRawProduct.is_active)
        .exists()
    )
    
    # Get groups without active products
    stmt = (
        select(ProductMatchingGroup)
        .where(ProductMatchingGroup.is_active)
        .where(~has_active_products)
    )
    
    result = await db.execute(stmt)
    orphaned_groups = result.scalars().all()
    
    # Soft delete orphaned groups
    cleaned_count = 0
    for group in orphaned_groups:
        group.is_active = False
        cleaned_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Cleaned up {cleaned_count} orphaned matching groups",
        "cleaned_count": cleaned_count
    }


@router.post("/reset/all-matching")
async def reset_all_matching(
    confirm: bool = False,
    db: AsyncSession = Depends(get_database_session),
    current_user = Depends(get_current_active_user)
):
    """DANGEROUS: Reset all matching data (groups and product assignments).
    
    This will:
    1. Soft delete ALL matching groups
    2. Reset all products to 'pending' status
    3. Clear product_group_id from all products
    
    Requires confirm=True parameter to execute.
    Use this only when you want to start matching from scratch.
    """
    
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="This is a destructive operation. Set confirm=True to proceed."
        )
    
    # Soft delete all groups
    groups_stmt = select(ProductMatchingGroup).where(ProductMatchingGroup.is_active)
    groups_result = await db.execute(groups_stmt)
    groups = groups_result.scalars().all()
    
    groups_count = 0
    for group in groups:
        group.is_active = False
        groups_count += 1
    
    # Reset all products
    products_stmt = select(SupplierRawProduct).where(SupplierRawProduct.is_active)
    products_result = await db.execute(products_stmt)
    products = products_result.scalars().all()
    
    products_count = 0
    for product in products:
        product.product_group_id = None
        product.matching_status = MatchingStatus.PENDING
        products_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Reset complete: {groups_count} groups deleted, {products_count} products reset to pending",
        "groups_deleted": groups_count,
        "products_reset": products_count
    }
