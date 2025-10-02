"""Enhanced eMAG offers management for MAIN and FBE accounts.

This module provides functionality to retrieve and manage product offers
from both MAIN and FBE (Fulfillment by eMAG) accounts on the eMAG marketplace.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_active_user
from app.core.exceptions import ConfigurationError
from app.db.models import User as UserModel
from app.services.emag_integration_service import EmagIntegrationService


class EmagAccountType(str, Enum):
    """eMAG account types."""

    MAIN = "main"
    FBE = "fbe"


router = APIRouter(prefix="/emag/offers", tags=["emag-offers"])


@router.get("/all")
async def get_all_offers(
    status: Optional[str] = Query(None, description="Offer status filter"),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    brand: Optional[str] = Query(None, description="Brand filter"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get product offers from all eMAG accounts (MAIN + FBE).

    - **status**: Filter by offer status (active, inactive, pending, etc.)
    - **category_id**: Filter by category ID
    - **brand**: Filter by brand name
    - **page**: Page number for pagination
    - **limit**: Number of items per page

    Returns combined offers from both MAIN and FBE accounts.
    """
    try:
        # Get offers from both accounts
        main_service = await get_emag_service_for_account(EmagAccountType.MAIN)
        fbe_service = await get_emag_service_for_account(EmagAccountType.FBE)

        # Get offers from MAIN account
        main_offers_data = await main_service.get_product_offers(
            account_type="main",
            status=status,
            category_id=category_id,
            brand=brand,
            page=page,
            limit=limit,
        )

        # Get offers from FBE account
        fbe_offers_data = await fbe_service.get_product_offers(
            account_type="fbe",
            status=status,
            category_id=category_id,
            brand=brand,
            page=page,
            limit=limit,
        )

        # Combine results
        main_offers = main_offers_data.get("offers", [])
        fbe_offers = fbe_offers_data.get("offers", [])

        # Add account type to each offer for identification
        for offer in main_offers:
            offer["_account_type"] = "main"
        for offer in fbe_offers:
            offer["_account_type"] = "fbe"

        combined_offers = main_offers + fbe_offers

        # Sort by account type and name
        combined_offers.sort(
            key=lambda x: (x.get("_account_type", ""), x.get("name", "").lower())
        )

        return {
            "account_type": "all",
            "offers": combined_offers,
            "total_count": len(combined_offers),
            "page": page,
            "limit": limit,
            "total_pages": (len(combined_offers) + limit - 1) // limit,
            "account_breakdown": {
                "main": len(main_offers),
                "fbe": len(fbe_offers),
            },
            "filters_applied": {
                "status": status,
                "category_id": category_id,
                "brand": brand,
            },
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
            detail=f"Failed to get eMAG offers from all accounts: {e!s}",
        )


# Dependency provider for eMAG service with account type support
async def get_emag_service_for_account(
    account_type: EmagAccountType = EmagAccountType.MAIN,
) -> EmagIntegrationService:
    """FastAPI dependency for EmagIntegrationService with account type."""
    from app.core.service_registry import get_service_registry

    registry = get_service_registry()
    if not registry.is_initialized:
        from app.core.service_registry import initialize_service_registry

        # Initialize with a mock session for now
        db_session = None
        await initialize_service_registry(db_session)

    # For now, create a new instance
    # In production, this should come from the service registry
    from app.core.config import get_settings
    from app.core.dependency_injection import ServiceContext

    settings = get_settings()
    context = ServiceContext(settings=settings)
    service = EmagIntegrationService(context, account_type=account_type.value)
    await service.initialize()
    return service


@router.get("/")
async def get_emag_offers(
    account_type: EmagAccountType = Query(
        EmagAccountType.MAIN,
        description="eMAG account type (main or fbe)",
    ),
    status: Optional[str] = Query(None, description="Offer status filter"),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    brand: Optional[str] = Query(None, description="Brand filter"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(get_emag_service_for_account),
) -> Dict[str, Any]:
    """Get product offers from eMAG marketplace.

    - **account_type**: eMAG account type (main or fbe)
    - **status**: Filter by offer status (active, inactive, pending, etc.)
    - **category_id**: Filter by category ID
    - **brand**: Filter by brand name
    - **page**: Page number for pagination
    - **limit**: Number of items per page

    Returns offers from the specified eMAG account.
    """
    try:
        if not emag_service.api_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"eMAG {account_type.value.upper()} API client not initialized",
            )

        # Get offers using eMAG's product offer API
        offers_data = await emag_service.get_product_offers(
            account_type=account_type.value,
            status=status,
            category_id=category_id,
            brand=brand,
            page=page,
            limit=limit,
        )

        return {
            "account_type": account_type.value,
            "offers": offers_data.get("offers", []),
            "total_count": offers_data.get("total_count", 0),
            "page": page,
            "limit": limit,
            "total_pages": (offers_data.get("total_count", 0) + limit - 1) // limit,
            "filters_applied": {
                "status": status,
                "category_id": category_id,
                "brand": brand,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"eMAG {account_type.value.upper()} integration not configured: {e!s}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get eMAG {account_type.value.upper()} offers: {e!s}",
        )


@router.get("/main")
async def get_main_account_offers(
    status: Optional[str] = Query(None, description="Offer status filter"),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    brand: Optional[str] = Query(None, description="Brand filter"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(
        lambda: get_emag_service_for_account(EmagAccountType.MAIN),
    ),
) -> Dict[str, Any]:
    """Get product offers from eMAG MAIN account.

    - **status**: Filter by offer status (active, inactive, pending, etc.)
    - **category_id**: Filter by category ID
    - **brand**: Filter by brand name
    - **page**: Page number for pagination
    - **limit**: Number of items per page
    """
    return await get_emag_offers(
        account_type=EmagAccountType.MAIN,
        status=status,
        category_id=category_id,
        brand=brand,
        page=page,
        limit=limit,
        current_user=current_user,
        emag_service=emag_service,
    )


@router.get("/fbe")
async def get_fbe_account_offers(
    status: Optional[str] = Query(None, description="Offer status filter"),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    brand: Optional[str] = Query(None, description="Brand filter"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
    emag_service: EmagIntegrationService = Depends(
        lambda: get_emag_service_for_account(EmagAccountType.FBE),
    ),
) -> Dict[str, Any]:
    """Get product offers from eMAG FBE (Fulfillment by eMAG) account.

    - **status**: Filter by offer status (active, inactive, pending, etc.)
    - **category_id**: Filter by category ID
    - **brand**: Filter by brand name
    - **page**: Page number for pagination
    - **limit**: Number of items per page
    """
    return await get_emag_offers(
        account_type=EmagAccountType.FBE,
        status=status,
        category_id=category_id,
        brand=brand,
        page=page,
        limit=limit,
        current_user=current_user,
        emag_service=emag_service,
    )


@router.get("/comparison")
async def compare_offers_between_accounts(
    sku: Optional[str] = Query(None, description="Filter by specific SKU"),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    limit: int = Query(50, description="Items per page", ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Compare offers between MAIN and FBE accounts.

    - **sku**: Filter by specific SKU
    - **category_id**: Filter by category ID
    - **limit**: Number of items per page

    Returns a comparison of offers between both account types.
    """
    try:
        # Get offers from both accounts
        main_service = await get_emag_service_for_account(EmagAccountType.MAIN)
        fbe_service = await get_emag_service_for_account(EmagAccountType.FBE)

        # Get offers from MAIN account
        main_offers_data = await main_service.get_product_offers(
            account_type="main",
            category_id=category_id,
            page=1,
            limit=limit,
        )

        # Get offers from FBE account
        fbe_offers_data = await fbe_service.get_product_offers(
            account_type="fbe",
            category_id=category_id,
            page=1,
            limit=limit,
        )

        # Process and compare offers
        main_offers = main_offers_data.get("offers", [])
        fbe_offers = fbe_offers_data.get("offers", [])

        # Create comparison data
        comparison = []
        for main_offer in main_offers:
            sku = main_offer.get("sku")
            fbe_offer = next(
                (offer for offer in fbe_offers if offer.get("sku") == sku),
                None,
            )

            comparison.append(
                {
                    "sku": sku,
                    "main_account": main_offer,
                    "fbe_account": fbe_offer,
                    "price_difference": None,
                    "status_difference": None,
                    "stock_difference": None,
                },
            )

            if fbe_offer:
                main_price = main_offer.get("price", 0)
                fbe_price = fbe_offer.get("price", 0)
                comparison[-1]["price_difference"] = fbe_price - main_price

                main_status = main_offer.get("status")
                fbe_status = fbe_offer.get("status")
                comparison[-1]["status_difference"] = fbe_status != main_status

                main_stock = main_offer.get("stock", 0)
                fbe_stock = fbe_offer.get("stock", 0)
                comparison[-1]["stock_difference"] = fbe_stock - main_stock

        # Add FBE-only offers
        main_skus = {offer.get("sku") for offer in main_offers}
        for fbe_offer in fbe_offers:
            sku = fbe_offer.get("sku")
            if sku not in main_skus:
                comparison.append(
                    {
                        "sku": sku,
                        "main_account": None,
                        "fbe_account": fbe_offer,
                        "price_difference": None,
                        "status_difference": None,
                        "stock_difference": None,
                    },
                )

        return {
            "comparison": comparison,
            "main_account_total": len(main_offers),
            "fbe_account_total": len(fbe_offers),
            "common_products": len(
                [c for c in comparison if c["main_account"] and c["fbe_account"]],
            ),
            "main_only_products": len(
                [c for c in comparison if c["main_account"] and not c["fbe_account"]],
            ),
            "fbe_only_products": len(
                [c for c in comparison if not c["main_account"] and c["fbe_account"]],
            ),
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
            detail=f"Failed to compare offers: {e!s}",
        )


@router.get("/summary")
async def get_offers_summary(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get summary of offers across all eMAG accounts.

    Returns a high-level summary of offers in MAIN and FBE accounts.
    """
    try:
        # Get summary from both accounts
        main_service = await get_emag_service_for_account(EmagAccountType.MAIN)
        fbe_service = await get_emag_service_for_account(EmagAccountType.FBE)

        # Get basic stats from MAIN
        try:
            main_stats = await main_service.get_offers_summary("main")
        except Exception:
            main_stats = {"total_offers": 0, "active_offers": 0}

        # Get basic stats from FBE
        try:
            fbe_stats = await fbe_service.get_offers_summary("fbe")
        except Exception:
            fbe_stats = {"total_offers": 0, "active_offers": 0}

        return {
            "accounts": {
                "main": {
                    "account_type": "MAIN",
                    "total_offers": main_stats.get("total_offers", 0),
                    "active_offers": main_stats.get("active_offers", 0),
                    "inactive_offers": main_stats.get("total_offers", 0)
                    - main_stats.get("active_offers", 0),
                    "status": (
                        "connected"
                        if main_stats.get("total_offers", 0) > 0
                        else "no_data"
                    ),
                },
                "fbe": {
                    "account_type": "FBE",
                    "total_offers": fbe_stats.get("total_offers", 0),
                    "active_offers": fbe_stats.get("active_offers", 0),
                    "inactive_offers": fbe_stats.get("total_offers", 0)
                    - fbe_stats.get("active_offers", 0),
                    "status": (
                        "connected"
                        if fbe_stats.get("total_offers", 0) > 0
                        else "no_data"
                    ),
                },
            },
            "summary": {
                "total_offers_across_accounts": main_stats.get("total_offers", 0)
                + fbe_stats.get("total_offers", 0),
                "total_active_offers": main_stats.get("active_offers", 0)
                + fbe_stats.get("active_offers", 0),
                "accounts_with_offers": sum(
                    1
                    for stats in [main_stats, fbe_stats]
                    if stats.get("total_offers", 0) > 0
                ),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ConfigurationError as e:
        return {
            "accounts": {
                "main": {"status": "not_configured"},
                "fbe": {"status": "not_configured"},
            },
            "summary": {
                "total_offers_across_accounts": 0,
                "total_active_offers": 0,
                "accounts_with_offers": 0,
            },
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get offers summary: {e!s}",
        )


@router.get("/search")
async def search_offers(
    query: str = Query(..., description="Search query"),
    account_type: Optional[EmagAccountType] = Query(
        None,
        description="Filter by account type",
    ),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(20, description="Items per page", ge=1, le=50),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Search for offers across eMAG accounts.

    - **query**: Search query for product name, SKU, or description
    - **account_type**: Filter by specific account type
    - **category_id**: Filter by category ID
    - **page**: Page number for pagination
    - **limit**: Number of items per page

    Searches across MAIN and FBE accounts unless filtered.
    """
    try:
        results = []

        # Search in MAIN account if not filtered to FBE only
        if account_type is None or account_type == EmagAccountType.MAIN:
            main_service = await get_emag_service_for_account(EmagAccountType.MAIN)
            try:
                main_results = await main_service.search_product_offers(
                    query=query,
                    category_id=category_id,
                    page=page,
                    limit=limit,
                )
                for offer in main_results.get("offers", []):
                    offer["_account_type"] = "main"
                results.extend(main_results.get("offers", []))
            except Exception as e:
                # Log error but continue with FBE search
                print(f"Error searching MAIN account: {e}")

        # Search in FBE account if not filtered to MAIN only
        if account_type is None or account_type == EmagAccountType.FBE:
            fbe_service = await get_emag_service_for_account(EmagAccountType.FBE)
            try:
                fbe_results = await fbe_service.search_product_offers(
                    query=query,
                    category_id=category_id,
                    page=page,
                    limit=limit,
                )
                for offer in fbe_results.get("offers", []):
                    offer["_account_type"] = "fbe"
                results.extend(fbe_results.get("offers", []))
            except Exception as e:
                # Log error but continue with other account
                print(f"Error searching FBE account: {e}")

        # Sort by relevance (you might want to implement proper scoring)
        results.sort(key=lambda x: x.get("name", "").lower())

        return {
            "query": query,
            "account_type_filter": account_type.value if account_type else None,
            "offers": results,
            "total_count": len(results),
            "page": page,
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search offers: {e!s}",
        )


@router.get("/{offer_id}")
async def get_offer_details(
    offer_id: str,
    account_type: Optional[EmagAccountType] = Query(
        None,
        description="Account type filter",
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get detailed information for a specific offer.

    - **offer_id**: The eMAG offer ID
    - **account_type**: Filter by account type (optional)

    Returns detailed offer information from the specified account.
    """
    try:
        # Try to find the offer in both accounts
        results = []

        if account_type is None or account_type == EmagAccountType.MAIN:
            main_service = await get_emag_service_for_account(EmagAccountType.MAIN)
            try:
                main_details = await main_service.get_offer_details(offer_id, "main")
                if main_details:
                    main_details["_account_type"] = "main"
                    results.append(main_details)
            except Exception as e:
                print(f"Error getting MAIN offer details: {e}")

        if account_type is None or account_type == EmagAccountType.FBE:
            fbe_service = await get_emag_service_for_account(EmagAccountType.FBE)
            try:
                fbe_details = await fbe_service.get_offer_details(offer_id, "fbe")
                if fbe_details:
                    fbe_details["_account_type"] = "fbe"
                    results.append(fbe_details)
            except Exception as e:
                print(f"Error getting FBE offer details: {e}")

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer {offer_id} not found in any eMAG account",
            )

        return {
            "offer_id": offer_id,
            "account_type_filter": account_type.value if account_type else None,
            "offers": results,
            "found_in_accounts": len(results),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get offer details: {e!s}",
        )
