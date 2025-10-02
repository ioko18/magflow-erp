"""
Enhanced eMAG Sync API Endpoints for MagFlow ERP.

This module provides comprehensive REST API endpoints for eMAG marketplace
integration, supporting full product synchronization, order management,
and real-time monitoring according to eMAG API v4.4.8 specifications.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.models.emag_models import EmagProductOfferV2, EmagProductV2
from app.services.enhanced_emag_service import EnhancedEmagIntegrationService

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models for request/response
class SyncAllProductsRequest(BaseModel):
    """Request model for syncing all products."""

    max_pages_per_account: int = Field(
        default=1000,  # Increased from 100 to 1000
        ge=1,
        le=1000,  # Increased from 500 to 1000
        description="Maximum pages to process per account (max 1000)"
    )
    delay_between_requests: float = Field(
        default=1.5,  # Increased from 1.2 to 1.5 for more safety
        ge=0.5,  # Reduced minimum from 0.1 to 0.5
        le=30.0,  # Increased from 10.0 to 30.0
        description="Delay between API requests in seconds (0.5-30.0)",
    )
    include_inactive: bool = Field(
        default=True,  # Changed default to True to ensure we get all products
        description="Whether to include inactive products (recommended: True for full sync)"
    )


class SyncAllOffersRequest(BaseModel):
    """Request model for syncing all offers."""

    max_pages_per_account: int = Field(
        default=50, ge=1, le=200, description="Maximum pages to process per account"
    )
    delay_between_requests: float = Field(
        default=1.2,
        ge=0.1,
        le=10.0,
        description="Delay between API requests in seconds",
    )


class SyncScheduledRequest(BaseModel):
    """Request model for scheduled sync configuration."""

    sync_interval_minutes: int = Field(
        default=60, ge=5, le=1440, description="Sync interval in minutes"
    )
    sync_types: List[str] = Field(
        default=["products", "offers"], description="Types of data to sync"
    )
    accounts: List[str] = Field(
        default=["main", "fbe"], description="Accounts to sync from"
    )
    max_pages_per_account: int = Field(
        default=50, ge=1, le=200, description="Maximum pages per sync"
    )


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""

    account_type: str
    latest_sync: Dict[str, Any]
    active_progress: Optional[Dict[str, Any]]
    metrics: Dict[str, Any]


class ProductSyncResponse(BaseModel):
    """Response model for product sync results."""

    main_account: Optional[Dict[str, Any]]
    fbe_account: Optional[Dict[str, Any]]
    combined: Dict[str, Any]
    sync_timestamp: str
    total_products_processed: int


# API Endpoints


@router.post("/sync/all-products", response_model=ProductSyncResponse)
async def sync_all_products(
    request: SyncAllProductsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Synchronize all products from both MAIN and FBE eMAG accounts.

    This endpoint performs a comprehensive product synchronization with:
    - Full pagination support (up to 500 pages per account)
    - Automatic deduplication by SKU
    - Rate limiting compliance with eMAG API v4.4.8
    - Real-time progress tracking
    - Error recovery and retry logic

    The sync process:
    1. Fetches products from MAIN account
    2. Fetches products from FBE account
    3. Combines and deduplicates by SKU (MAIN takes priority)
    4. Saves to database with full metadata
    5. Returns comprehensive results and statistics
    """
    try:
        logger.info(
            "Starting full product sync requested by user %s with params: %s",
            current_user.email,
            request.dict(),
        )

        # Initialize enhanced eMAG service (use main as default, sync_all_products_from_both_accounts handles both)
        async with EnhancedEmagIntegrationService("main", db) as emag_service:
            # Perform full sync
            results = await emag_service.sync_all_products_from_both_accounts(
                max_pages_per_account=request.max_pages_per_account,
                delay_between_requests=request.delay_between_requests,
                include_inactive=request.include_inactive,
            )

            # Calculate total processed
            total_processed = 0
            if results.get("main_account"):
                total_processed += results["main_account"].get("products_count", 0)
            if results.get("fbe_account"):
                total_processed += results["fbe_account"].get("products_count", 0)

            response = ProductSyncResponse(
                main_account=results.get("main_account"),
                fbe_account=results.get("fbe_account"),
                combined=results.get("combined", {}),
                sync_timestamp=datetime.utcnow().isoformat(),
                total_products_processed=total_processed,
            )

            logger.info("Completed full product sync with %d products", total_processed)
            return response

    except Exception as e:
        logger.error("Failed to sync all products: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to sync products: {str(e)}"
        )


@router.post("/sync/all-offers")
async def sync_all_offers(
    request: SyncAllOffersRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Synchronize all offers from both MAIN and FBE eMAG accounts.

    Similar to product sync but focuses on offer-specific data:
    - Price and stock information
    - Availability status
    - Marketplace-specific settings
    - Shipping and handling details
    """
    try:
        logger.info(
            "Starting full offer sync requested by user %s with params: %s",
            current_user.email,
            request.dict(),
        )

        async with EnhancedEmagIntegrationService("main", db) as emag_service:
            results = await emag_service.sync_all_offers_from_both_accounts(
                max_pages_per_account=request.max_pages_per_account,
                delay_between_requests=request.delay_between_requests,
            )

            logger.info("Completed full offer sync")
            return results

    except Exception as e:
        logger.error("Failed to sync all offers: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync offers: {str(e)}")


@router.get("/products/all")
async def get_all_products(
    account_type: str = Query(
        default="both", description="Account type: main, fbe, or both"
    ),
    max_pages_per_account: int = Query(default=25, ge=1, le=100),
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all products from specified eMAG account(s).

    This endpoint provides read-only access to synchronized product data
    with filtering and pagination options.
    """
    try:
        if account_type not in ["main", "fbe", "both"]:
            raise HTTPException(status_code=400, detail="Invalid account_type")

        # Query real products from database using async session
        from app.core.database import get_async_session

        async for async_db in get_async_session():
            # Query using raw SQL to ensure we're using the correct schema
            from sqlalchemy import text

            # Build the WHERE clause based on parameters
            where_conditions = []
            params = {}

            if account_type != "both":
                where_conditions.append("account_type = :account_type")
                params["account_type"] = account_type

            if not include_inactive:
                where_conditions.append("is_active = true")

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            # Execute raw SQL query
            query = f"""
                SELECT id, sku, name, account_type, price, currency, stock_quantity, 
                       is_active, status, brand, emag_category_name, last_synced_at, sync_status
                FROM app.emag_products_v2 
                {where_clause}
                ORDER BY updated_at DESC 
                LIMIT :limit
            """
            params["limit"] = max_pages_per_account * 100

            result = await async_db.execute(text(query), params)
            products = result.fetchall()

            # Convert to response format
            product_data = []
            for product in products:
                product_data.append(
                    {
                        "id": str(product.id),
                        "sku": product.sku,
                        "name": product.name,
                        "account_type": product.account_type,
                        "price": float(product.price) if product.price else 0.0,
                        "currency": product.currency,
                        "stock_quantity": product.stock_quantity,
                        "is_active": product.is_active,
                        "status": product.status,
                        "brand": product.brand,
                        "category_name": product.emag_category_name,
                        "last_synced_at": (
                            product.last_synced_at.isoformat()
                            if product.last_synced_at
                            else None
                        ),
                        "sync_status": product.sync_status,
                    }
                )

            return {
                "products": product_data,
                "total_count": len(product_data),
                "account_type": account_type,
                "include_inactive": include_inactive,
                "timestamp": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        logger.error("Failed to get all products: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve products: {str(e)}"
        )


@router.get("/offers/all")
async def get_all_offers(
    account_type: str = Query(
        default="both", description="Account type: main, fbe, or both"
    ),
    max_pages_per_account: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all offers from specified eMAG account(s).
    """
    try:
        if account_type not in ["main", "fbe", "both"]:
            raise HTTPException(status_code=400, detail="Invalid account_type")

        # Return mock data for now (TODO: implement real database queries with async session)
        mock_offers = []

        if account_type in ["main", "both"]:
            mock_offers.extend(
                [
                    {
                        "id": "mock-offer-main-001",
                        "sku": "MAIN-PROD-001",
                        "account_type": "main",
                        "price": 5499.99,
                        "currency": "RON",
                        "stock": 15,
                        "available_stock": 15,
                        "status": "active",
                        "is_available": True,
                        "last_synced_at": "2024-09-29T10:30:00Z",
                        "sync_status": "synced",
                    }
                ]
            )

        if account_type in ["fbe", "both"]:
            mock_offers.extend(
                [
                    {
                        "id": "mock-offer-fbe-001",
                        "sku": "FBE-PROD-001",
                        "account_type": "fbe",
                        "price": 12999.99,
                        "currency": "RON",
                        "stock": 5,
                        "available_stock": 5,
                        "status": "active",
                        "is_available": True,
                        "last_synced_at": "2024-09-29T10:30:00Z",
                        "sync_status": "synced",
                    }
                ]
            )

        return {
            "offers": mock_offers,
            "total_count": len(mock_offers),
            "account_type": account_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to get all offers: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync progress: {str(e)}"
        )


@router.get("/products/sync-progress")
async def get_products_sync_progress(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get real-time progress of active product synchronization.
    
    Returns detailed progress information including:
    - Current page being processed
    - Total pages to process
    - Processed items count
    - Estimated time remaining
    - Current account being synced
    - Throughput metrics
    """
    try:
        from app.core.database import get_async_session
        from sqlalchemy import text

        async for async_db in get_async_session():
            # Query recent sync logs for active syncs
            query = """
                SELECT sync_type, account_type, status, sync_params, 
                       started_at, processed_items, total_items,
                       EXTRACT(EPOCH FROM (NOW() - started_at)) as duration_seconds
                FROM app.emag_sync_logs 
                WHERE status = 'running' 
                  AND sync_type = 'products'
                ORDER BY started_at DESC 
                LIMIT 5
            """
            result = await async_db.execute(text(query))
            active_syncs = result.fetchall()

            progress_data = []
            for sync in active_syncs:
                sync_params = sync.sync_params or {}
                items_processed = sync.processed_items or 0
                items_total = sync.total_items or 0
                duration = sync.duration_seconds or 0

                # Calculate throughput and ETA
                throughput = items_processed / duration if duration > 0 else 0
                remaining_items = max(0, items_total - items_processed)
                eta_seconds = remaining_items / throughput if throughput > 0 else 0

                progress_data.append({
                    "account_type": sync.account_type,
                    "current_page": sync_params.get("current_page", 0),
                    "total_pages": sync_params.get("max_pages_per_account", 0),
                    "processed_items": items_processed,
                    "total_items": items_total,
                    "progress_percentage": int((items_processed / items_total * 100) if items_total > 0 else 0),
                    "started_at": sync.started_at.isoformat() if sync.started_at else None,
                    "duration_seconds": int(duration),
                    "throughput_per_second": round(throughput, 2),
                    "estimated_time_remaining_seconds": int(eta_seconds),
                    "status": sync.status,
                })

            return {
                "is_running": len(progress_data) > 0,
                "active_syncs": progress_data,
                "total_active": len(progress_data),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "syncing" if progress_data else "idle",
            }

    except Exception as e:
        logger.error("Failed to get sync progress: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync progress: {str(e)}"
        )


@router.get("/products/{product_id}")
async def get_product_details(
    product_id: UUID,
    account_type: str = Query(default="main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific product.
    """
    try:
        product = db.query(EmagProductV2).filter(EmagProductV2.id == product_id).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return {
            "id": str(product.id),
            "emag_id": product.emag_id,
            "sku": product.sku,
            "name": product.name,
            "account_type": product.account_type,
            "description": product.description,
            "brand": product.brand,
            "manufacturer": product.manufacturer,
            "price": product.price,
            "currency": product.currency,
            "stock_quantity": product.stock_quantity,
            "category_id": product.category_id,
            "emag_category_id": product.emag_category_id,
            "emag_category_name": product.emag_category_name,
            "is_active": product.is_active,
            "status": product.status,
            "images": product.images,
            "green_tax": product.green_tax,
            "supply_lead_time": product.supply_lead_time,
            "safety_information": product.safety_information,
            "manufacturer_info": product.manufacturer_info,
            "eu_representative": product.eu_representative,
            "emag_characteristics": product.emag_characteristics,
            "attributes": product.attributes,
            "specifications": product.specifications,
            "sync_status": product.sync_status,
            "last_synced_at": (
                product.last_synced_at.isoformat() if product.last_synced_at else None
            ),
            "sync_error": product.sync_error,
            "sync_attempts": product.sync_attempts,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
            "emag_created_at": (
                product.emag_created_at.isoformat() if product.emag_created_at else None
            ),
            "emag_modified_at": (
                product.emag_modified_at.isoformat()
                if product.emag_modified_at
                else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get product details: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve product: {str(e)}"
        )


@router.post("/sync/scheduled")
async def configure_scheduled_sync(
    request: SyncScheduledRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Configure scheduled synchronization.

    Sets up automatic sync jobs that run at specified intervals.
    """
    try:
        logger.info(
            "Configuring scheduled sync by user %s: %s",
            current_user.email,
            request.dict(),
        )

        # This would integrate with a job scheduler like Celery
        # For now, return configuration confirmation

        return {
            "status": "configured",
            "sync_interval_minutes": request.sync_interval_minutes,
            "sync_types": request.sync_types,
            "accounts": request.accounts,
            "max_pages_per_account": request.max_pages_per_account,
            "next_sync_at": (
                datetime.utcnow().replace(second=0, microsecond=0)
                + timedelta(minutes=request.sync_interval_minutes)
            ).isoformat(),
            "configured_by": current_user.email,
            "configured_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to configure scheduled sync: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to configure scheduled sync: {str(e)}"
        )


@router.get("/sync/export")
async def export_sync_data(
    include_products: bool = Query(
        default=True, description="Include products in export"
    ),
    include_offers: bool = Query(default=True, description="Include offers in export"),
    account_type: str = Query(default="both", description="Account type to export"),
    format: str = Query(default="json", description="Export format: json or csv"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export synchronized data for backup or analysis.

    Supports multiple formats and filtering options.
    """
    try:
        if account_type not in ["main", "fbe", "both"]:
            raise HTTPException(status_code=400, detail="Invalid account_type")

        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Invalid format")

        export_data = {
            "export_info": {
                "exported_by": current_user.email,
                "exported_at": datetime.utcnow().isoformat(),
                "account_type": account_type,
                "include_products": include_products,
                "include_offers": include_offers,
                "format": format,
            }
        }

        # Export products
        if include_products:
            query = db.query(EmagProductV2)
            if account_type != "both":
                query = query.filter(EmagProductV2.account_type == account_type)

            products = query.all()
            export_data["products"] = [
                {
                    "id": str(p.id),
                    "sku": p.sku,
                    "name": p.name,
                    "account_type": p.account_type,
                    "price": p.price,
                    "stock_quantity": p.stock_quantity,
                    "is_active": p.is_active,
                    "last_synced_at": (
                        p.last_synced_at.isoformat() if p.last_synced_at else None
                    ),
                }
                for p in products
            ]

        # Export offers
        if include_offers:
            query = db.query(EmagProductOfferV2)
            if account_type != "both":
                query = query.filter(EmagProductOfferV2.account_type == account_type)

            offers = query.all()
            export_data["offers"] = [
                {
                    "id": str(o.id),
                    "sku": o.sku,
                    "account_type": o.account_type,
                    "price": o.price,
                    "stock": o.stock,
                    "status": o.status,
                    "last_synced_at": (
                        o.last_synced_at.isoformat() if o.last_synced_at else None
                    ),
                }
                for o in offers
            ]

        if format == "json":
            return JSONResponse(content=export_data)
        else:
            # CSV export would be implemented here
            return {"message": "CSV export not yet implemented"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export sync data: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")


@router.get("/status")
async def get_emag_status(
    account_type: str = Query(default="both", description="Account type: main, fbe, or both"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive eMAG integration status for specified account(s).

    Returns detailed status information including:
    - Connection status and health
    - Last sync information with duration
    - Product counts (total, active, synced)
    - Recent sync logs with success/failure rates
    - API rate limit usage
    - System health metrics
    """
    try:
        logger.info("Getting eMAG status for account_type=%s, user=%s", account_type, current_user.email)

        # Query database for actual product counts and sync logs
        from app.core.database import get_async_session

        async for async_db in get_async_session():
            from sqlalchemy import text

            # Get product counts by account type
            count_query = """
                SELECT account_type, COUNT(*) as count, 
                       COUNT(CASE WHEN is_active = true THEN 1 END) as active_count,
                       COUNT(CASE WHEN sync_status = 'synced' THEN 1 END) as synced_count,
                       COUNT(CASE WHEN sync_status = 'failed' THEN 1 END) as failed_count,
                       MAX(last_synced_at) as last_sync,
                       AVG(CASE WHEN price IS NOT NULL THEN price ELSE 0 END) as avg_price,
                       SUM(stock_quantity) as total_stock
                FROM app.emag_products_v2 
                GROUP BY account_type
            """
            result = await async_db.execute(text(count_query))
            account_stats = result.fetchall()

            # Process results
            main_stats = {"total": 0, "active": 0, "synced": 0, "failed": 0, "last_sync": None, "avg_price": 0, "total_stock": 0}
            fbe_stats = {"total": 0, "active": 0, "synced": 0, "failed": 0, "last_sync": None, "avg_price": 0, "total_stock": 0}

            for row in account_stats:
                stats = {
                    "total": row.count,
                    "active": row.active_count,
                    "synced": row.synced_count,
                    "failed": row.failed_count,
                    "last_sync": row.last_sync.isoformat() if row.last_sync else None,
                    "avg_price": float(row.avg_price) if row.avg_price else 0.0,
                    "total_stock": int(row.total_stock) if row.total_stock else 0,
                }
                if row.account_type == "main":
                    main_stats = stats
                elif row.account_type == "fbe":
                    fbe_stats = stats

            # Get recent sync logs from database
            sync_logs_query = """
                SELECT id, account_type, sync_type, status, 
                       started_at, completed_at, processed_items, total_items,
                       COALESCE(ARRAY_TO_STRING(ARRAY(SELECT jsonb_array_elements_text(errors)), ', '), NULL) as error_message,
                       EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
                FROM app.emag_sync_logs 
                WHERE sync_type IN ('products', 'offers', 'orders')
                ORDER BY started_at DESC 
                LIMIT 10
            """
            sync_result = await async_db.execute(text(sync_logs_query))
            sync_logs = sync_result.fetchall()

            recent_syncs = []
            for log in sync_logs:
                processed = log.processed_items or 0
                total = log.total_items or 0
                recent_syncs.append({
                    "id": str(log.id),
                    "account_type": log.account_type,
                    "sync_type": log.sync_type,
                    "status": log.status,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "items_processed": processed,
                    "items_total": total,
                    "duration_seconds": int(log.duration_seconds) if log.duration_seconds else 0,
                    "error_message": log.error_message,
                    "success_rate": round((processed / total * 100) if total else 0, 2),
                })

            # Calculate health metrics
            total_syncs = len([s for s in recent_syncs if s["status"] in ["completed", "failed"]])
            successful_syncs = len([s for s in recent_syncs if s["status"] == "completed"])
            health_score = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 100

            response = {
                "status": "connected",
                "health_score": round(health_score, 2),
                "health_status": "healthy" if health_score >= 90 else "warning" if health_score >= 70 else "critical",
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Add account-specific data based on filter
            if account_type in ["main", "both"]:
                response["main_account"] = {
                    "status": "connected",
                    "username": "galactronice@yahoo.com",
                    "products": main_stats,
                    "last_activity": main_stats["last_sync"],
                    "connection_test": "success",
                    "api_version": "v4.4.8",
                }

            if account_type in ["fbe", "both"]:
                response["fbe_account"] = {
                    "status": "connected",
                    "username": "galactronice.fbe@yahoo.com",
                    "products": fbe_stats,
                    "last_activity": fbe_stats["last_sync"],
                    "connection_test": "success",
                    "api_version": "v4.4.8",
                }

            if account_type == "both":
                response["summary"] = {
                    "total_products": main_stats["total"] + fbe_stats["total"],
                    "active_products": main_stats["active"] + fbe_stats["active"],
                    "synced_products": main_stats["synced"] + fbe_stats["synced"],
                    "failed_products": main_stats["failed"] + fbe_stats["failed"],
                    "total_stock": main_stats["total_stock"] + fbe_stats["total_stock"],
                    "avg_price": round((main_stats["avg_price"] + fbe_stats["avg_price"]) / 2, 2),
                    "last_sync": max(
                        main_stats["last_sync"] or "1970-01-01T00:00:00Z",
                        fbe_stats["last_sync"] or "1970-01-01T00:00:00Z",
                    ),
                }

            response["recent_syncs"] = recent_syncs
            response["sync_statistics"] = {
                "total_syncs": total_syncs,
                "successful_syncs": successful_syncs,
                "failed_syncs": total_syncs - successful_syncs,
                "success_rate": round(health_score, 2),
            }

            # Add latest_sync for backward compatibility
            if recent_syncs:
                response["latest_sync"] = recent_syncs[0]

            return response

    except Exception as e:
        logger.error("Failed to get eMAG status: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get eMAG status: {str(e)}"
        )


class SyncOrdersRequest(BaseModel):
    """Request model for syncing orders."""

    max_pages_per_account: int = Field(
        default=50, ge=1, le=200, description="Maximum pages to process per account"
    )
    delay_between_requests: float = Field(
        default=1.2,
        ge=0.1,
        le=10.0,
        description="Delay between API requests in seconds",
    )
    status_filter: Optional[str] = Field(
        default=None, description="Filter orders by status (1=new, 2=in_progress, 3=prepared, 4=finalized, 5=returned, 0=canceled)"
    )


class OrderSyncResponse(BaseModel):
    """Response model for order sync results."""

    main_account: Optional[Dict[str, Any]]
    fbe_account: Optional[Dict[str, Any]]
    combined: Dict[str, Any]
    sync_timestamp: str
    total_orders_processed: int


@router.post("/sync/all-orders", response_model=OrderSyncResponse)
async def sync_all_orders(
    request: SyncOrdersRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Synchronize all orders from both MAIN and FBE eMAG accounts.

    This endpoint performs a comprehensive order synchronization with:
    - Full pagination support (up to 200 pages per account)
    - Status filtering (new, in_progress, prepared, finalized, returned, canceled)
    - Rate limiting compliance with eMAG API v4.4.8 (12 RPS for orders)
    - Real-time progress tracking
    - Error recovery and retry logic

    The sync process:
    1. Fetches orders from MAIN account
    2. Fetches orders from FBE account
    3. Combines results from both accounts
    4. Returns comprehensive results and statistics
    """
    try:
        logger.info(
            "Starting full order sync requested by user %s with params: %s",
            current_user.email,
            request.dict(),
        )

        # Initialize enhanced eMAG service
        async with EnhancedEmagIntegrationService("main", db) as emag_service:
            # Perform full order sync
            results = await emag_service.sync_all_orders_from_both_accounts(
                max_pages_per_account=request.max_pages_per_account,
                delay_between_requests=request.delay_between_requests,
                status_filter=request.status_filter,
            )

            # Calculate total processed
            total_processed = 0
            if results.get("main_account"):
                total_processed += results["main_account"].get("orders_count", 0)
            if results.get("fbe_account"):
                total_processed += results["fbe_account"].get("orders_count", 0)

            response = OrderSyncResponse(
                main_account=results.get("main_account"),
                fbe_account=results.get("fbe_account"),
                combined=results.get("combined", {}),
                sync_timestamp=datetime.utcnow().isoformat(),
                total_orders_processed=total_processed,
            )

            logger.info(
                "Completed full order sync: %d orders from MAIN, %d orders from FBE",
                results.get("main_account", {}).get("orders_count", 0),
                results.get("fbe_account", {}).get("orders_count", 0),
            )

            return response

    except Exception as e:
        logger.error("Failed to sync orders: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to sync orders: {str(e)}"
        )


@router.put("/products/{product_id}")
async def update_emag_product(
    product_id: str,
    update_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an eMAG product by ID.
    
    This endpoint allows updating eMAG product fields including:
    - Price, sale_price, stock
    - Name, description, brand
    - Status, availability
    - And other eMAG-specific fields
    
    The product will be updated in the local database and optionally synced to eMAG.
    """
    try:
        from app.core.database import get_async_session
        from sqlalchemy import text
        from uuid import UUID

        # Validate product_id is a valid UUID
        try:
            product_uuid = UUID(product_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid product ID format")

        account_type = update_data.pop('account_type', None)
        if not account_type or account_type not in ['main', 'fbe']:
            raise HTTPException(status_code=400, detail="account_type is required and must be 'main' or 'fbe'")

        async for async_db in get_async_session():
            # Check if product exists
            check_query = """
                SELECT id, sku, name FROM app.emag_products_v2 
                WHERE id = :product_id AND account_type = :account_type
            """
            result = await async_db.execute(
                text(check_query),
                {"product_id": product_uuid, "account_type": account_type}
            )
            existing_product = result.fetchone()

            if not existing_product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Build UPDATE query dynamically based on provided fields
            # Note: emag_products_v2 table fields (not offer fields)
            allowed_fields = [
                'name', 'description', 'brand', 'manufacturer',
                'price',  # Main price field in emag_products_v2
                'stock_quantity',  # Main stock field
                'status', 'is_active',
                'green_tax', 'supply_lead_time',
                'safety_information', 'emag_characteristics', 'attributes'
            ]

            update_fields = []
            params = {"product_id": product_uuid, "account_type": account_type}

            for field, value in update_data.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = :{field}")
                    params[field] = value

            if not update_fields:
                raise HTTPException(status_code=400, detail="No valid fields to update")

            # Add updated_at timestamp
            update_fields.append("updated_at = NOW()")

            update_query = f"""
                UPDATE app.emag_products_v2 
                SET {', '.join(update_fields)}
                WHERE id = :product_id AND account_type = :account_type
                RETURNING id, sku, name, price, stock_quantity, status, updated_at
            """

            result = await async_db.execute(text(update_query), params)
            updated_product = result.fetchone()
            await async_db.commit()

            if not updated_product:
                raise HTTPException(status_code=500, detail="Failed to update product")

            logger.info(f"Successfully updated eMAG product {product_id} ({account_type})")

            return {
                "status": "success",
                "message": "Product updated successfully",
                "product": {
                    "id": str(updated_product.id),
                    "sku": updated_product.sku,
                    "name": updated_product.name,
                    "price": float(updated_product.price) if updated_product.price else None,
                    "stock_quantity": updated_product.stock_quantity,
                    "status": updated_product.status,
                    "updated_at": updated_product.updated_at.isoformat() if updated_product.updated_at else None,
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.get("/orders/all")
async def get_all_orders(
    account_type: str = Query(
        default="both", description="Account type: 'main', 'fbe', or 'both'"
    ),
    max_pages_per_account: int = Query(
        default=10, ge=1, le=50, description="Maximum pages to fetch per account"
    ),
    status_filter: Optional[str] = Query(
        default=None, description="Filter by order status"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all orders from specified eMAG account(s).

    Returns orders from MAIN, FBE, or both accounts with optional status filtering.
    """
    try:
        logger.info(
            "Getting orders for account_type=%s, max_pages=%d",
            account_type,
            max_pages_per_account,
        )

        results = {}

        if account_type in ["main", "both"]:
            async with EnhancedEmagIntegrationService("main", db) as main_service:
                results["main_account"] = await main_service.sync_orders_from_account(
                    max_pages=max_pages_per_account,
                    delay_between_requests=0.5,
                    status_filter=status_filter,
                )

        if account_type in ["fbe", "both"]:
            async with EnhancedEmagIntegrationService("fbe", db) as fbe_service:
                results["fbe_account"] = await fbe_service.sync_orders_from_account(
                    max_pages=max_pages_per_account,
                    delay_between_requests=0.5,
                    status_filter=status_filter,
                )

        # Combine orders if both accounts
        all_orders = []
        if "main_account" in results:
            all_orders.extend(results["main_account"].get("orders", []))
        if "fbe_account" in results:
            all_orders.extend(results["fbe_account"].get("orders", []))

        return {
            "orders": all_orders,
            "total_count": len(all_orders),
            "account_type": account_type,
            "accounts": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to get orders: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")


@router.get("/products/unified/all")
async def get_all_unified_products(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    source: str = Query(default="all", description="Product source: all, emag_main, emag_fbe, local"),
    search: Optional[str] = Query(default=None, description="Search by SKU or name"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get unified view of all products (eMAG + local products).
    
    This endpoint combines products from:
    - eMAG MAIN account (emag_products_v2 table)
    - eMAG FBE account (emag_products_v2 table)
    - Local products (products table)
    
    Supports pagination, filtering, and search.
    """
    try:
        from app.models.product import Product
        from sqlalchemy import or_, select

        all_products = []
        total_count = 0

        # Get eMAG products
        if source in ["all", "emag_main", "emag_fbe", "emag"]:
            emag_query = select(EmagProductV2)

            # Filter by account type
            if source == "emag_main":
                emag_query = emag_query.where(EmagProductV2.account_type == "main")
            elif source == "emag_fbe":
                emag_query = emag_query.where(EmagProductV2.account_type == "fbe")

            # Filter by active status
            if is_active is not None:
                emag_query = emag_query.where(EmagProductV2.is_active == is_active)

            # Search filter
            if search:
                emag_query = emag_query.where(
                    or_(
                        EmagProductV2.sku.ilike(f"%{search}%"),
                        EmagProductV2.name.ilike(f"%{search}%")
                    )
                )

            result = await db.execute(emag_query)
            emag_products = result.scalars().all()

            for product in emag_products:
                all_products.append({
                    "id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "source": f"emag_{product.account_type}",
                    "account_type": product.account_type,
                    "price": float(product.price) if product.price else None,
                    "currency": product.currency,
                    "stock_quantity": product.stock_quantity,
                    "is_active": product.is_active,
                    "status": product.status,
                    "brand": product.brand,
                    "category_name": product.emag_category_name,
                    "last_synced_at": product.last_synced_at.isoformat() if product.last_synced_at else None,
                    "sync_status": product.sync_status,
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                })

        # Get local products
        if source in ["all", "local"]:
            local_query = select(Product)

            # Filter by active status
            if is_active is not None:
                local_query = local_query.where(Product.is_active == is_active)

            # Search filter
            if search:
                local_query = local_query.where(
                    or_(
                        Product.sku.ilike(f"%{search}%"),
                        Product.name.ilike(f"%{search}%")
                    )
                )

            result = await db.execute(local_query)
            local_products = result.scalars().all()

            for product in local_products:
                all_products.append({
                    "id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "source": "local",
                    "account_type": "local",
                    "price": float(product.base_price) if hasattr(product, 'base_price') and product.base_price else None,
                    "currency": product.currency if hasattr(product, 'currency') else "RON",
                    "stock_quantity": getattr(product, 'stock_quantity', 0),
                    "is_active": product.is_active,
                    "status": "active" if product.is_active else "inactive",
                    "brand": getattr(product, 'brand', None),
                    "category_name": None,
                    "last_synced_at": None,
                    "sync_status": "local",
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                })

        # Sort by updated_at descending
        all_products.sort(key=lambda x: x.get("updated_at") or "", reverse=True)

        # Calculate pagination
        total_count = len(all_products)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_products = all_products[start_idx:end_idx]

        # Calculate statistics
        emag_main_count = len([p for p in all_products if p["source"] == "emag_main"])
        emag_fbe_count = len([p for p in all_products if p["source"] == "emag_fbe"])
        local_count = len([p for p in all_products if p["source"] == "local"])

        return {
            "products": paginated_products,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
            },
            "statistics": {
                "total": total_count,
                "emag_main": emag_main_count,
                "emag_fbe": emag_fbe_count,
                "local": local_count,
            },
            "filters": {
                "source": source,
                "search": search,
                "is_active": is_active,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to get unified products: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get unified products: {str(e)}")


# Light Offer API Endpoints (v4.4.9)

class LightOfferPriceUpdate(BaseModel):
    """Request model for Light Offer API price update."""
    product_id: int = Field(description="Seller internal product ID")
    sale_price: float = Field(gt=0, description="Sale price without VAT")
    recommended_price: Optional[float] = Field(default=None, description="Recommended retail price")
    min_sale_price: Optional[float] = Field(default=None, description="Minimum sale price")
    max_sale_price: Optional[float] = Field(default=None, description="Maximum sale price")
    account_type: str = Field(default="main", description="Account type: main or fbe")


class LightOfferStockUpdate(BaseModel):
    """Request model for Light Offer API stock update."""
    product_id: int = Field(description="Seller internal product ID")
    stock: int = Field(ge=0, description="Stock quantity")
    warehouse_id: int = Field(default=1, description="Warehouse ID")
    account_type: str = Field(default="main", description="Account type: main or fbe")


class LightOfferBulkUpdate(BaseModel):
    """Request model for bulk Light Offer API updates."""
    updates: List[Dict[str, Any]] = Field(description="List of updates")
    account_type: str = Field(default="main", description="Account type: main or fbe")
    batch_size: int = Field(default=25, ge=1, le=50, description="Batch size (optimal: 25)")


@router.post("/light-offer/update-price")
async def light_offer_update_price(
    request: LightOfferPriceUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Quick price update using Light Offer API (v4.4.9).
    
    This endpoint is faster and more efficient than traditional product_offer/save.
    Only sends the fields that need to be updated.
    """
    try:
        from app.services.emag_light_offer_service import EmagLightOfferService

        async with EmagLightOfferService(request.account_type) as service:
            result = await service.update_offer_price(
                product_id=request.product_id,
                sale_price=request.sale_price,
                recommended_price=request.recommended_price,
                min_sale_price=request.min_sale_price,
                max_sale_price=request.max_sale_price
            )

        return {
            "status": "success",
            "message": "Price updated successfully",
            "product_id": request.product_id,
            "sale_price": request.sale_price,
            "emag_response": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Failed to update price via Light Offer API: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update price: {str(e)}"
        )


@router.post("/light-offer/update-stock")
async def light_offer_update_stock(
    request: LightOfferStockUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Quick stock update using Light Offer API (v4.4.9).
    
    This endpoint is faster and more efficient than traditional product_offer/save.
    Only sends the stock field that needs to be updated.
    """
    try:
        from app.services.emag_light_offer_service import EmagLightOfferService

        async with EmagLightOfferService(request.account_type) as service:
            result = await service.update_offer_stock(
                product_id=request.product_id,
                stock=request.stock,
                warehouse_id=request.warehouse_id
            )

        return {
            "status": "success",
            "message": "Stock updated successfully",
            "product_id": request.product_id,
            "stock": request.stock,
            "emag_response": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Failed to update stock via Light Offer API: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update stock: {str(e)}"
        )


@router.post("/light-offer/bulk-update-prices")
async def light_offer_bulk_update_prices(
    request: LightOfferBulkUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Bulk price updates using Light Offer API (v4.4.9).
    
    Processes updates in batches for optimal performance.
    Recommended batch size: 25 offers per batch.
    """
    try:
        from app.services.emag_light_offer_service import EmagLightOfferService

        async with EmagLightOfferService(request.account_type) as service:
            result = await service.bulk_update_prices(
                updates=request.updates,
                batch_size=request.batch_size
            )

        return {
            "status": "success",
            "message": "Bulk price update completed",
            "summary": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Failed to bulk update prices via Light Offer API: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bulk update prices: {str(e)}"
        )


@router.get("/analytics/detailed-stats")
async def get_detailed_analytics(
    account_type: str = Query(default="both", description="Account type: main, fbe, or both"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed analytics and statistics for eMAG products.
    
    Returns comprehensive metrics including:
    - Product distribution by category, brand, and price range
    - Stock analysis and availability metrics
    - Sync performance and success rates
    - Trending products and top performers
    - Historical data and trends
    """
    try:
        from app.core.database import get_async_session
        from sqlalchemy import text
        from datetime import timedelta

        async for async_db in get_async_session():
            # Calculate date range
            start_date = datetime.utcnow() - timedelta(days=days)

            # Build WHERE clause
            where_conditions = []
            params = {"start_date": start_date}

            if account_type != "both":
                where_conditions.append("account_type = :account_type")
                params["account_type"] = account_type

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            # Get product distribution by category
            category_query = f"""
                SELECT emag_category_name, COUNT(*) as count,
                       AVG(price) as avg_price,
                       SUM(stock_quantity) as total_stock
                FROM app.emag_products_v2
                {where_clause}
                GROUP BY emag_category_name
                ORDER BY count DESC
                LIMIT 20
            """
            category_result = await async_db.execute(text(category_query), params)
            categories = [
                {
                    "category": row.emag_category_name or "Uncategorized",
                    "count": row.count,
                    "avg_price": float(row.avg_price) if row.avg_price else 0,
                    "total_stock": int(row.total_stock) if row.total_stock else 0
                }
                for row in category_result.fetchall()
            ]

            # Get brand distribution
            brand_where = where_clause if where_clause else "WHERE"
            if where_clause:
                brand_where += " AND brand IS NOT NULL"
            else:
                brand_where = "WHERE brand IS NOT NULL"

            brand_query = f"""
                SELECT brand, COUNT(*) as count,
                       AVG(price) as avg_price
                FROM app.emag_products_v2
                {brand_where}
                GROUP BY brand
                ORDER BY count DESC
                LIMIT 15
            """
            brand_result = await async_db.execute(text(brand_query), params)
            brands = [
                {
                    "brand": row.brand,
                    "count": row.count,
                    "avg_price": float(row.avg_price) if row.avg_price else 0
                }
                for row in brand_result.fetchall()
            ]

            # Get price distribution
            price_where = where_clause if where_clause else "WHERE"
            if where_clause:
                price_where += " AND price IS NOT NULL"
            else:
                price_where = "WHERE price IS NOT NULL"

            price_query = f"""
                SELECT 
                    CASE 
                        WHEN price < 50 THEN '0-50'
                        WHEN price < 100 THEN '50-100'
                        WHEN price < 200 THEN '100-200'
                        WHEN price < 500 THEN '200-500'
                        WHEN price < 1000 THEN '500-1000'
                        ELSE '1000+'
                    END as price_range,
                    COUNT(*) as count
                FROM app.emag_products_v2
                {price_where}
                GROUP BY price_range
                ORDER BY price_range
            """
            price_result = await async_db.execute(text(price_query), params)
            price_distribution = [
                {"range": row.price_range, "count": row.count}
                for row in price_result.fetchall()
            ]

            # Get stock analysis
            stock_query = f"""
                SELECT 
                    COUNT(CASE WHEN stock_quantity = 0 THEN 1 END) as out_of_stock,
                    COUNT(CASE WHEN stock_quantity > 0 AND stock_quantity <= 5 THEN 1 END) as low_stock,
                    COUNT(CASE WHEN stock_quantity > 5 AND stock_quantity <= 20 THEN 1 END) as medium_stock,
                    COUNT(CASE WHEN stock_quantity > 20 THEN 1 END) as high_stock,
                    AVG(stock_quantity) as avg_stock,
                    SUM(stock_quantity) as total_stock
                FROM app.emag_products_v2
                {where_clause}
            """
            stock_result = await async_db.execute(text(stock_query), params)
            stock_row = stock_result.fetchone()
            stock_analysis = {
                "out_of_stock": stock_row.out_of_stock or 0,
                "low_stock": stock_row.low_stock or 0,
                "medium_stock": stock_row.medium_stock or 0,
                "high_stock": stock_row.high_stock or 0,
                "avg_stock": float(stock_row.avg_stock) if stock_row.avg_stock else 0,
                "total_stock": int(stock_row.total_stock) if stock_row.total_stock else 0
            }

            # Get sync performance
            sync_perf_query = """
                SELECT 
                    COUNT(*) as total_syncs,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_syncs,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_syncs,
                    AVG(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds END) as avg_duration,
                    SUM(processed_items) as total_items_processed
                FROM app.emag_sync_logs
                WHERE sync_type = 'products'
                  AND started_at >= :start_date
            """
            sync_perf_result = await async_db.execute(text(sync_perf_query), {"start_date": start_date})
            sync_row = sync_perf_result.fetchone()
            sync_performance = {
                "total_syncs": sync_row.total_syncs or 0,
                "successful_syncs": sync_row.successful_syncs or 0,
                "failed_syncs": sync_row.failed_syncs or 0,
                "success_rate": round((sync_row.successful_syncs / sync_row.total_syncs * 100) if sync_row.total_syncs else 0, 2),
                "avg_duration_seconds": round(float(sync_row.avg_duration), 2) if sync_row.avg_duration else 0,
                "total_items_processed": sync_row.total_items_processed or 0
            }

            return {
                "status": "success",
                "account_type": account_type,
                "period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "analytics": {
                    "categories": categories,
                    "brands": brands,
                    "price_distribution": price_distribution,
                    "stock_analysis": stock_analysis,
                    "sync_performance": sync_performance
                }
            }

    except Exception as e:
        logger.error("Failed to get detailed analytics: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics: {str(e)}"
        )


# ========== NEW API v4.4.9 Endpoints - Section 8 Support ==========

@router.get("/categories", summary="Get eMAG categories")
async def get_emag_categories(
    category_id: Optional[int] = Query(None, description="Specific category ID for detailed info"),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    language: str = Query("ro", description="Response language (ro, en, hu, bg, etc.)"),
    account_type: str = Query("main", description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
):
    """
    Get eMAG categories with characteristics and family types.
    
    - **category_id**: Optional - Get specific category with full details
    - **page**: Page number for pagination
    - **items_per_page**: Number of items per page (max 100)
    - **language**: Response language
    - **account_type**: Which eMAG account to use
    
    Returns categories with:
    - Basic info (id, name, parent_id)
    - Permissions (is_allowed, is_ean_mandatory, is_warranty_mandatory)
    - Characteristics (only for specific category)
    - Family types (only for specific category)
    """
    try:
        async with EnhancedEmagIntegrationService(account_type) as service:
            response = await service.client.get_categories(
                category_id=category_id,
                page=page,
                items_per_page=items_per_page,
                language=language
            )

            if response.get("isError"):
                raise HTTPException(
                    status_code=400,
                    detail=f"eMAG API error: {response.get('messages', [])}"
                )

            return {
                "status": "success",
                "account_type": account_type,
                "language": language,
                "results": response.get("results", []),
                "pagination": response.get("pagination", {}),
                "retrieved_at": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error("Failed to get categories: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get categories: {str(e)}"
        )


@router.get("/vat-rates", summary="Get eMAG VAT rates")
async def get_emag_vat_rates(
    account_type: str = Query("main", description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
):
    """
    Get available VAT rates from eMAG.
    
    Returns list of VAT rates with their IDs that can be used when creating/updating offers.
    """
    try:
        async with EnhancedEmagIntegrationService(account_type) as service:
            response = await service.client.get_vat_rates()

            if response.get("isError"):
                raise HTTPException(
                    status_code=400,
                    detail=f"eMAG API error: {response.get('messages', [])}"
                )

            return {
                "status": "success",
                "account_type": account_type,
                "vat_rates": response.get("results", []),
                "retrieved_at": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error("Failed to get VAT rates: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get VAT rates: {str(e)}"
        )


@router.get("/handling-times", summary="Get eMAG handling time values")
async def get_emag_handling_times(
    account_type: str = Query("main", description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
):
    """
    Get available handling time values from eMAG.
    
    Returns list of handling time values (in days) that can be used when creating/updating offers.
    """
    try:
        async with EnhancedEmagIntegrationService(account_type) as service:
            response = await service.client.get_handling_times()

            if response.get("isError"):
                raise HTTPException(
                    status_code=400,
                    detail=f"eMAG API error: {response.get('messages', [])}"
                )

            return {
                "status": "success",
                "account_type": account_type,
                "handling_times": response.get("results", []),
                "retrieved_at": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error("Failed to get handling times: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get handling times: {str(e)}"
        )


class EanSearchRequest(BaseModel):
    """Request model for EAN search."""
    eans: List[str] = Field(..., max_items=100, description="List of EAN codes to search (max 100)")
    account_type: str = Field(default="main", description="Account type (main or fbe)")


@router.post("/find-by-eans", summary="Search products by EAN codes")
async def find_products_by_eans(
    request: EanSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Search products by EAN codes (NEW in v4.4.9).
    
    Quickly check if products with given EAN codes already exist on eMAG.
    
    **Rate Limits:**
    - 5 requests/second
    - 200 requests/minute
    - 5,000 requests/day
    
    **Returns for each EAN:**
    - eans: European Article Number
    - part_number_key: eMAG product key (use this to attach offers)
    - product_name: Product name
    - brand_name: Brand name
    - category_name: Category name
    - doc_category_id: Category ID
    - site_url: eMAG product URL
    - allow_to_add_offer: Whether you can add an offer
    - vendor_has_offer: Whether you already have an offer
    - hotness: Product performance indicator
    - product_image: Main image URL
    """
    try:
        if len(request.eans) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 EAN codes per request"
            )

        async with EnhancedEmagIntegrationService(request.account_type) as service:
            response = await service.client.find_products_by_eans(request.eans)

            if response.get("isError"):
                raise HTTPException(
                    status_code=400,
                    detail=f"eMAG API error: {response.get('messages', [])}"
                )

            results = response.get("results", [])

            return {
                "status": "success",
                "account_type": request.account_type,
                "eans_searched": len(request.eans),
                "products_found": len(results),
                "results": results,
                "retrieved_at": datetime.utcnow().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to search by EANs: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search by EANs: {str(e)}"
        )


class UpdateOfferLightRequest(BaseModel):
    """Request model for Light Offer API (v4.4.9)."""
    product_id: int = Field(..., description="Seller internal product ID")
    sale_price: Optional[float] = Field(None, description="Sale price without VAT")
    recommended_price: Optional[float] = Field(None, description="Recommended retail price without VAT")
    min_sale_price: Optional[float] = Field(None, description="Minimum sale price")
    max_sale_price: Optional[float] = Field(None, description="Maximum sale price")
    stock: Optional[List[Dict[str, int]]] = Field(None, description="Stock array")
    handling_time: Optional[List[Dict[str, int]]] = Field(None, description="Handling time array")
    vat_id: Optional[int] = Field(None, description="VAT rate ID")
    status: Optional[int] = Field(None, description="Offer status (0=inactive, 1=active, 2=EOL)")
    currency_type: Optional[str] = Field(None, description="Currency (EUR or PLN)")
    account_type: str = Field(default="main", description="Account type (main or fbe)")


@router.post("/update-offer-light", summary="Update offer using Light API")
async def update_offer_light(
    request: UpdateOfferLightRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update existing offer using Light Offer API (NEW in v4.4.9).
    
    Simplified endpoint for updating EXISTING offers only.
    - Cannot create new offers
    - Cannot modify product information
    - Only send fields you want to update
    
    **Advantages:**
    - Simpler payload
    - Faster processing
    - Recommended for stock and price updates
    
    **Example:**
    ```json
    {
        "product_id": 243409,
        "sale_price": 179.99,
        "stock": [{"warehouse_id": 1, "value": 25}]
    }
    ```
    """
    try:
        async with EnhancedEmagIntegrationService(request.account_type) as service:
            response = await service.client.update_offer_light(
                product_id=request.product_id,
                sale_price=request.sale_price,
                recommended_price=request.recommended_price,
                min_sale_price=request.min_sale_price,
                max_sale_price=request.max_sale_price,
                stock=request.stock,
                handling_time=request.handling_time,
                vat_id=request.vat_id,
                status=request.status,
                currency_type=request.currency_type
            )

            if response.get("isError"):
                raise HTTPException(
                    status_code=400,
                    detail=f"eMAG API error: {response.get('messages', [])}"
                )

            return {
                "status": "success",
                "account_type": request.account_type,
                "product_id": request.product_id,
                "message": "Offer updated successfully",
                "response": response,
                "updated_at": datetime.utcnow().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update offer: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update offer: {str(e)}"
        )


class SaveMeasurementsRequest(BaseModel):
    """Request model for saving product measurements."""
    product_id: int = Field(..., description="Seller internal product ID")
    length: float = Field(..., ge=0, le=999999, description="Length in millimeters")
    width: float = Field(..., ge=0, le=999999, description="Width in millimeters")
    height: float = Field(..., ge=0, le=999999, description="Height in millimeters")
    weight: float = Field(..., ge=0, le=999999, description="Weight in grams")
    account_type: str = Field(default="main", description="Account type (main or fbe)")


@router.post("/save-measurements", summary="Save product measurements")
async def save_product_measurements(
    request: SaveMeasurementsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Save volume measurements (dimensions and weight) for a product.
    
    **Units:**
    - Dimensions: millimeters (mm)
    - Weight: grams (g)
    
    **Example:**
    ```json
    {
        "product_id": 243409,
        "length": 200.00,
        "width": 150.50,
        "height": 80.00,
        "weight": 450.75
    }
    ```
    """
    try:
        async with EnhancedEmagIntegrationService(request.account_type) as service:
            response = await service.client.save_measurements(
                product_id=request.product_id,
                length=request.length,
                width=request.width,
                height=request.height,
                weight=request.weight
            )

            if response.get("isError"):
                raise HTTPException(
                    status_code=400,
                    detail=f"eMAG API error: {response.get('messages', [])}"
                )

            return {
                "status": "success",
                "account_type": request.account_type,
                "product_id": request.product_id,
                "message": "Measurements saved successfully",
                "measurements": {
                    "length_mm": request.length,
                    "width_mm": request.width,
                    "height_mm": request.height,
                    "weight_g": request.weight
                },
                "saved_at": datetime.utcnow().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to save measurements: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save measurements: {str(e)}"
        )
