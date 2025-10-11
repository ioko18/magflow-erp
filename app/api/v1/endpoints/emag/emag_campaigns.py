"""
eMAG Campaign Management API Endpoints for MagFlow ERP.

This module provides REST API endpoints for managing eMAG campaigns:
- Propose products to campaigns
- MultiDeals campaigns with date intervals
- Stock-in-site campaigns
- Voucher-based campaigns

Implements eMAG API v4.4.9 campaign features.
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config.emag_config import get_emag_config
from app.core.logging import get_logger
from app.db import get_db
from app.models.user import User
from app.services.emag.emag_api_client import EmagApiClient

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models for request/response
class DateInterval(BaseModel):
    """Date interval for MultiDeals campaigns."""

    start_date: str = Field(
        ..., description="Start date in format YYYY-MM-DD HH:MM:SS.SSSSSS"
    )
    end_date: str = Field(
        ..., description="End date in format YYYY-MM-DD HH:MM:SS.SSSSSS"
    )
    voucher_discount: int = Field(
        ..., ge=10, le=100, description="Discount percentage for this interval"
    )
    index: int = Field(..., ge=1, le=30, description="Display order index (1-30)")
    timezone: str = Field(default="Europe/Bucharest", description="Timezone")

    def to_emag_format(self) -> dict[str, Any]:
        """Convert to eMAG API format."""
        return {
            "start_date": {
                "date": self.start_date,
                "timezone_type": 3,
                "timezone": self.timezone,
            },
            "end_date": {
                "date": self.end_date,
                "timezone_type": 3,
                "timezone": self.timezone,
            },
            "voucher_discount": self.voucher_discount,
            "index": self.index,
        }


class CampaignProposalRequest(BaseModel):
    """Request model for campaign proposal."""

    product_id: int = Field(..., description="Seller internal product ID")
    campaign_id: int = Field(..., description="eMAG campaign ID")
    sale_price: float = Field(..., gt=0, description="Campaign price without VAT")
    stock: int = Field(..., ge=0, le=255, description="Stock reserved for campaign")
    account_type: str = Field(
        default="main", description="Account type: 'main' or 'fbe'"
    )

    # Optional fields
    max_qty_per_order: int | None = Field(
        None, description="Max quantity per order (required for Stock-in-site)"
    )
    voucher_discount: int | None = Field(
        None, ge=10, le=100, description="Voucher discount percentage"
    )
    post_campaign_sale_price: float | None = Field(
        None, gt=0, description="Price after campaign ends"
    )
    not_available_post_campaign: bool = Field(
        False, description="Deactivate offer after campaign"
    )

    # MultiDeals specific
    date_intervals: list[DateInterval] | None = Field(
        None, description="Date intervals for MultiDeals campaigns"
    )

    @field_validator("date_intervals")
    @classmethod
    def validate_date_intervals(cls, v):
        """Validate date intervals for MultiDeals."""
        if v is not None:
            if len(v) > 30:
                raise ValueError("Maximum 30 date intervals allowed")
            # Check for unique indices
            indices = [interval.index for interval in v]
            if len(indices) != len(set(indices)):
                raise ValueError("Date interval indices must be unique")
        return v


class CampaignProposalResponse(BaseModel):
    """Response model for campaign proposal."""

    status: str
    message: str
    product_id: int
    campaign_id: int
    data: dict[str, Any] | None = None
    error: str | None = None


class BulkCampaignProposalRequest(BaseModel):
    """Request model for bulk campaign proposals."""

    proposals: list[CampaignProposalRequest] = Field(
        ..., max_items=50, description="List of campaign proposals (max 50)"
    )


class BulkCampaignProposalResponse(BaseModel):
    """Response model for bulk campaign proposals."""

    status: str
    message: str
    summary: dict[str, Any]
    results: list[dict[str, Any]]


# API Endpoints


@router.post("/propose", response_model=CampaignProposalResponse)
async def propose_to_campaign(
    request: CampaignProposalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignProposalResponse:
    """
    Propose a product to an eMAG campaign.

    This endpoint allows you to submit product offers to eMAG campaigns including:
    - Standard campaigns
    - Stock-in-site campaigns (requires max_qty_per_order)
    - MultiDeals campaigns (requires date_intervals)
    - Voucher-based campaigns

    Args:
        request: Campaign proposal details

    Returns:
        CampaignProposalResponse with proposal status
    """
    try:
        config = get_emag_config(request.account_type)

        async with EmagApiClient(
            username=config.api_username,
            password=config.api_password,
            base_url=config.base_url,
        ) as client:
            # Convert date intervals to eMAG format if present
            date_intervals_emag = None
            if request.date_intervals:
                date_intervals_emag = [
                    interval.to_emag_format() for interval in request.date_intervals
                ]

            result = await client.propose_to_campaign(
                product_id=request.product_id,
                campaign_id=request.campaign_id,
                sale_price=request.sale_price,
                stock=request.stock,
                max_qty_per_order=request.max_qty_per_order,
                voucher_discount=request.voucher_discount,
                post_campaign_sale_price=request.post_campaign_sale_price,
                not_available_post_campaign=request.not_available_post_campaign,
                date_intervals=date_intervals_emag,
            )

            if result.get("isError"):
                error_msg = result.get("messages", [{}])[0].get("text", "Unknown error")
                logger.warning(
                    f"Campaign proposal error for product {request.product_id}: {error_msg}"
                )
                return CampaignProposalResponse(
                    status="failed",
                    message="Campaign proposal failed",
                    product_id=request.product_id,
                    campaign_id=request.campaign_id,
                    error=error_msg,
                )

            return CampaignProposalResponse(
                status="success",
                message="Product successfully proposed to campaign",
                product_id=request.product_id,
                campaign_id=request.campaign_id,
                data=result.get("results"),
            )

    except Exception as e:
        logger.error(
            f"Error proposing product {request.product_id} to campaign {request.campaign_id}: {e}"
        )
        return CampaignProposalResponse(
            status="failed",
            message="Internal error",
            product_id=request.product_id,
            campaign_id=request.campaign_id,
            error=str(e),
        )


@router.post("/propose/bulk", response_model=BulkCampaignProposalResponse)
async def bulk_propose_to_campaigns(
    request: BulkCampaignProposalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkCampaignProposalResponse:
    """
    Propose multiple products to campaigns in bulk.

    This endpoint processes multiple campaign proposals efficiently with:
    - Automatic batching
    - Individual error tracking
    - Progress reporting

    Args:
        request: Bulk campaign proposals (max 50)

    Returns:
        BulkCampaignProposalResponse with results for each proposal
    """
    import asyncio

    results = []
    total_success = 0
    total_failed = 0

    # Group by account type for efficiency
    proposals_by_account = {}
    for proposal in request.proposals:
        account = proposal.account_type.lower()
        if account not in proposals_by_account:
            proposals_by_account[account] = []
        proposals_by_account[account].append(proposal)

    # Process each account's proposals
    for account_type, account_proposals in proposals_by_account.items():
        try:
            config = get_emag_config(account_type)

            async with EmagApiClient(
                username=config.api_username,
                password=config.api_password,
                base_url=config.base_url,
            ) as client:
                # Process proposals
                for proposal in account_proposals:
                    try:
                        # Convert date intervals if present
                        date_intervals_emag = None
                        if proposal.date_intervals:
                            date_intervals_emag = [
                                interval.to_emag_format()
                                for interval in proposal.date_intervals
                            ]

                        result = await client.propose_to_campaign(
                            product_id=proposal.product_id,
                            campaign_id=proposal.campaign_id,
                            sale_price=proposal.sale_price,
                            stock=proposal.stock,
                            max_qty_per_order=proposal.max_qty_per_order,
                            voucher_discount=proposal.voucher_discount,
                            post_campaign_sale_price=proposal.post_campaign_sale_price,
                            not_available_post_campaign=proposal.not_available_post_campaign,
                            date_intervals=date_intervals_emag,
                        )

                        if result.get("isError"):
                            error_msg = result.get("messages", [{}])[0].get(
                                "text", "Unknown error"
                            )
                            results.append(
                                {
                                    "product_id": proposal.product_id,
                                    "campaign_id": proposal.campaign_id,
                                    "status": "failed",
                                    "error": error_msg,
                                }
                            )
                            total_failed += 1
                        else:
                            results.append(
                                {
                                    "product_id": proposal.product_id,
                                    "campaign_id": proposal.campaign_id,
                                    "status": "success",
                                    "data": result.get("results"),
                                }
                            )
                            total_success += 1

                        # Rate limiting
                        await asyncio.sleep(0.4)  # ~3 requests per second

                    except Exception as e:
                        logger.error(
                            f"Error processing proposal for product {proposal.product_id}: {e}"
                        )
                        results.append(
                            {
                                "product_id": proposal.product_id,
                                "campaign_id": proposal.campaign_id,
                                "status": "failed",
                                "error": str(e),
                            }
                        )
                        total_failed += 1

        except Exception as e:
            logger.error(
                f"Error processing bulk proposals for account {account_type}: {e}"
            )
            # Mark remaining proposals as failed
            for proposal in account_proposals:
                if not any(r["product_id"] == proposal.product_id for r in results):
                    results.append(
                        {
                            "product_id": proposal.product_id,
                            "campaign_id": proposal.campaign_id,
                            "status": "failed",
                            "error": f"Batch processing error: {str(e)}",
                        }
                    )
                    total_failed += 1

    return BulkCampaignProposalResponse(
        status="completed",
        message=f"Processed {len(request.proposals)} proposals: {total_success} succeeded, {total_failed} failed",
        summary={
            "total": len(request.proposals),
            "success": total_success,
            "failed": total_failed,
            "success_rate": round((total_success / len(request.proposals)) * 100, 2)
            if request.proposals
            else 0,
        },
        results=results,
    )


@router.get("/templates/multideals")
async def get_multideals_template(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get a template for MultiDeals campaign proposal.

    Returns a sample structure for creating MultiDeals campaigns with date intervals.
    """
    return {
        "example": {
            "product_id": 12345,
            "campaign_id": 350,
            "sale_price": 89.99,
            "stock": 50,
            "account_type": "main",
            "date_intervals": [
                {
                    "start_date": "2025-10-01 00:00:00.000000",
                    "end_date": "2025-10-02 23:59:59.000000",
                    "voucher_discount": 10,
                    "index": 1,
                    "timezone": "Europe/Bucharest",
                },
                {
                    "start_date": "2025-10-03 00:00:00.000000",
                    "end_date": "2025-10-04 23:59:59.000000",
                    "voucher_discount": 15,
                    "index": 2,
                    "timezone": "Europe/Bucharest",
                },
            ],
        },
        "notes": [
            "Maximum 30 date intervals allowed",
            "Indices must be unique and incrementing",
            "Voucher discount: 10-100%",
            "Dates in format: YYYY-MM-DD HH:MM:SS.SSSSSS",
        ],
    }


__all__ = ["router"]
