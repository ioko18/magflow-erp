"""
Stock Synchronization API Endpoints.

Provides intelligent stock management across MAIN and FBE accounts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.security.jwt import get_current_user
from app.models.user import User
from app.services.stock_sync_service import StockSyncService

router = APIRouter(prefix="/stock-sync", tags=["stock-sync"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StockTransferRequest(BaseModel):
    """Request for stock transfer suggestion."""
    sku: str = Field(..., description="Product SKU")
    from_account: str = Field(..., description="Source account: main or fbe")
    to_account: str = Field(..., description="Destination account: main or fbe")
    amount: int = Field(..., gt=0, description="Number of units to transfer")


# ============================================================================
# Stock Analysis Endpoints
# ============================================================================

@router.get("/analyze/{sku}")
async def analyze_stock_distribution(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze stock distribution for a product across MAIN and FBE accounts.
    
    Provides:
    - Current stock levels on both accounts
    - Competition analysis
    - Buy button rank comparison
    - Actionable recommendations
    - Priority level
    
    Example use case:
    - Product EMG331 has 0 stock on MAIN but 26 on FBE
    - MAIN has 2 offers (competition)
    - Recommendation: Transfer stock from FBE to MAIN to regain buy button
    """
    service = StockSyncService(db)
    analysis = await service.analyze_stock_distribution(sku)
    
    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])
    
    return {
        "status": "success",
        "data": analysis
    }


@router.get("/alerts")
async def get_stock_sync_alerts(
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get products that need stock synchronization attention.
    
    Returns products with:
    - Zero stock with competition (HIGH priority)
    - Imbalanced stock distribution
    - Offers not updated in 7+ days (eMAG best practice)
    
    Use this endpoint to:
    - Daily monitoring of stock issues
    - Identify products losing buy button
    - Ensure weekly offer updates
    """
    service = StockSyncService(db)
    alerts = await service.get_products_needing_stock_sync(limit)
    
    # Categorize by priority
    high_priority = [a for a in alerts if "zero_stock_with_competition" in a["issues"]]
    medium_priority = [a for a in alerts if "needs_weekly_update" in a["issues"] and a not in high_priority]
    
    return {
        "status": "success",
        "data": {
            "alerts": alerts,
            "summary": {
                "total": len(alerts),
                "high_priority": len(high_priority),
                "medium_priority": len(medium_priority)
            },
            "categorized": {
                "high_priority": high_priority,
                "medium_priority": medium_priority
            }
        }
    }


# ============================================================================
# Stock Transfer Endpoints
# ============================================================================

@router.post("/transfer/suggest")
async def suggest_stock_transfer(
    request: StockTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get stock transfer suggestion with validation and impact analysis.
    
    Before executing a stock transfer, use this endpoint to:
    - Validate sufficient stock availability
    - Analyze impact on buy button
    - Get warnings about potential issues
    - Receive recommendation (proceed or review)
    
    Example:
    ```json
    {
      "sku": "EMG331",
      "from_account": "fbe",
      "to_account": "main",
      "amount": 10
    }
    ```
    
    Response includes:
    - Current and proposed stock levels
    - Impact on buy button for each account
    - Warnings if transfer creates issues
    - Final recommendation
    """
    if request.from_account not in ["main", "fbe"]:
        raise HTTPException(status_code=400, detail="from_account must be 'main' or 'fbe'")
    
    if request.to_account not in ["main", "fbe"]:
        raise HTTPException(status_code=400, detail="to_account must be 'main' or 'fbe'")
    
    if request.from_account == request.to_account:
        raise HTTPException(status_code=400, detail="from_account and to_account must be different")
    
    service = StockSyncService(db)
    suggestion = await service.suggest_stock_transfer(
        sku=request.sku,
        from_account=request.from_account,
        to_account=request.to_account,
        amount=request.amount
    )
    
    if "error" in suggestion:
        raise HTTPException(status_code=400, detail=suggestion["error"])
    
    return {
        "status": "success",
        "data": suggestion
    }


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/dashboard/summary")
async def get_stock_sync_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get stock synchronization dashboard summary.
    
    Provides overview of:
    - Products with zero stock and competition
    - Products needing weekly updates
    - Stock distribution statistics
    """
    service = StockSyncService(db)
    alerts = await service.get_products_needing_stock_sync(limit=1000)
    
    # Categorize issues
    zero_stock_competition = len([a for a in alerts if "zero_stock_with_competition" in a["issues"]])
    needs_update = len([a for a in alerts if "needs_weekly_update" in a["issues"]])
    
    return {
        "status": "success",
        "data": {
            "total_alerts": len(alerts),
            "critical_issues": {
                "zero_stock_with_competition": zero_stock_competition,
                "description": "Products losing buy button due to 0 stock"
            },
            "maintenance_needed": {
                "needs_weekly_update": needs_update,
                "description": "Products not updated in 7+ days (eMAG best practice)"
            }
        }
    }


# ============================================================================
# Bulk Operations
# ============================================================================

class BulkAnalyzeRequest(BaseModel):
    """Request for bulk stock analysis."""
    skus: list[str] = Field(..., description="List of SKUs to analyze")


@router.post("/bulk-analyze")
async def bulk_analyze_stock(
    request: BulkAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze stock distribution for multiple products at once.
    
    Useful for:
    - Batch analysis of product category
    - Daily stock review
    - Identifying patterns across products
    """
    service = StockSyncService(db)
    results = []
    
    for sku in request.skus:
        try:
            analysis = await service.analyze_stock_distribution(sku)
            results.append(analysis)
        except Exception as e:
            results.append({
                "sku": sku,
                "error": str(e)
            })
    
    # Summary statistics
    action_required_count = sum(1 for r in results if r.get("action_required", False))
    high_priority_count = sum(1 for r in results if r.get("priority") == "high")
    
    return {
        "status": "success",
        "data": {
            "results": results,
            "summary": {
                "total_analyzed": len(results),
                "action_required": action_required_count,
                "high_priority": high_priority_count
            }
        }
    }
