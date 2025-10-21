#!/usr/bin/env python3
"""
Enhanced Campaign Management System for MagFlow ERP
Supports eMAG/FD campaigns with MultiDeals and date intervals
Based on API v4.4.8 specifications
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class CampaignType(Enum):
    """Campaign types supported by eMAG/FD"""
    STANDARD = "standard"
    FLASH_SALE = "flash_sale"
    MULTI_DEALS = "multi_deals"
    BUNDLE = "bundle"
    SEASONAL = "seasonal"

class DiscountType(Enum):
    """Discount types for campaigns"""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_X_GET_Y = "buy_x_get_y"

@dataclass
class DateInterval:
    """Date interval for MultiDeals campaigns"""
    start_date: datetime
    end_date: datetime
    voucher_discount: Decimal
    timezone_type: str = "marketplace"
    timezone: str = "UTC"
    index: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API"""
        return {
            "start_date": {
                "date": self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                "timezone_type": self.timezone_type,
                "timezone": self.timezone
            },
            "end_date": {
                "date": self.end_date.strftime('%Y-%m-%d %H:%M:%S'),
                "timezone_type": self.timezone_type,
                "timezone": self.timezone
            },
            "voucher_discount": float(self.voucher_discount),
            "index": self.index
        }

@dataclass
class CampaignProposal:
    """Campaign proposal for submission to marketplace"""
    id: str  # Internal campaign ID
    sale_price: Decimal
    stock: int
    max_qty_per_order: int | None = None
    post_campaign_sale_price: Decimal | None = None
    campaign_id: str | None = None
    not_available_post_campaign: bool = False
    voucher_discount: Decimal | None = None
    date_intervals: list[DateInterval] = field(default_factory=list)
    campaign_type: CampaignType = CampaignType.STANDARD

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API submission"""
        data = {
            "id": self.id,
            "sale_price": float(self.sale_price),
            "stock": self.stock,
            "not_available_post_campaign": 1 if self.not_available_post_campaign else 0
        }

        if self.max_qty_per_order is not None:
            data["max_qty_per_order"] = self.max_qty_per_order

        if self.post_campaign_sale_price is not None:
            data["post_campaign_sale_price"] = float(self.post_campaign_sale_price)

        if self.campaign_id:
            data["campaign_id"] = self.campaign_id

        if self.voucher_discount is not None:
            data["voucher_discount"] = float(self.voucher_discount)

        if self.date_intervals:
            data["date_intervals"] = [interval.to_dict() for interval in self.date_intervals]

        return data

@dataclass
class CampaignResponse:
    """Response from campaign API"""
    campaign_id: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, response_data: dict[str, Any]) -> 'CampaignResponse':
        """Create from API response"""
        return cls(
            campaign_id=response_data.get('campaign_id', ''),
            status=response_data.get('status', 'unknown'),
            message=response_data.get('message', ''),
            details=response_data
        )

@dataclass
class SmartDealsPriceCheck:
    """Smart Deals price check request/response"""
    product_id: str
    target_price: Decimal | None = None
    currency: str = "RON"
    is_eligible: bool = False
    recommended_price: Decimal | None = None
    confidence_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API"""
        return {
            "product_id": self.product_id,
            "target_price": float(self.target_price) if self.target_price else None,
            "currency": self.currency
        }

    @classmethod
    def from_api_response(cls, response_data: dict[str, Any]) -> 'SmartDealsPriceCheck':
        """Create from API response"""
        return cls(
            product_id=response_data.get('product_id', ''),
            target_price=Decimal(str(response_data.get('target_price', '0'))),
            currency=response_data.get('currency', 'RON'),
            is_eligible=response_data.get('is_eligible', False),
            recommended_price=Decimal(str(response_data.get('recommended_price', '0'))),
            confidence_score=float(response_data.get('confidence_score', 0.0))
        )

class CampaignManager:
    """Enhanced campaign management system"""

    def __init__(self, api_client):
        self.api_client = api_client
        self.campaign_cache: dict[str, CampaignProposal] = {}
        self.active_campaigns: dict[str, CampaignResponse] = {}

    async def create_campaign_proposal(self, proposal: CampaignProposal) -> CampaignResponse:
        """Create a new campaign proposal"""
        try:
            logger.info(f"Creating campaign proposal: {proposal.id}")

            # Prepare payload
            payload = {
                "data": proposal.to_dict()
            }

            # Make API call
            response = await self.api_client.make_request(
                "POST",
                f"{self.api_client.base_url}/campaign_proposals/save",
                json=payload
            )

            # Process response
            if response.get('isError', False):
                error_messages = response.get('messages', [])
                error_msg = error_messages[0] if error_messages else 'Unknown error'
                logger.error(f"Campaign proposal failed: {error_msg}")
                return CampaignResponse(
                    campaign_id=proposal.id,
                    status='failed',
                    message=error_msg,
                    details=response
                )

            # Cache the proposal
            self.campaign_cache[proposal.id] = proposal

            campaign_response = CampaignResponse.from_api_response(response)
            self.active_campaigns[proposal.id] = campaign_response

            logger.info(f"Campaign proposal created successfully: {campaign_response.campaign_id}")
            return campaign_response

        except Exception as e:
            logger.error(f"Failed to create campaign proposal: {e}")
            return CampaignResponse(
                campaign_id=proposal.id,
                status='error',
                message=str(e)
            )

    async def check_smart_deals_price(
        self,
        product_id: str,
        target_price: Decimal | None = None,
    ) -> SmartDealsPriceCheck:
        """Check if product is eligible for Smart Deals badge"""
        try:
            logger.info(f"Checking Smart Deals price for product: {product_id}")

            # Prepare query parameters
            params = f"productId={product_id}"
            if target_price:
                params += f"&targetPrice={float(target_price)}"

            # Make API call
            response = await self.api_client.make_request(
                "GET",
                f"{self.api_client.base_url}/smart-deals-price-check?{params}"
            )

            # Process response
            if response.get('isError', False):
                error_messages = response.get('messages', [])
                error_msg = error_messages[0] if error_messages else 'Unknown error'
                logger.error(f"Smart Deals price check failed: {error_msg}")
                return SmartDealsPriceCheck(
                    product_id=product_id,
                    is_eligible=False
                )

            smart_deals_check = SmartDealsPriceCheck.from_api_response(response)
            logger.info(f"Smart Deals check completed: eligible={smart_deals_check.is_eligible}")
            return smart_deals_check

        except Exception as e:
            logger.error(f"Failed to check Smart Deals price: {e}")
            return SmartDealsPriceCheck(
                product_id=product_id,
                is_eligible=False
            )

    async def create_multi_deals_campaign(
        self,
        product_id: str,
        base_price: Decimal,
        intervals: list[DateInterval],
    ) -> CampaignResponse:
        """Create a MultiDeals campaign with multiple date intervals"""
        try:
            logger.info(f"Creating MultiDeals campaign for product: {product_id}")

            # Create campaign proposal with intervals
            proposal = CampaignProposal(
                id=f"multi_deals_{product_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                sale_price=base_price,
                stock=100,  # Default stock, should be configurable
                max_qty_per_order=1,
                campaign_type=CampaignType.MULTI_DEALS,
                date_intervals=intervals
            )

            return await self.create_campaign_proposal(proposal)

        except Exception as e:
            logger.error(f"Failed to create MultiDeals campaign: {e}")
            return CampaignResponse(
                campaign_id=product_id,
                status='error',
                message=str(e)
            )

    async def create_flash_sale_campaign(self,
                                       product_id: str,
                                       sale_price: Decimal,
                                       original_price: Decimal,
                                       duration_hours: int = 24) -> CampaignResponse:
        """Create a flash sale campaign"""
        try:
            logger.info(f"Creating flash sale campaign for product: {product_id}")

            # Calculate discount percentage
            discount = ((original_price - sale_price) / original_price) * 100

            # Create time intervals
            now = datetime.utcnow()
            end_time = now + timedelta(hours=duration_hours)

            intervals = [
                DateInterval(
                    start_date=now,
                    end_date=end_time,
                    voucher_discount=Decimal(str(discount)),
                    index=0
                )
            ]

            # Create campaign proposal
            proposal = CampaignProposal(
                id=f"flash_sale_{product_id}_{now.strftime('%Y%m%d_%H%M%S')}",
                sale_price=sale_price,
                stock=50,  # Default stock for flash sales
                max_qty_per_order=1,
                post_campaign_sale_price=original_price,
                not_available_post_campaign=True,  # Make unavailable after campaign
                campaign_type=CampaignType.FLASH_SALE,
                date_intervals=intervals
            )

            return await self.create_campaign_proposal(proposal)

        except Exception as e:
            logger.error(f"Failed to create flash sale campaign: {e}")
            return CampaignResponse(
                campaign_id=product_id,
                status='error',
                message=str(e)
            )

    def validate_campaign_proposal(self, proposal: CampaignProposal) -> list[str]:
        """Validate campaign proposal before submission"""
        errors = []

        # Basic validations
        if proposal.sale_price <= 0:
            errors.append("Sale price must be greater than 0")

        if proposal.stock < 0:
            errors.append("Stock cannot be negative")

        if proposal.max_qty_per_order is not None and proposal.max_qty_per_order <= 0:
            errors.append("Max quantity per order must be greater than 0")

        # Date interval validations
        if proposal.date_intervals:
            for i, interval in enumerate(proposal.date_intervals):
                if interval.start_date >= interval.end_date:
                    errors.append(f"Interval {i}: Start date must be before end date")

                if interval.start_date < datetime.utcnow():
                    errors.append(f"Interval {i}: Start date cannot be in the past")

                if interval.voucher_discount <= 0 or interval.voucher_discount > 100:
                    errors.append(f"Interval {i}: Discount must be between 0 and 100")

        # Campaign type specific validations
        if proposal.campaign_type == CampaignType.MULTI_DEALS:
            if not proposal.date_intervals:
                errors.append("MultiDeals campaign must have date intervals")

            if len(proposal.date_intervals) < 2:
                errors.append("MultiDeals campaign should have at least 2 intervals")

        return errors

    async def bulk_create_campaigns(
        self,
        proposals: list[CampaignProposal],
    ) -> list[CampaignResponse]:
        """Create multiple campaign proposals in bulk"""
        results = []

        for proposal in proposals:
            # Validate proposal
            errors = self.validate_campaign_proposal(proposal)
            if errors:
                logger.error(f"Campaign proposal {proposal.id} has validation errors: {errors}")
                results.append(CampaignResponse(
                    campaign_id=proposal.id,
                    status='validation_failed',
                    message=', '.join(errors)
                ))
                continue

            # Create campaign
            result = await self.create_campaign_proposal(proposal)
            results.append(result)

            # Small delay to respect rate limits
            await asyncio.sleep(0.1)

        return results

    def get_campaign_statistics(self) -> dict[str, Any]:
        """Get campaign statistics"""
        total_campaigns = len(self.campaign_cache)
        active_campaigns = len([c for c in self.active_campaigns.values() if c.status == 'active'])

        return {
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'cached_campaigns': list(self.campaign_cache.keys()),
            'active_campaign_ids': [
                cid for cid, c in self.active_campaigns.items() if c.status == 'active'
            ]
        }

    def clear_campaign_cache(self):
        """Clear campaign cache"""
        self.campaign_cache.clear()
        self.active_campaigns.clear()
        logger.info("Campaign cache cleared")

# Factory function for easy usage
async def get_campaign_manager(api_client) -> CampaignManager:
    """Get or create campaign manager instance"""
    return CampaignManager(api_client)

# Export for easy usage
__all__ = [
    'CampaignManager',
    'CampaignProposal',
    'CampaignResponse',
    'CampaignType',
    'DiscountType',
    'DateInterval',
    'SmartDealsPriceCheck',
    'get_campaign_manager'
]
