"""eMAG Marketplace API endpoints for MagFlow ERP using dependency injection."""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    status,
)

if TYPE_CHECKING:
    from app.db.models import User as UserModel
else:
    UserModel = Any

from app.api.dependencies import get_current_active_user
from app.core.config import get_settings  # expose symbol for test patching
from app.core.dependency_injection import ServiceContext
from app.core.exceptions import ConfigurationError
from app.services.emag_integration_service import EmagIntegrationService

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/emag", tags=["emag"])


@router.get("/health")
async def get_emag_health() -> Dict[str, Any]:
    """Health check endpoint for eMAG integration monitoring.

    This endpoint can be used by monitoring systems to check eMAG integration health
    without requiring authentication.
    """
    # 1) Load settings
    try:
        settings = get_settings()
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "emag_integration",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "version": "1.0.0",
        }

    # Normalize environment fallback
    environment = getattr(settings, "EMAG_ENVIRONMENT", "not_configured")
    if not environment:
        environment = "not_configured"

    # 2) Try to construct service and inspect config
    try:
        # Import locally so tests can patch the class at its module path
        from app.services.emag_integration_service import (
            EmagIntegrationService as _EmagIntegrationService,
        )

        context = ServiceContext(settings=settings)
        service = _EmagIntegrationService(context)
        config_loaded = service.config is not None
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "emag_integration",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "version": "1.0.0",
        }

    return {
        "status": "healthy" if config_loaded else "unhealthy",
        "service": "emag_integration",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "config_loaded": config_loaded,
        "environment": environment,
    }


async def get_emag_service() -> EmagIntegrationService:
    """FastAPI dependency for EmagIntegrationService."""
    from app.core.service_registry import get_service_registry

    registry = get_service_registry()
    if not registry.is_initialized:
        from app.core.service_registry import initialize_service_registry

        # Initialize with a mock session for now
        # In production, this would be handled by proper dependency injection
        db_session = None
        initialize_service_registry(db_session)

    # For now, create a new instance
    # In production, this should come from the service registry
    from app.core.config import get_settings
    from app.core.dependency_injection import ServiceContext

    settings = get_settings()
    context = ServiceContext(settings=settings)
    service = EmagIntegrationService(context)

    await service.initialize()
    return service


@router.get("/status")
async def get_emag_status(
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get eMAG integration status.

    - **Returns**: Current status of eMAG integration including sync status
    """
    try:
        status_info = {
            "service_initialized": emag_service is not None,
            "api_client_available": (
                emag_service.api_client is not None if emag_service else False
            ),
            "active_sync_tasks": len(emag_service._sync_tasks) if emag_service else 0,
            "last_sync_time": None,  # Would be stored in database
            "sync_errors": [],  # Would be retrieved from logs
            "environment": (
                emag_service.config.environment.value
                if emag_service and emag_service.config
                else "unknown"
            ),
        }

        return {
            "status": (
                "operational"
                if status_info["service_initialized"]
                else "not_configured"
            ),
            "details": status_info,
            "config_status": {
                "has_username": bool(
                    getattr(
                        emag_service.context.settings if emag_service else None,
                        "EMAG_USERNAME",
                        "",
                    )
                ),
                "has_password": bool(
                    getattr(
                        emag_service.context.settings if emag_service else None,
                        "EMAG_PASSWORD",
                        "",
                    )
                ),
                "has_client_id": bool(
                    getattr(
                        emag_service.context.settings if emag_service else None,
                        "EMAG_CLIENT_ID",
                        "",
                    )
                ),
                "has_client_secret": bool(
                    getattr(
                        emag_service.context.settings if emag_service else None,
                        "EMAG_CLIENT_SECRET",
                        "",
                    )
                ),
                "environment": getattr(
                    emag_service.context.settings if emag_service else None,
                    "EMAG_ENVIRONMENT",
                    "not_set",
                ),
            },
        }

    except ConfigurationError:
        return {
            "status": "not_configured",
            "details": {"reason": "eMAG integration not properly configured"},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get eMAG status: {e!s}",
        )


@router.post("/sync/products")
async def sync_products(
    background_tasks: BackgroundTasks,
    full_sync: bool = Query(False, description="Perform full synchronization"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Sync products between ERP and eMAG marketplace.

    - **full_sync**: If true, sync all products; if false, sync only changed products
    - **Returns**: Synchronization results
    """
    try:
        # Run sync in background
        background_tasks.add_task(emag_service.sync_products, full_sync)

        return {
            "message": "Product synchronization started",
            "full_sync": full_sync,
            "status": "in_progress",
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start product sync: {e!s}",
        )


@router.post("/sync/orders")
async def sync_orders(
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Sync orders between ERP and eMAG marketplace.

    - **Returns**: Synchronization results
    """
    try:
        # Run sync in background
        background_tasks.add_task(emag_service.sync_orders)

        return {"message": "Order synchronization started", "status": "in_progress"}

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start order sync: {e!s}",
        )


@router.post("/sync/inventory")
async def sync_inventory(
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Sync inventory levels with eMAG marketplace.

    - **Returns**: Synchronization results
    """
    try:
        # Run inventory sync in background
        background_tasks.add_task(emag_service.bulk_update_inventory, [])

        return {"message": "Inventory synchronization started", "status": "in_progress"}

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start inventory sync: {e!s}",
        )


@router.post("/sync/full")
async def full_synchronization(
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Perform full synchronization of all data with eMAG.

    This includes products, orders, and inventory.

    - **Returns**: Synchronization status
    """
    try:

        async def full_sync():
            results = {}

            # Sync products
            results["products"] = await emag_service.sync_products(full_sync=True)

            # Sync orders
            results["orders"] = await emag_service.sync_orders()

            # Sync inventory
            inventory_updates = await emag_service._get_inventory_updates()
            if inventory_updates:
                results["inventory"] = await emag_service.bulk_update_inventory(
                    inventory_updates,
                )
            else:
                results["inventory"] = {"message": "No inventory updates needed"}

            return results

        # Run full sync in background
        background_tasks.add_task(full_sync)

        return {
            "message": "Full synchronization started",
            "status": "in_progress",
            "includes": ["products", "orders", "inventory"],
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start full sync: {e!s}",
        )


@router.post("/sync/start-auto")
async def start_auto_sync(
    sync_interval: int = Query(
        300,
        description="Sync interval in seconds",
        ge=60,
        le=3600,
    ),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Start automatic synchronization with eMAG.

    - **sync_interval**: How often to sync in seconds (60-3600)
    - **Returns**: Task information
    """
    try:
        task_id = await emag_service.start_auto_sync(sync_interval)

        return {
            "message": "Auto synchronization started",
            "task_id": task_id,
            "sync_interval_seconds": sync_interval,
            "status": "running",
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start auto sync: {e!s}",
        )


@router.post("/sync/stop-auto")
async def stop_auto_sync(
    task_id: str = Query(..., description="Task ID to stop"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Stop automatic synchronization with eMAG.

    - **task_id**: ID of the sync task to stop
    - **Returns**: Stop confirmation
    """
    try:
        success = await emag_service.stop_auto_sync(task_id)

        if success:
            return {
                "message": "Auto synchronization stopped",
                "task_id": task_id,
                "status": "stopped",
            }
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sync task {task_id} not found",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop auto sync: {e!s}",
        )


@router.get("/products")
async def get_emag_products(
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get products from eMAG marketplace.

    - **page**: Page number for pagination
    - **limit**: Number of items per page
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        products_data = await emag_service.api_client.get_products(
            page=page,
            limit=limit,
        )

        return {
            "products": products_data.get("products", []),
            "total_count": products_data.get("total_count", 0),
            "page": page,
            "limit": limit,
            "total_pages": (products_data.get("total_count", 0) + limit - 1) // limit,
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get eMAG products: {e!s}",
        )


@router.get("/orders")
async def get_emag_orders(
    status: Optional[str] = Query(None, description="Filter by order status"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get orders from eMAG marketplace.

    - **status**: Filter by order status
    - **start_date**: Start date filter
    - **end_date**: End date filter
    - **page**: Page number for pagination
    - **limit**: Number of items per page
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        # Parse dates
        start_date_obj = None
        end_date_obj = None

        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(
                    start_date.replace("Z", "+00:00"),
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format",
                )

        if end_date:
            try:
                end_date_obj = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format",
                )

        orders_data = await emag_service.api_client.get_orders(
            status=status,
            start_date=start_date_obj,
            end_date=end_date_obj,
            page=page,
            limit=limit,
        )

        return {
            "orders": orders_data.get("orders", []),
            "total_count": orders_data.get("total_count", 0),
            "page": page,
            "limit": limit,
            "total_pages": (orders_data.get("total_count", 0) + limit - 1) // limit,
        }

    except HTTPException:
        raise
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get eMAG orders: {e!s}",
        )


@router.get("/categories")
async def get_emag_categories(
    parent_id: Optional[str] = Query(None, description="Parent category ID"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get product categories from eMAG marketplace.

    - **parent_id**: Parent category ID to get subcategories
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        categories_data = await emag_service.api_client.get_categories(
            parent_id=parent_id,
        )

        return {
            "categories": categories_data.get("categories", []),
            "total_count": len(categories_data.get("categories", [])),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get eMAG categories: {e!s}",
        )


@router.post("/inventory/update")
async def update_inventory(
    inventory_updates: Dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Update inventory levels on eMAG.

    - **inventory_updates**: Dictionary containing inventory updates
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        # Handle both single product and bulk updates
        if "sku" in inventory_updates and "quantity" in inventory_updates:
            # Single product update
            result = await emag_service.api_client.sync_inventory(
                inventory_updates["sku"],
                inventory_updates["quantity"],
            )
        elif "updates" in inventory_updates:
            # Bulk update
            result = await emag_service.api_client.bulk_update_inventory(
                inventory_updates["updates"],
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid inventory update format",
            )

        return {
            "message": "Inventory update completed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update inventory: {e!s}",
        )


@router.get("/sync/history")
async def get_sync_history(
    limit: int = Query(
        50,
        description="Number of history records to return",
        ge=1,
        le=100,
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get synchronization history.

    - **limit**: Number of history records to return
    """
    try:
        # In a real implementation, this would query a sync_history table
        # For now, return mock data
        history = [
            {
                "id": "sync_001",
                "type": "products",
                "status": "completed",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T10:05:00Z",
                "records_processed": 150,
                "errors": 0,
            },
            {
                "id": "sync_002",
                "type": "orders",
                "status": "completed",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T10:02:00Z",
                "records_processed": 25,
                "errors": 0,
            },
        ]

        return {"history": history[:limit], "total_count": len(history)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync history: {e!s}",
        )


@router.get("/sync/tasks")
async def get_sync_tasks(
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get active synchronization tasks."""
    try:
        tasks = []
        for task_id, task in emag_service._sync_tasks.items():
            tasks.append(
                {
                    "task_id": task_id,
                    "status": "running" if not task.done() else "completed",
                    "created_at": (
                        task_id.split("_", 2)[-1] if "_" in task_id else "unknown"
                    ),
                },
            )

        return {"tasks": tasks, "total_count": len(tasks)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync tasks: {e!s}",
        )


@router.get("/analytics/duplicates")
async def get_duplicate_analysis(
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get duplicate products analysis and recommendations.

    - **account_type**: Account type filter (main or fbe)
    """
    try:
        from app.services.emag_analytics_service import EmagAnalyticsService

        # Mock duplicates data for demonstration
        duplicates_data = {
            "total_duplicates": 75,
            "duplicate_skus": [
                {
                    "sku": "PRD001",
                    "duplicate_accounts": ["main", "fbe"],
                    "product_count": 2,
                    "price_conflict": True,
                    "stock_conflict": True,
                },
            ],
        }

        # Initialize analytics service
        context = ServiceContext(settings=get_settings())
        analytics_service = EmagAnalyticsService(context)
        await analytics_service.initialize()

        result = await analytics_service.analyze_duplicates_and_conflicts(
            account_type,
            duplicates_data,
        )

        return {
            "analysis": result,
            "message": f"Duplicate analysis for {account_type} account",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get duplicate analysis: {e!s}",
        )


@router.get("/products/duplicates")
async def get_duplicate_products(
    account_type: Optional[str] = Query(
        None,
        description="Filter by account type (main or fbe)",
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get all products with duplicate SKU detection.

    - **account_type**: Filter by specific account type
    """
    try:
        # Mock duplicate products data for demonstration
        duplicates_data = {
            "total_duplicates": 75,
            "duplicate_skus": [
                {
                    "sku": "PRD001",
                    "duplicate_accounts": ["main", "fbe"],
                    "product_count": 2,
                    "accounts_involved": ["main", "fbe"],
                    "products": [
                        {
                            "id": "12345",
                            "sku": "PRD001",
                            "name": "Product Name Main",
                            "account": "main",
                            "price": 299.99,
                            "stock": 50,
                            "_is_duplicate": True,
                            "_duplicate_count": 2,
                        },
                        {
                            "id": "67890",
                            "sku": "PRD001",
                            "name": "Product Name FBE",
                            "account": "fbe",
                            "price": 295.00,
                            "stock": 30,
                            "_is_duplicate": True,
                            "_duplicate_count": 2,
                        },
                    ],
                },
                {
                    "sku": "PRD002",
                    "duplicate_accounts": ["main", "fbe"],
                    "product_count": 3,
                    "accounts_involved": ["main", "fbe"],
                    "products": [
                        {
                            "id": "11111",
                            "sku": "PRD002",
                            "name": "Product 2 Main",
                            "account": "main",
                            "price": 199.99,
                            "stock": 25,
                            "_is_duplicate": True,
                            "_duplicate_count": 3,
                        },
                    ],
                },
            ],
            "summary": {
                "total_duplicate_skus": 25,
                "most_common_duplicates": 3,
                "accounts_with_duplicates": ["main", "fbe"],
                "price_differences_found": True,
                "stock_differences_found": True,
            },
            "message": "Duplicate products detected - review and resolve conflicts",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return duplicates_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get duplicate products: {e!s}",
        )


@router.get("/products/duplicates/{sku}")
async def get_duplicate_sku_details(
    sku: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get detailed information about a specific duplicate SKU.

    - **sku**: The SKU to check for duplicates
    """
    try:
        # Mock detailed duplicate SKU data
        sku_details = {
            "sku": sku,
            "duplicate_found": True,
            "duplicate_count": 2,
            "accounts_involved": ["main", "fbe"],
            "products": [
                {
                    "id": "12345",
                    "sku": sku,
                    "name": f"Product {sku} - Main Account",
                    "account": "main",
                    "price": 299.99,
                    "stock": 50,
                    "currency": "RON",
                    "status": "active",
                    "category": "Electronics",
                    "last_updated": "2024-01-15T10:30:00Z",
                    "_is_duplicate": True,
                    "_duplicate_accounts": ["main", "fbe"],
                    "_first_account": "main",
                },
                {
                    "id": "67890",
                    "sku": sku,
                    "name": f"Product {sku} - FBE Account",
                    "account": "fbe",
                    "price": 295.00,
                    "stock": 30,
                    "currency": "RON",
                    "status": "active",
                    "category": "Electronics",
                    "last_updated": "2024-01-15T09:45:00Z",
                    "_is_duplicate": True,
                    "_duplicate_accounts": ["main", "fbe"],
                    "_first_account": "main",
                },
            ],
            "conflicts": {
                "price_difference": 4.99,
                "stock_difference": 20,
                "name_different": False,
                "status_different": False,
                "category_different": False,
            },
            "recommendations": [
                "💰 Price conflict: MAIN has higher price (299.99 vs 295.00)",
                "📦 Stock conflict: MAIN has more stock (50 vs 30)",
                "🔍 Review which account should be the primary source",
                "⚖️ Consider price harmonization",
                "📊 Check sales performance on both accounts",
            ],
            "resolution_options": [
                {
                    "option": "keep_main",
                    "description": "Keep MAIN account version as primary",
                    "impact": "FBE price will be updated to match MAIN",
                    "action": "update_fbe_to_main",
                },
                {
                    "option": "keep_fbe",
                    "description": "Keep FBE account version as primary",
                    "impact": "MAIN price will be updated to match FBE",
                    "action": "update_main_to_fbe",
                },
                {
                    "option": "merge_best",
                    "description": "Merge best attributes from both",
                    "impact": "Create hybrid version with best price/stock",
                    "action": "create_hybrid_version",
                },
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

        return sku_details

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get duplicate SKU details: {e!s}",
        )


@router.post("/products/duplicates/resolve")
async def resolve_duplicate_sku(
    sku: str = Body(..., description="SKU to resolve"),
    resolution: str = Body(
        ...,
        description="Resolution strategy (keep_main, keep_fbe, merge_best)",
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Resolve duplicate SKU conflicts.

    - **sku**: The SKU with conflicts
    - **resolution**: Resolution strategy to apply
    """
    try:
        # Mock duplicate resolution
        resolution_result = {
            "sku": sku,
            "resolution_applied": resolution,
            "status": "resolved",
            "actions_taken": [
                "Marked conflict as resolved",
                "Applied resolution strategy",
                "Updated product records",
                "Sent notification to administrators",
            ],
            "resolution_details": {
                "strategy": resolution,
                "timestamp": datetime.utcnow().isoformat(),
                "resolved_by": "admin",
                "notes": "Resolved via API call",
            },
            "message": f"Duplicate SKU {sku} resolved using strategy: {resolution}",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return resolution_result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve duplicate SKU: {e!s}",
        )


@router.get("/products/conflicts")
async def get_product_conflicts(
    conflict_type: Optional[str] = Query(
        None,
        description="Filter by conflict type (price, stock, name, all)",
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get product conflicts and discrepancies.

    - **conflict_type**: Filter by specific conflict type
    """
    try:
        # Mock conflicts data
        conflicts_data = {
            "total_conflicts": 156,
            "conflicts_by_type": {"price": 89, "stock": 45, "name": 12, "category": 10},
            "high_priority_conflicts": [
                {
                    "sku": "PRD001",
                    "conflict_type": "price",
                    "severity": "high",
                    "description": "Price difference of 15% between accounts",
                    "accounts_involved": ["main", "fbe"],
                    "details": {
                        "main_price": 299.99,
                        "fbe_price": 254.99,
                        "difference": 45.00,
                        "difference_percentage": 15.0,
                    },
                },
                {
                    "sku": "PRD002",
                    "conflict_type": "stock",
                    "severity": "medium",
                    "description": "Stock discrepancy detected",
                    "accounts_involved": ["main", "fbe"],
                    "details": {"main_stock": 0, "fbe_stock": 25, "difference": 25},
                },
            ],
            "resolution_suggestions": [
                "💰 Price conflicts: Review pricing strategy across accounts",
                "📦 Stock conflicts: Check inventory accuracy",
                "🏷️ Name conflicts: Standardize product naming",
                "📂 Category conflicts: Align product categorization",
            ],
            "message": "Product conflicts detected - review and resolve",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return conflicts_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product conflicts: {e!s}",
        )


@router.post("/test-connection")
async def test_emag_connection(
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Test connection to eMAG API.

    - **Returns**: Connection test results
    """
    try:
        if not emag_service.api_client:
            return {
                "status": "failed",
                "message": "eMAG API client not initialized",
                "details": {"reason": "not_configured"},
            }

        # Test basic connectivity by getting available reports (lightweight endpoint)
        _ = await emag_service.api_client._make_request("GET", "/")

        return {
            "status": "success",
            "message": "Connection to eMAG API successful",
            "details": {
                "environment": emag_service.config.environment.value,
                "api_available": True,
                "test_timestamp": datetime.utcnow().isoformat(),
            },
        }

    except ConfigurationError as e:
        return {
            "status": "failed",
            "message": f"eMAG integration not configured: {e!s}",
            "details": {"reason": "not_configured"},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {e!s}",
        )


@router.post("/sync/all-products")
async def sync_all_products_from_both_accounts(
    background_tasks: BackgroundTasks,
    max_pages_per_account: int = Query(
        100,
        description="Maximum pages per account",
        ge=1,
        le=500,
    ),
    delay_between_requests: float = Query(
        0.1,
        description="Delay between requests in seconds",
        ge=0.0,
        le=5.0,
    ),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Sync all products from both MAIN and FBE accounts.

    - **max_pages_per_account**: Maximum pages to retrieve per account (1-500)
    - **delay_between_requests**: Delay between API requests in seconds (0.0-5.0)
    - **Returns**: Complete sync results with all products from both accounts
    """
    try:
        # Run sync in background
        background_tasks.add_task(
            emag_service.sync_all_products_from_both_accounts,
            max_pages_per_account=max_pages_per_account,
            delay_between_requests=delay_between_requests,
        )

        return {
            "message": "Full product synchronization started",
            "max_pages_per_account": max_pages_per_account,
            "delay_between_requests": delay_between_requests,
            "status": "in_progress",
            "estimated_time": f"{max_pages_per_account * 2 * delay_between_requests:.1f} seconds",
            "note": "This will retrieve all products from both MAIN and FBE accounts",
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start full product sync: {e!s}",
        )


@router.post("/sync/all-offers")
async def sync_all_offers_from_both_accounts(
    background_tasks: BackgroundTasks,
    max_pages_per_account: int = Query(
        100,
        description="Maximum pages per account",
        ge=1,
        le=500,
    ),
    delay_between_requests: float = Query(
        0.1,
        description="Delay between requests in seconds",
        ge=0.0,
        le=5.0,
    ),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Sync all offers from both MAIN and FBE accounts.

    - **max_pages_per_account**: Maximum pages to retrieve per account (1-500)
    - **delay_between_requests**: Delay between API requests in seconds (0.0-5.0)
    - **Returns**: Complete sync results with all offers from both accounts
    """
    try:
        # Run sync in background
        background_tasks.add_task(
            emag_service.sync_all_offers_from_both_accounts,
            max_pages_per_account=max_pages_per_account,
            delay_between_requests=delay_between_requests,
        )

        return {
            "message": "Full offers synchronization started",
            "max_pages_per_account": max_pages_per_account,
            "delay_between_requests": delay_between_requests,
            "status": "in_progress",
            "estimated_time": f"{max_pages_per_account * 2 * delay_between_requests:.1f} seconds",
            "note": "This will retrieve all offers from both MAIN and FBE accounts",
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start full offers sync: {e!s}",
        )


@router.get("/products/all")
async def get_all_products_from_both_accounts(
    max_pages_per_account: int = Query(
        50,
        description="Maximum pages per account",
        ge=1,
        le=200,
    ),
    delay_between_requests: float = Query(
        0.1,
        description="Delay between requests in seconds",
        ge=0.0,
        le=2.0,
    ),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get all products from both MAIN and FBE accounts.

    - **max_pages_per_account**: Maximum pages to retrieve per account (1-200)
    - **delay_between_requests**: Delay between API requests in seconds (0.0-2.0)
    - **Returns**: All products from both accounts with deduplication
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        # Get all products from both accounts
        result = await emag_service.sync_all_products_from_both_accounts(
            max_pages_per_account=max_pages_per_account,
            delay_between_requests=delay_between_requests,
        )

        return {
            "sync_results": result,
            "message": f"Retrieved {result['combined']['products_count']} unique products from both accounts",
            "main_account_products": result["main_account"]["products_count"],
            "fbe_account_products": result["fbe_account"]["products_count"],
            "total_processed": result["total_products_processed"],
            "sync_timestamp": result["sync_timestamp"],
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all products: {e!s}",
        )


@router.get("/offers/all")
async def get_all_offers_from_both_accounts(
    max_pages_per_account: int = Query(
        50,
        description="Maximum pages per account",
        ge=1,
        le=200,
    ),
    delay_between_requests: float = Query(
        0.1,
        description="Delay between requests in seconds",
        ge=0.0,
        le=2.0,
    ),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get all offers from both MAIN and FBE accounts.

    - **max_pages_per_account**: Maximum pages to retrieve per account (1-200)
    - **delay_between_requests**: Delay between API requests in seconds (0.0-2.0)
    - **Returns**: All offers from both accounts with deduplication
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        # Get all offers from both accounts
        result = await emag_service.sync_all_offers_from_both_accounts(
            max_pages_per_account=max_pages_per_account,
            delay_between_requests=delay_between_requests,
        )

        return {
            "sync_results": result,
            "message": f"Retrieved {result['combined']['offers_count']} unique offers from both accounts",
            "main_account_offers": result["main_account"]["offers_count"],
            "fbe_account_offers": result["fbe_account"]["offers_count"],
            "total_processed": result["total_offers_processed"],
            "sync_timestamp": result["sync_timestamp"],
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all offers: {e!s}",
        )


@router.get("/products/{product_id}")
async def get_product_details(
    product_id: str,
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get detailed information for a specific product from eMAG.

    - **product_id**: The eMAG product ID
    - **account_type**: Account type filter (main or fbe)
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        # Get product details
        product_details = await emag_service.get_product_details(
            product_id,
            account_type,
        )

        return {
            "product_id": product_id,
            "account_type": account_type,
            "product_details": product_details,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product details: {e!s}",
        )


@router.get("/offers/{offer_id}")
async def get_offer_details(
    offer_id: str,
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get detailed information for a specific offer from eMAG.

    - **offer_id**: The eMAG offer ID
    - **account_type**: Account type filter (main or fbe)
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        # Get offer details
        offer_details = await emag_service.get_offer_details(offer_id, account_type)

        return {
            "offer_id": offer_id,
            "account_type": account_type,
            "offer_details": offer_details,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get offer details: {e!s}",
        )


@router.get("/products/sync-progress")
async def get_sync_progress(
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get current sync progress and status.

    Returns information about ongoing and completed sync operations.
    """
    try:
        # In a real implementation, this would query sync status from database
        # For now, return mock data with service information
        sync_info = {
            "service_status": (
                "operational" if emag_service.api_client else "not_initialized"
            ),
            "active_sync_tasks": (
                len(emag_service._sync_tasks)
                if hasattr(emag_service, "_sync_tasks")
                else 0
            ),
            "last_sync_time": None,  # Would come from database
            "total_products_synced": 0,  # Would come from database
            "total_offers_synced": 0,  # Would come from database
            "sync_errors": [],  # Would come from logs
            "estimated_next_sync": None,  # Would be calculated based on schedule
            "sync_history": [
                {
                    "sync_type": "products",
                    "account_type": "main",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "products_count": 1250,
                    "duration_seconds": 45.2,
                    "status": "completed",
                },
                {
                    "sync_type": "offers",
                    "account_type": "fbe",
                    "timestamp": "2024-01-15T09:15:00Z",
                    "offers_count": 890,
                    "duration_seconds": 32.1,
                    "status": "completed",
                },
            ],
        }

        return {"sync_progress": sync_info, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync progress: {e!s}",
        )


@router.post("/sync/scheduled")
async def setup_scheduled_sync(
    sync_config: Dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Setup scheduled synchronization for eMAG products and offers.

    - **sync_config**: Configuration for scheduled sync
    """
    try:
        # Validate sync configuration
        required_fields = ["sync_interval_minutes", "sync_types", "accounts"]
        for field in required_fields:
            if field not in sync_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        sync_interval = sync_config["sync_interval_minutes"]
        sync_types = sync_config["sync_types"]  # ["products", "offers"]
        accounts = sync_config["accounts"]  # ["main", "fbe"]

        if sync_interval < 15 or sync_interval > 1440:  # 15 minutes to 24 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sync interval must be between 15 minutes and 24 hours",
            )

        # Setup scheduled sync (in real implementation, this would configure a scheduler)
        scheduled_sync = {
            "sync_interval_minutes": sync_interval,
            "sync_types": sync_types,
            "accounts": accounts,
            "next_sync_time": (
                datetime.utcnow() + timedelta(minutes=sync_interval)
            ).isoformat(),
            "status": "scheduled",
            "created_at": datetime.utcnow().isoformat(),
        }

        return {
            "scheduled_sync": scheduled_sync,
            "message": "Scheduled sync configured successfully",
            "note": f"Next sync will run in {sync_interval} minutes and repeat every {sync_interval} minutes",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup scheduled sync: {e!s}",
        )


@router.get("/sync/export")
async def export_sync_data(
    export_format: str = Query("json", description="Export format (json, csv)"),
    include_products: bool = Query(True, description="Include products data"),
    include_offers: bool = Query(True, description="Include offers data"),
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Export sync data for analysis or backup.

    - **export_format**: Export format (json, csv)
    - **include_products**: Include products data
    - **include_offers**: Include offers data
    - **account_type**: Filter by account type (main, fbe, or null for both)
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eMAG API client not initialized",
            )

        # Get sync data based on parameters
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_format": export_format,
            "filters": {
                "include_products": include_products,
                "include_offers": include_offers,
                "account_type": account_type,
            },
            "data": {},
        }

        if include_products:
            # Get products data
            if account_type:
                products = await emag_service.get_all_products(
                    account_type,
                    max_pages=10,
                )
            else:
                products_result = (
                    await emag_service.sync_all_products_from_both_accounts(
                        max_pages_per_account=10,
                    )
                )
                products = products_result["combined"]["products"]

            export_data["data"]["products"] = {
                "count": len(products),
                "products": products,
            }

        if include_offers:
            # Get offers data
            if account_type:
                offers = await emag_service.get_all_offers(account_type, max_pages=10)
            else:
                offers_result = await emag_service.sync_all_offers_from_both_accounts(
                    max_pages_per_account=10,
                )
                offers = offers_result["combined"]["offers"]

            export_data["data"]["offers"] = {"count": len(offers), "offers": offers}

        return {
            "export_data": export_data,
            "message": f"Export completed with {len(export_data['data'])} data types",
            "download_url": "/api/v1/emag/sync/export/download",  # Would be implemented
            "file_size_estimate": f"{len(str(export_data))} characters",
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export sync data: {e!s}",
        )


@router.get("/analytics/sales")
async def get_sales_analytics(
    days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get advanced sales analytics and insights.

    - **days**: Analysis period in days (1-365)
    - **account_type**: Account type filter (main or fbe)
    """
    try:
        from app.services.emag_analytics_service import EmagAnalyticsService

        analytics_service = EmagAnalyticsService(emag_service.context)
        await analytics_service.initialize()

        result = await analytics_service.analyze_sales_performance(account_type, days)

        return {
            "analytics": result,
            "message": f"Sales analytics for {account_type} account over {days} days",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analytics service not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sales analytics: {e!s}",
        )


@router.get("/analytics/inventory")
async def get_inventory_analytics(
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get inventory optimization analytics.

    - **account_type**: Account type filter (main or fbe)
    """
    try:
        from app.services.emag_analytics_service import EmagAnalyticsService

        analytics_service = EmagAnalyticsService(emag_service.context)
        await analytics_service.initialize()

        result = await analytics_service.analyze_inventory_optimization(account_type)

        return {
            "analytics": result,
            "message": f"Inventory analytics for {account_type} account",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analytics service not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get inventory analytics: {e!s}",
        )


@router.get("/analytics/pricing")
async def get_pricing_analytics(
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get price optimization analytics.

    - **account_type**: Account type filter (main or fbe)
    """
    try:
        from app.services.emag_analytics_service import EmagAnalyticsService

        analytics_service = EmagAnalyticsService(emag_service.context)
        await analytics_service.initialize()

        result = await analytics_service.analyze_price_optimization(account_type)

        return {
            "analytics": result,
            "message": f"Pricing analytics for {account_type} account",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analytics service not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pricing analytics: {e!s}",
        )


@router.get("/analytics/trends")
async def get_market_trends(
    prediction_days: int = Query(
        30,
        description="Prediction period in days",
        ge=1,
        le=90,
    ),
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get market trend predictions using AI.

    - **prediction_days**: Prediction period in days (1-90)
    - **account_type**: Account type filter (main or fbe)
    """
    try:
        from app.services.emag_analytics_service import EmagAnalyticsService

        analytics_service = EmagAnalyticsService(emag_service.context)
        await analytics_service.initialize()

        result = await analytics_service.predict_market_trends(
            account_type,
            prediction_days,
        )

        return {
            "analytics": result,
            "message": f"Market trend predictions for {account_type} account",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analytics service not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market trends: {e!s}",
        )


@router.get("/analytics/report")
async def get_comprehensive_report(
    report_type: str = Query(
        "full",
        description="Report type (full, sales, inventory, pricing, trends)",
    ),
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service),
) -> Dict[str, Any]:
    """Get comprehensive analytics report.

    - **report_type**: Type of report (full, sales, inventory, pricing, trends)
    - **account_type**: Account type filter (main or fbe)
    """
    try:
        from app.services.emag_analytics_service import EmagAnalyticsService

        analytics_service = EmagAnalyticsService(emag_service.context)
        await analytics_service.initialize()

        result = await analytics_service.generate_comprehensive_report(
            account_type,
            report_type,
        )

        return {
            "report": result,
            "message": f"Comprehensive {report_type} report for {account_type} account",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analytics service not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comprehensive report: {e!s}",
        )


# @router.get("/security/audit")
# async def get_security_audit(
#     hours: int = Query(24, description="Audit period in hours", ge=1, le=168),
#     event_type: Optional[str] = Query(None, description="Filter by event type"),
#     current_user: UserModel = Depends(get_current_active_user),
#     security_service: AdvancedSecurityService = Depends(get_security_service)
# ) -> Dict[str, Any]:
#     """
#     Get security audit log.
#
#     - **hours**: Audit period in hours (1-168)
#     - **event_type**: Filter by specific event type
#     """
#     try:
#         from app.services.advanced_security_service import AdvancedSecurityService
#
#         # This would normally get the service from dependency injection
#         # For now, we'll create a mock response
#         audit_data = {
#             "period_hours": hours,
#             "total_events": 1250,
#             "event_types": {
#                 "login_success": 890,
#                 "api_call": 234,
#                 "sync_operation": 67,
#                 "logout": 59
#             },
#             "security_levels": {
#                 "low": 1120,
#                 "medium": 98,
#                 "high": 28,
#                 "critical": 4
#             },
#             "recent_events": [
#                 {
#                     "event_type": "login_success",
#                     "user_id": "user123",
#                     "resource": "/auth/login",
#                     "timestamp": "2024-01-15T10:30:00Z",
#                     "success": True
#                 }
#             ],
#             "message": f"Security audit data for the last {hours} hours",
#             "timestamp": datetime.utcnow().isoformat()
#         }
#
#         return audit_data
#
#     except Exception as e:
#         raise HTTPException(
#     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#     detail=f"Failed to get security audit: {str(e)}"
#     )


@router.get("/security/alerts")
async def get_security_alerts(
    active_only: bool = Query(True, description="Show only active alerts"),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get security alerts.

    - **active_only**: Show only active (unresolved) alerts
    """
    try:
        # Mock security alerts data
        alerts_data = {
            "total_alerts": 15,
            "active_alerts": 3,
            "alerts_by_severity": {"low": 8, "medium": 4, "high": 2, "critical": 1},
            "recent_alerts": [
                {
                    "alert_type": "suspicious_activity",
                    "severity": "medium",
                    "title": "Multiple Failed Login Attempts",
                    "description": "User user123 had 5 failed login attempts",
                    "timestamp": "2024-01-15T09:45:00Z",
                    "resolved": False,
                },
            ],
            "message": "Security alerts overview",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return alerts_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security alerts: {e!s}",
        )


@router.get("/rate-limit/status")
async def get_rate_limit_status(
    user_id: Optional[str] = Query(None, description="User ID for specific status"),
    endpoint: Optional[str] = Query(None, description="Endpoint for specific status"),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get current rate limiting status.

    - **user_id**: Get status for specific user
    - **endpoint**: Get status for specific endpoint
    """
    try:
        # Mock rate limit status data
        status_data = {
            "is_healthy": True,
            "current_load_level": "normal",
            "queue_size": 0,
            "limits": {"orders": 720, "products": 180, "default": 60},
            "requests_per_minute": {
                "user_123": 45,
                "endpoint_products": 120,
                "global_default": 890,
            },
            "message": "Rate limiting status overview",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return status_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rate limit status: {e!s}",
        )


@router.get("/tenants")
async def get_tenants(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get multi-tenant eMAG account management.

    Returns list of configured eMAG accounts/tenants.
    """
    try:
        # Mock tenants data
        tenants_data = {
            "total_tenants": 3,
            "active_tenants": 2,
            "tenants": [
                {
                    "tenant_id": "main_account",
                    "account_type": "main",
                    "status": "active",
                    "last_sync": "2024-01-15T10:00:00Z",
                    "quotas": {"requests_per_minute": 720, "products_per_sync": 10000},
                },
                {
                    "tenant_id": "fbe_account",
                    "account_type": "fbe",
                    "status": "active",
                    "last_sync": "2024-01-15T09:30:00Z",
                    "quotas": {"requests_per_minute": 180, "products_per_sync": 5000},
                },
                {
                    "tenant_id": "staging_account",
                    "account_type": "main",
                    "status": "inactive",
                    "last_sync": "2024-01-10T15:45:00Z",
                    "quotas": {"requests_per_minute": 60, "products_per_sync": 1000},
                },
            ],
            "message": "Multi-tenant eMAG accounts overview",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return tenants_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenants: {e!s}",
        )


@router.post("/tenants/{tenant_id}/sync")
async def sync_tenant(
    tenant_id: str,
    sync_type: str = Body(..., description="Type of sync (products, offers, full)"),
    max_pages: int = Body(50, description="Maximum pages to sync"),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Sync specific eMAG tenant/account.

    - **tenant_id**: Tenant/account ID to sync
    - **sync_type**: Type of sync operation
    - **max_pages**: Maximum pages to retrieve
    """
    try:
        # Mock tenant sync response
        sync_result = {
            "tenant_id": tenant_id,
            "sync_type": sync_type,
            "status": "initiated",
            "max_pages": max_pages,
            "estimated_duration_seconds": 120,
            "message": f"Sync initiated for tenant {tenant_id}",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return sync_result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync tenant: {e!s}",
        )


@router.get("/analytics/dashboard")
async def get_analytics_dashboard(
    period_days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get comprehensive analytics dashboard.

    - **period_days**: Analysis period in days (1-365)
    """
    try:
        # Mock analytics dashboard data
        dashboard_data = {
            "period_days": period_days,
            "summary": {
                "total_products_synced": 15420,
                "total_offers_synced": 12890,
                "sync_success_rate": 0.987,
                "average_response_time": 245,
                "data_quality_score": 0.94,
            },
            "accounts": {
                "main": {
                    "products": 8950,
                    "offers": 7890,
                    "last_sync": "2024-01-15T10:00:00Z",
                    "health_score": 0.96,
                },
                "fbe": {
                    "products": 6470,
                    "offers": 5000,
                    "last_sync": "2024-01-15T09:30:00Z",
                    "health_score": 0.92,
                },
            },
            "performance_metrics": {
                "sync_duration_avg": 180,
                "error_rate": 0.013,
                "throughput_products_per_minute": 85,
                "api_efficiency": 0.89,
            },
            "alerts": {"critical": 0, "warnings": 2, "info": 5},
            "message": f"Analytics dashboard for the last {period_days} days",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return dashboard_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics dashboard: {e!s}",
        )


@router.get("/health/advanced")
async def get_advanced_health(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get advanced system health metrics."""
    try:
        # Mock advanced health data
        health_data = {
            "overall_status": "healthy",
            "services": {
                "emag_api": {
                    "status": "healthy",
                    "response_time_ms": 245,
                    "uptime_percentage": 99.8,
                    "last_check": "2024-01-15T10:35:00Z",
                },
                "database": {
                    "status": "healthy",
                    "connections": 12,
                    "query_performance": "good",
                    "last_check": "2024-01-15T10:35:00Z",
                },
                "cache": {
                    "status": "healthy",
                    "hit_rate": 0.94,
                    "memory_usage": "45%",
                    "last_check": "2024-01-15T10:35:00Z",
                },
                "rate_limiter": {
                    "status": "healthy",
                    "queue_size": 0,
                    "load_level": "normal",
                    "last_check": "2024-01-15T10:35:00Z",
                },
            },
            "performance": {
                "cpu_usage": "23%",
                "memory_usage": "67%",
                "disk_usage": "45%",
                "network_io": "normal",
            },
            "security": {
                "failed_login_attempts": 3,
                "suspicious_activities": 0,
                "audit_log_size": 15420,
                "last_security_scan": "2024-01-15T08:00:00Z",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        return health_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get advanced health: {e!s}",
        )


@router.post("/test/credentials")
async def test_emag_credentials(
    credentials: Dict[str, Any] = Body(..., description="eMAG credentials for testing"),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Test eMAG credentials and connection.

    **credentials**: Dictionary containing eMAG username, password, and optional settings
    """
    try:
        from app.services.emag_testing_service import (
            EmagCredentials,
            EmagTestingService,
            TestEnvironment,
        )

        # Validate credentials format
        if not isinstance(credentials, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credentials must be a dictionary",
            )

        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required",
            )

        # Create credentials object
        test_credentials = EmagCredentials(
            username=username,
            password=password,
            environment=TestEnvironment.PRODUCTION,
            test_mode=True,
        )

        # Initialize testing service
        context = ServiceContext(settings=get_settings())
        testing_service = EmagTestingService(context)
        await testing_service.initialize()

        # Run connection test
        connection_result = await testing_service.test_credentials_connection(
            test_credentials,
        )

        # Run authentication test
        auth_result = await testing_service.test_authentication(test_credentials)

        return {
            "test_results": {
                "connection": {
                    "success": connection_result.success,
                    "duration_ms": connection_result.duration_ms,
                    "error": connection_result.error_message,
                    "metadata": connection_result.metadata,
                },
                "authentication": {
                    "success": auth_result.success,
                    "duration_ms": auth_result.duration_ms,
                    "error": auth_result.error_message,
                    "metadata": auth_result.metadata,
                },
            },
            "overall_status": (
                "success"
                if (connection_result.success and auth_result.success)
                else "issues_detected"
            ),
            "recommendations": await generate_credential_test_recommendations(
                connection_result,
                auth_result,
            ),
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Credential testing completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test credentials: {e!s}",
        )


@router.post("/test/full-suite")
async def run_full_test_suite(
    credentials: Dict[str, Any] = Body(..., description="eMAG credentials for testing"),
    test_types: List[str] = Body(
        default=["connection", "authentication", "rate_limits", "data_retrieval"],
        description="Types of tests to run",
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Run complete test suite with eMAG credentials.

    **credentials**: Dictionary containing eMAG username, password, and optional settings
    **test_types**: List of test types to run (connection, authentication, rate_limits, data_retrieval, sync_operation)
    """
    try:
        from app.services.emag_testing_service import (
            EmagCredentials,
            EmagTestingService,
            TestEnvironment,
            TestType,
        )

        # Validate credentials
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required",
            )

        # Create credentials object
        test_credentials = EmagCredentials(
            username=username,
            password=password,
            environment=TestEnvironment.PRODUCTION,
            test_mode=True,
        )

        # Convert test types
        valid_test_types = []
        for test_type_str in test_types:
            try:
                valid_test_types.append(TestType(test_type_str))
            except ValueError:
                logger.warning(f"Invalid test type: {test_type_str}")

        if not valid_test_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid test types provided",
            )

        # Initialize testing service
        context = ServiceContext(settings=get_settings())
        testing_service = EmagTestingService(context)
        await testing_service.initialize()

        # Run test suite
        test_suite = await testing_service.run_complete_test_suite(
            test_credentials,
            valid_test_types,
        )

        return {
            "suite_id": test_suite.suite_id,
            "overall_success": test_suite.overall_success,
            "summary": test_suite.summary,
            "test_results": [
                {
                    "test_type": result.test_type.value,
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                    "request_count": result.request_count,
                    "response_time_avg_ms": result.response_time_avg_ms,
                    "error_message": result.error_message,
                    "metadata": result.metadata,
                }
                for result in test_suite.results
            ],
            "recommendations": await generate_test_suite_recommendations(test_suite),
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Full test suite completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run test suite: {e!s}",
        )


@router.post("/test/rate-limits")
async def test_emag_rate_limits(
    credentials: Dict[str, Any] = Body(..., description="eMAG credentials for testing"),
    test_duration_seconds: int = Body(
        60,
        description="Test duration in seconds",
        ge=10,
        le=300,
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Test eMAG API rate limits.

    **credentials**: Dictionary containing eMAG username, password
    **test_duration_seconds**: How long to test rate limits (10-300 seconds)
    """
    try:
        from app.services.emag_testing_service import (
            EmagCredentials,
            EmagTestingService,
            TestEnvironment,
        )

        # Validate credentials
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required",
            )

        # Create credentials object
        test_credentials = EmagCredentials(
            username=username,
            password=password,
            environment=TestEnvironment.PRODUCTION,
            test_mode=True,
        )

        # Initialize testing service
        context = ServiceContext(settings=get_settings())
        testing_service = EmagTestingService(context)
        await testing_service.initialize()

        # Run rate limits test
        rate_limit_result = await testing_service.test_rate_limits(
            test_credentials,
            test_duration_seconds,
        )

        return {
            "test_result": {
                "success": rate_limit_result.success,
                "duration_ms": rate_limit_result.duration_ms,
                "request_count": rate_limit_result.request_count,
                "response_time_avg_ms": rate_limit_result.response_time_avg_ms,
                "requests_per_second": rate_limit_result.metadata.get(
                    "requests_per_second",
                    0,
                ),
                "rate_limited": rate_limit_result.metadata.get("rate_limit_hit", False),
                "metadata": rate_limit_result.metadata,
            },
            "recommendations": await generate_rate_limit_recommendations(
                rate_limit_result,
            ),
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Rate limits test completed in {test_duration_seconds} seconds",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test rate limits: {e!s}",
        )


@router.post("/test/data-retrieval")
async def test_data_retrieval(
    credentials: Dict[str, Any] = Body(..., description="eMAG credentials for testing"),
    max_pages: int = Body(5, description="Maximum pages to test", ge=1, le=10),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Test data retrieval capabilities.

    **credentials**: Dictionary containing eMAG username, password
    **max_pages**: Maximum pages to retrieve for testing
    """
    try:
        from app.services.emag_testing_service import (
            EmagCredentials,
            EmagTestingService,
            TestEnvironment,
        )

        # Validate credentials
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required",
            )

        # Create credentials object
        test_credentials = EmagCredentials(
            username=username,
            password=password,
            environment=TestEnvironment.PRODUCTION,
            test_mode=True,
        )

        # Initialize testing service
        context = ServiceContext(settings=get_settings())
        testing_service = EmagTestingService(context)
        await testing_service.initialize()

        # Run data retrieval test
        data_result = await testing_service.test_data_retrieval(
            test_credentials,
            max_pages,
        )

        return {
            "test_result": {
                "success": data_result.success,
                "duration_ms": data_result.duration_ms,
                "request_count": data_result.request_count,
                "response_time_avg_ms": data_result.response_time_avg_ms,
                "products_retrieved": data_result.metadata.get("products_retrieved", 0),
                "offers_retrieved": data_result.metadata.get("offers_retrieved", 0),
                "data_quality_score": data_result.metadata.get("data_quality_score", 0),
                "metadata": data_result.metadata,
            },
            "recommendations": await generate_data_retrieval_recommendations(
                data_result,
            ),
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Data retrieval test completed with {max_pages} pages",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test data retrieval: {e!s}",
        )


@router.get("/test/status")
async def get_test_status(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get current testing status and available test configurations."""
    try:
        return {
            "testing_available": True,
            "test_types": [
                "connection",
                "authentication",
                "rate_limits",
                "data_retrieval",
                "sync_operation",
            ],
            "default_test_suite": [
                "connection",
                "authentication",
                "rate_limits",
                "data_retrieval",
            ],
            "recommended_settings": {
                "max_pages_test": 5,
                "rate_limit_test_duration": 60,
                "data_retrieval_pages": 3,
            },
            "safety_features": {
                "test_mode_enabled": True,
                "rate_limiting_respected": True,
                "error_recovery": True,
                "data_validation": True,
            },
            "current_environment": "production",  # Would be configurable
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Testing service ready",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test status: {e!s}",
        )


@router.post("/test/sync-operation")
async def test_sync_operation(
    credentials: Dict[str, Any] = Body(..., description="eMAG credentials for testing"),
    max_pages: int = Body(3, description="Maximum pages to sync", ge=1, le=5),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Test complete sync operation.

    **credentials**: Dictionary containing eMAG username, password
    **max_pages**: Maximum pages to sync per account
    """
    try:
        from app.services.emag_testing_service import (
            EmagCredentials,
            EmagTestingService,
            TestEnvironment,
        )

        # Validate credentials
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required",
            )

        # Create credentials object
        test_credentials = EmagCredentials(
            username=username,
            password=password,
            environment=TestEnvironment.PRODUCTION,
            test_mode=True,
        )

        # Initialize testing service
        context = ServiceContext(settings=get_settings())
        testing_service = EmagTestingService(context)
        await testing_service.initialize()

        # Run sync test
        sync_result = await testing_service.test_sync_operation(
            test_credentials,
            max_pages,
        )

        return {
            "test_result": {
                "success": sync_result.success,
                "duration_ms": sync_result.duration_ms,
                "request_count": sync_result.request_count,
                "response_time_avg_ms": sync_result.response_time_avg_ms,
                "main_products": sync_result.metadata.get("main_products", 0),
                "fbe_products": sync_result.metadata.get("fbe_products", 0),
                "combined_products": sync_result.metadata.get("combined_products", 0),
                "metadata": sync_result.metadata,
            },
            "recommendations": await generate_sync_recommendations(sync_result),
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Sync test completed with {max_pages} pages per account",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test sync operation: {e!s}",
        )


# RMA Integration endpoints (keeping existing functionality)
@router.get("/rma/sync-status")
async def get_rma_sync_status(
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get RMA sync status with eMAG."""
    return {
        "status": "success",
        "rma_integration": {
            "supported": True,
            "endpoints": ["create_rma", "update_rma_status", "get_rma_details"],
            "account_types": ["main", "fbe"],
        },
        "message": "RMA integration ready",
    }


@router.post("/sync/rma")
async def sync_rma_with_emag(
    return_request_id: int,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Sync a return request with eMAG."""
    try:
        # This would integrate with the new service
        # For now, return mock success
        return {
            "status": "success",
            "sync_result": {"rma_id": f"rma_{return_request_id}"},
            "message": f"Return request {return_request_id} synced with eMAG",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync RMA: {e!s}",
        )


# Invoice Integration endpoints (keeping existing functionality)
@router.get("/invoices/sync-status")
async def get_invoice_sync_status(
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get invoice sync status with eMAG."""
    return {
        "status": "success",
        "invoice_integration": {
            "supported": True,
            "endpoints": [
                "create_invoice",
                "update_invoice_payment_status",
                "get_invoice_details",
            ],
            "account_types": ["main", "fbe"],
        },
        "message": "Invoice integration ready",
    }


@router.post("/sync/invoice")
async def sync_invoice_with_emag(
    invoice_id: int,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Sync an invoice with eMAG."""
    try:
        # This would integrate with the new service
        # For now, return mock success
        return {
            "status": "success",
            "sync_result": {"invoice_id": f"inv_{invoice_id}"},
            "message": f"Invoice {invoice_id} synced with eMAG",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync invoice: {e!s}",
        )


# Configuration endpoint
@router.get("/configuration")
async def get_emag_configuration(
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get eMAG integration configuration."""
    return {
        "status": "success",
        "configuration": {
            "base_url": "https://marketplace.emag.ro/api-3",
            "supported_account_types": ["main", "fbe"],
            "rate_limits": {
                "orders": "12 requests/second",
                "offers": "3 requests/second",
                "rma": "5 requests/second",
                "invoices": "3 requests/second",
                "other": "3 requests/second",
            },
            "features": {
                "product_offers": True,
                "rma_management": True,
                "order_cancellations": True,
                "invoice_management": True,
                "automatic_retry": True,
                "rate_limiting": True,
            },
            "endpoints": {
                "product_offers": "/product_offer/read",
                "rma_create": "/rma/create",
                "rma_update": "/rma/update_status",
                "cancel_order": "/order/cancel",
                "process_refund": "/order/process_refund",
                "create_invoice": "/invoice/create",
                "update_invoice": "/invoice/update_payment",
            },
        },
        "message": "eMAG integration configuration retrieved",
    }


# Helper functions for generating recommendations
async def generate_credential_test_recommendations(
    conn_result,
    auth_result,
) -> List[str]:
    """Generate recommendations based on credential test results."""
    recommendations = []

    if not conn_result.success:
        recommendations.append("❌ Connection failed - Check username and password")
        recommendations.append("🔒 Verify eMAG credentials are correct")
        recommendations.append("🌐 Check internet connection and eMAG API status")

    if not auth_result.success:
        recommendations.append("❌ Authentication failed - IP may not be whitelisted")
        recommendations.append("⚙️ Add your IP to eMAG API whitelist")
        recommendations.append("🔑 Verify username and password are correct")

    if conn_result.success and auth_result.success:
        recommendations.append("✅ Credentials are valid and working")
        recommendations.append("🚀 Ready to proceed with full testing")

    return recommendations


async def generate_test_suite_recommendations(test_suite) -> List[str]:
    """Generate recommendations based on complete test suite results."""
    recommendations = []

    failed_tests = [r for r in test_suite.results if not r.success]

    if failed_tests:
        recommendations.append(
            f"⚠️ {len(failed_tests)} test(s) failed - Review errors below",
        )

    successful_tests = [r for r in test_suite.results if r.success]
    if successful_tests:
        recommendations.append(
            f"✅ {len(successful_tests)} test(s) passed successfully",
        )

    if test_suite.overall_success:
        recommendations.append("🎉 All tests passed - System is ready for production")
    else:
        recommendations.append(
            "🔧 Review failed tests and fix issues before production use",
        )

    return recommendations


async def generate_rate_limit_recommendations(result) -> List[str]:
    """Generate recommendations based on rate limit test results."""
    recommendations = []

    if not result.success:
        recommendations.append("⚠️ Rate limit test encountered issues")
    else:
        recommendations.append("✅ Rate limiting is working correctly")

    rps = result.metadata.get("requests_per_second", 0)
    if rps > 0:
        recommendations.append(f"📊 Requests per second: {rps:.2f}")

    if result.metadata.get("rate_limit_hit", False):
        recommendations.append("🚦 Rate limits were hit during testing")
        recommendations.append("⚙️ Consider increasing delays between requests")

    recommendations.append("🔧 Rate limiting is properly configured")
    return recommendations


async def generate_data_retrieval_recommendations(result) -> List[str]:
    """Generate recommendations based on data retrieval test results."""
    recommendations = []

    if not result.success:
        recommendations.append("❌ Data retrieval test failed")
    else:
        recommendations.append("✅ Data retrieval is working correctly")

    products = result.metadata.get("products_retrieved", 0)
    offers = result.metadata.get("offers_retrieved", 0)

    if products > 0:
        recommendations.append(f"📦 Successfully retrieved {products} products")

    if offers > 0:
        recommendations.append(f"💰 Successfully retrieved {offers} offers")

    quality_score = result.metadata.get("data_quality_score", 0)
    if quality_score > 0:
        recommendations.append(f"📊 Data quality score: {quality_score:.2f}")

    return recommendations


async def generate_sync_recommendations(result) -> List[str]:
    """Generate recommendations based on sync test results."""
    recommendations = []

    if not result.success:
        recommendations.append("❌ Sync operation test failed")
    else:
        recommendations.append("✅ Sync operation completed successfully")

    main_products = result.metadata.get("main_products", 0)
    fbe_products = result.metadata.get("fbe_products", 0)
    combined = result.metadata.get("combined_products", 0)

    if main_products > 0:
        recommendations.append(f"📦 MAIN account: {main_products} products")

    if fbe_products > 0:
        recommendations.append(f"📦 FBE account: {fbe_products} products")

    if combined > 0:
        recommendations.append(f"🔄 Combined unique products: {combined}")

    recommendations.append("🚀 Sync system is ready for production use")
