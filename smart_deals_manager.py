#!/usr/bin/env python3
"""
Smart Deals Integration System for MagFlow ERP
Implements smart-deals-price-check functionality and automated badge management
Based on eMAG API v4.4.8 specifications
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SmartDealsEligibility(Enum):
    """Smart Deals eligibility status"""
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    PENDING_REVIEW = "pending_review"
    REQUIRES_PRICE_ADJUSTMENT = "requires_price_adjustment"
    INSUFFICIENT_DATA = "insufficient_data"

class SmartDealsType(Enum):
    """Smart Deals badge types"""
    FULL = 1          # Full Smart Deals eligibility
    EASYBOX = 2       # EasyBox delivery eligible
    HD = 3            # Heavy Duty delivery eligible

@dataclass
class SmartDealsAnalysis:
    """Smart Deals analysis result"""
    product_id: str
    eligibility: SmartDealsEligibility
    confidence_score: float
    recommended_price: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    price_gap: Optional[Decimal] = None
    analysis_details: Dict[str, Any] = field(default_factory=dict)
    last_analysis: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "product_id": self.product_id,
            "eligibility": self.eligibility.value,
            "confidence_score": self.confidence_score,
            "recommended_price": float(self.recommended_price) if self.recommended_price else None,
            "target_price": float(self.target_price) if self.target_price else None,
            "current_price": float(self.current_price) if self.current_price else None,
            "price_gap": float(self.price_gap) if self.price_gap else None,
            "analysis_details": self.analysis_details,
            "last_analysis": self.last_analysis.isoformat()
        }

@dataclass
class SmartDealsRecommendation:
    """Recommendation for Smart Deals optimization"""
    product_id: str
    action: str
    current_price: Decimal
    recommended_price: Decimal
    expected_benefit: str
    implementation_effort: str
    risk_level: str
    reasoning: str

class SmartDealsManager:
    """Smart Deals management and optimization system"""

    def __init__(self, api_client):
        self.api_client = api_client
        self.analysis_cache: Dict[str, SmartDealsAnalysis] = {}
        self.eligibility_cache: Dict[str, SmartDealsEligibility] = {}

        # Smart Deals thresholds and parameters
        self.eligibility_thresholds = {
            'min_confidence_score': 0.7,
            'max_price_gap_percent': 15,
            'min_competitor_offers': 3,
            'analysis_validity_hours': 24
        }

    async def check_smart_deals_eligibility(self, product_id: str,
                                          current_price: Optional[Decimal] = None) -> SmartDealsAnalysis:
        """Check if product is eligible for Smart Deals badge"""

        # Check cache first
        cached_analysis = self.analysis_cache.get(product_id)
        if cached_analysis and self._is_analysis_valid(cached_analysis):
            logger.info(f"Using cached Smart Deals analysis for product {product_id}")
            return cached_analysis

        try:
            logger.info(f"Checking Smart Deals eligibility for product: {product_id}")

            # Make API call to check Smart Deals price
            response = await self.api_client.make_request(
                "GET",
                f"{self.api_client.base_url}/smart-deals-price-check",
                params={"productId": product_id}
            )

            # Process API response
            if response.get('isError', False):
                error_messages = response.get('messages', [])
                error_msg = error_messages[0] if error_messages else 'Unknown API error'
                logger.error(f"Smart Deals check failed: {error_msg}")

                return SmartDealsAnalysis(
                    product_id=product_id,
                    eligibility=SmartDealsEligibility.NOT_ELIGIBLE,
                    confidence_score=0.0,
                    analysis_details={'api_error': error_msg}
                )

            # Extract data from response
            api_eligible = response.get('is_eligible', False)
            confidence_score = float(response.get('confidence_score', 0.0))
            recommended_price = Decimal(str(response.get('recommended_price', '0')))
            target_price = Decimal(str(response.get('target_price', '0')))

            # Determine eligibility
            eligibility = self._determine_eligibility(
                api_eligible, confidence_score, current_price, target_price
            )

            # Create analysis
            analysis = SmartDealsAnalysis(
                product_id=product_id,
                eligibility=eligibility,
                confidence_score=confidence_score,
                recommended_price=recommended_price,
                target_price=target_price,
                current_price=current_price,
                price_gap=self._calculate_price_gap(current_price, target_price),
                analysis_details={
                    'api_response': response,
                    'eligibility_score': confidence_score,
                    'market_analysis': response.get('market_analysis', {})
                }
            )

            # Cache the result
            self.analysis_cache[product_id] = analysis
            self.eligibility_cache[product_id] = eligibility

            logger.info(f"Smart Deals analysis completed for {product_id}: {eligibility.value}")
            return analysis

        except Exception as e:
            logger.error(f"Failed to check Smart Deals eligibility: {e}")
            return SmartDealsAnalysis(
                product_id=product_id,
                eligibility=SmartDealsEligibility.NOT_ELIGIBLE,
                confidence_score=0.0,
                analysis_details={'error': str(e)}
            )

    def _determine_eligibility(self, api_eligible: bool, confidence_score: float,
                             current_price: Optional[Decimal], target_price: Optional[Decimal]) -> SmartDealsEligibility:
        """Determine Smart Deals eligibility based on various factors"""

        if not api_eligible:
            return SmartDealsEligibility.NOT_ELIGIBLE

        if confidence_score < self.eligibility_thresholds['min_confidence_score']:
            return SmartDealsEligibility.INSUFFICIENT_DATA

        if current_price and target_price:
            price_gap = abs(current_price - target_price) / current_price * 100
            if price_gap > self.eligibility_thresholds['max_price_gap_percent']:
                return SmartDealsEligibility.REQUIRES_PRICE_ADJUSTMENT

        return SmartDealsEligibility.ELIGIBLE

    def _calculate_price_gap(self, current_price: Optional[Decimal], target_price: Optional[Decimal]) -> Optional[Decimal]:
        """Calculate price gap between current and target prices"""
        if not current_price or not target_price:
            return None

        return abs(current_price - target_price)

    def _is_analysis_valid(self, analysis: SmartDealsAnalysis) -> bool:
        """Check if cached analysis is still valid"""
        age = datetime.utcnow() - analysis.last_analysis
        return age.total_seconds() < (self.eligibility_thresholds['analysis_validity_hours'] * 3600)

    async def optimize_for_smart_deals(self, product_id: str, current_price: Decimal,
                                     max_price_adjustment: float = 0.15) -> SmartDealsRecommendation:
        """Optimize product pricing for Smart Deals eligibility"""

        analysis = await self.check_smart_deals_eligibility(product_id, current_price)

        if analysis.eligibility == SmartDealsEligibility.ELIGIBLE:
            return SmartDealsRecommendation(
                product_id=product_id,
                action="maintain_current_price",
                current_price=current_price,
                recommended_price=current_price,
                expected_benefit="Already eligible for Smart Deals badge",
                implementation_effort="None required",
                risk_level="Low",
                reasoning=f"Product meets Smart Deals criteria with {analysis.confidence_score:.2f} confidence"
            )

        elif analysis.eligibility == SmartDealsEligibility.REQUIRES_PRICE_ADJUSTMENT:
            if analysis.recommended_price:
                price_adjustment = abs(current_price - analysis.recommended_price) / current_price

                if price_adjustment <= max_price_adjustment:
                    return SmartDealsRecommendation(
                        product_id=product_id,
                        action="adjust_price",
                        current_price=current_price,
                        recommended_price=analysis.recommended_price,
                        expected_benefit=f"Gain Smart Deals badge with {analysis.confidence_score:.2f} confidence",
                        implementation_effort="Price update required",
                        risk_level="Medium" if price_adjustment > 0.1 else "Low",
                        reasoning=f"Price adjustment of {price_adjustment:.1%} needed to achieve Smart Deals eligibility"
                    )
                else:
                    return SmartDealsRecommendation(
                        product_id=product_id,
                        action="consider_alternative",
                        current_price=current_price,
                        recommended_price=current_price,
                        expected_benefit="Alternative optimization strategies available",
                        implementation_effort="Analysis and decision required",
                        risk_level="High",
                        reasoning=f"Required price adjustment ({price_adjustment:.1%}) exceeds maximum threshold ({max_price_adjustment:.1%})"
                    )

        elif analysis.eligibility == SmartDealsEligibility.INSUFFICIENT_DATA:
            return SmartDealsRecommendation(
                product_id=product_id,
                action="gather_more_data",
                current_price=current_price,
                recommended_price=current_price,
                expected_benefit="Improve Smart Deals eligibility assessment",
                implementation_effort="Data collection and analysis",
                risk_level="Low",
                reasoning="Insufficient market data for confident Smart Deals recommendation"
            )

        else:
            return SmartDealsRecommendation(
                product_id=product_id,
                action="not_applicable",
                current_price=current_price,
                recommended_price=current_price,
                expected_benefit="Product not suitable for Smart Deals",
                implementation_effort="None",
                risk_level="Low",
                reasoning=f"Product does not meet Smart Deals criteria (confidence: {analysis.confidence_score:.2f})"
            )

    async def batch_check_eligibility(self, product_ids: List[str]) -> Dict[str, SmartDealsAnalysis]:
        """Check Smart Deals eligibility for multiple products"""
        results = {}

        for product_id in product_ids:
            try:
                analysis = await self.check_smart_deals_eligibility(product_id)
                results[product_id] = analysis

                # Small delay to respect rate limits
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to check eligibility for {product_id}: {e}")
                results[product_id] = SmartDealsAnalysis(
                    product_id=product_id,
                    eligibility=SmartDealsEligibility.NOT_ELIGIBLE,
                    confidence_score=0.0,
                    analysis_details={'error': str(e)}
                )

        return results

    async def get_smart_deals_statistics(self, product_ids: List[str]) -> Dict[str, Any]:
        """Get Smart Deals statistics for a list of products"""

        if not product_ids:
            return {'error': 'No product IDs provided'}

        analyses = await self.batch_check_eligibility(product_ids)

        stats = {
            'total_products': len(product_ids),
            'eligible_products': 0,
            'not_eligible_products': 0,
            'pending_review_products': 0,
            'requires_adjustment_products': 0,
            'insufficient_data_products': 0,
            'average_confidence': 0.0,
            'recommendations': []
        }

        confidences = []

        for product_id, analysis in analyses.items():
            stats[f'{analysis.eligibility.value}_products'] += 1
            confidences.append(analysis.confidence_score)

            if analysis.eligibility == SmartDealsEligibility.ELIGIBLE:
                stats['eligible_products'] += 1
            elif analysis.eligibility == SmartDealsEligibility.NOT_ELIGIBLE:
                stats['not_eligible_products'] += 1
            elif analysis.eligibility == SmartDealsEligibility.PENDING_REVIEW:
                stats['pending_review_products'] += 1
            elif analysis.eligibility == SmartDealsEligibility.REQUIRES_PRICE_ADJUSTMENT:
                stats['requires_adjustment_products'] += 1
            elif analysis.eligibility == SmartDealsEligibility.INSUFFICIENT_DATA:
                stats['insufficient_data_products'] += 1

            # Generate recommendations
            if analysis.current_price:
                recommendation = await self.optimize_for_smart_deals(
                    product_id, analysis.current_price
                )
                stats['recommendations'].append({
                    'product_id': product_id,
                    'recommendation': recommendation.action,
                    'current_price': float(analysis.current_price),
                    'recommended_price': float(recommendation.recommended_price),
                    'expected_benefit': recommendation.expected_benefit
                })

        stats['average_confidence'] = sum(confidences) / len(confidences) if confidences else 0.0

        return stats

    def clear_cache(self):
        """Clear analysis and eligibility caches"""
        self.analysis_cache.clear()
        self.eligibility_cache.clear()
        logger.info("Smart Deals cache cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        return {
            'cached_analyses': len(self.analysis_cache),
            'cached_eligibilities': len(self.eligibility_cache),
            'cache_expiry_hours': self.eligibility_thresholds['analysis_validity_hours']
        }

# Factory function for easy usage
async def get_smart_deals_manager(api_client) -> SmartDealsManager:
    """Get or create Smart Deals manager instance"""
    return SmartDealsManager(api_client)

# Export for easy usage
__all__ = [
    'SmartDealsManager',
    'SmartDealsAnalysis',
    'SmartDealsRecommendation',
    'SmartDealsEligibility',
    'SmartDealsType',
    'get_smart_deals_manager'
]
