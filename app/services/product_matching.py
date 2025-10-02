"""Product matching service for MagFlow ERP.

This service provides intelligent product matching between:
- Local product catalog (MagFlow products)
- Supplier products from 1688.com scraping
- Uses multiple algorithms for accurate matching
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.models.supplier import SupplierProduct
from app.models.product import Product

logger = logging.getLogger(__name__)


class TextSimilarityMatcher:
    """Text similarity matching for product names in Chinese vs Romanian."""

    def __init__(self):
        # In a real implementation, this would load ML models
        # For now, simple string similarity
        self.stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

    async def compare_names(self, chinese_name: str, romanian_name: str) -> float:
        """Compare Chinese product name with Romanian product name."""

        # Simple implementation - in production would use:
        # - Chinese to Pinyin conversion
        # - Semantic similarity models
        # - Keyword extraction and matching

        # For now, basic string similarity after cleaning
        chinese_clean = self._clean_text(chinese_name)
        romanian_clean = self._clean_text(romanian_name)

        # Simple Jaccard similarity for keywords
        chinese_words = set(chinese_clean.split())
        romanian_words = set(romanian_clean.split())

        if not chinese_words or not romanian_words:
            return 0.0

        intersection = chinese_words.intersection(romanian_words)
        union = chinese_words.union(romanian_words)

        jaccard_score = len(intersection) / len(union) if union else 0.0

        return min(jaccard_score * 2, 1.0)  # Scale up for better matching

    def _clean_text(self, text: str) -> str:
        """Clean text for comparison."""
        # Remove special characters, convert to lowercase
        cleaned = text.lower()
        cleaned = ''.join(c for c in cleaned if c.isalnum() or c.isspace())
        return ' '.join(word for word in cleaned.split() if word not in self.stop_words)


class ImageSimilarityMatcher:
    """Image similarity matching for product photos."""

    def __init__(self):
        # In production, this would use computer vision models like:
        # - ResNet for feature extraction
        # - Siamese networks for similarity
        # - Pre-trained models for product recognition
        pass

    async def compare_images(self, scraped_image_url: str, local_images: List[str]) -> float:
        """Compare scraped image with local product images."""

        # Placeholder implementation
        # In production, would:
        # 1. Download and process images
        # 2. Extract features using CNN
        # 3. Calculate similarity scores

        # For now, return a random score (would be replaced with actual CV)
        import random
        return random.uniform(0.3, 0.8)  # Placeholder similarity score


class AttributeMatcher:
    """Attribute-based matching for product specifications."""

    def __init__(self):
        pass

    def compare_attributes(self, scraped_specs: Dict[str, Any], local_specs: Dict[str, Any]) -> float:
        """Compare product specifications."""

        if not scraped_specs or not local_specs:
            return 0.0

        # Simple attribute matching
        # In production, would use more sophisticated comparison

        matching_attributes = 0
        total_attributes = max(len(scraped_specs), len(local_specs))

        if total_attributes == 0:
            return 0.0

        # Compare common attributes
        for key in scraped_specs:
            if key in local_specs:
                scraped_value = str(scraped_specs[key]).lower()
                local_value = str(local_specs[key]).lower()

                # Simple string matching for attribute values
                if scraped_value == local_value:
                    matching_attributes += 1
                elif scraped_value in local_value or local_value in scraped_value:
                    matching_attributes += 0.5

        return matching_attributes / total_attributes


class ProductMatchingService:
    """Main service for product matching operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.text_matcher = TextSimilarityMatcher()
        self.image_matcher = ImageSimilarityMatcher()
        self.attribute_matcher = AttributeMatcher()

    async def find_matches_for_supplier(
        self,
        supplier_id: int,
        confidence_threshold: float = 0.5,
        limit: int = 50
    ) -> List[SupplierProduct]:
        """Find potential product matches for a supplier."""

        # Get all active supplier products for this supplier
        supplier_products_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.is_active
            )
        ).options(selectinload(SupplierProduct.local_product))
        supplier_products_result = await self.db.execute(supplier_products_query)
        supplier_products = supplier_products_result.scalars().all()

        # Get all local products for comparison
        local_products_query = select(Product).where(Product.is_active)
        local_products_result = await self.db.execute(local_products_query)
        local_products = local_products_result.scalars().all()

        matches = []

        for supplier_product in supplier_products:
            if not supplier_product.manual_confirmed:  # Only process unconfirmed matches
                # Find best matches for this supplier product
                best_matches = await self._find_best_matches(
                    supplier_product,
                    local_products,
                    limit=5
                )

                # Update confidence scores
                for match in best_matches:
                    if match.confidence_score >= confidence_threshold:
                        matches.append(match)

        # Sort by confidence score
        matches.sort(key=lambda x: x.confidence_score, reverse=True)

        return matches[:limit]

    async def _find_best_matches(
        self,
        supplier_product: SupplierProduct,
        local_products: List[Product],
        limit: int = 5
    ) -> List[SupplierProduct]:
        """Find best matching local products for a supplier product."""

        scored_matches = []

        for local_product in local_products:
            # Skip if already mapped
            existing_query = select(SupplierProduct).where(
                and_(
                    SupplierProduct.local_product_id == local_product.id,
                    SupplierProduct.supplier_id == supplier_product.supplier_id,
                    SupplierProduct.manual_confirmed
                )
            )
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                continue

            # Calculate similarity scores
            text_score = await self.text_matcher.compare_names(
                supplier_product.supplier_product_name,
                local_product.name
            )

            image_score = await self.image_matcher.compare_images(
                supplier_product.supplier_image_url,
                [img for img in local_product.images.values()] if local_product.images else []
            )

            attr_score = self.attribute_matcher.compare_attributes(
                supplier_product.supplier_specifications or {},
                local_product.characteristics or {}
            )

            # Weighted final score
            final_score = (text_score * 0.4) + (image_score * 0.4) + (attr_score * 0.2)

            # Create match record if score is above threshold
            if final_score > 0.3:  # Minimum threshold
                match = SupplierProduct(
                    supplier_id=supplier_product.supplier_id,
                    local_product_id=local_product.id,
                    supplier_product_name=supplier_product.supplier_product_name,
                    supplier_product_url=supplier_product.supplier_product_url,
                    supplier_image_url=supplier_product.supplier_image_url,
                    supplier_price=supplier_product.supplier_price,
                    supplier_currency=supplier_product.supplier_currency,
                    supplier_specifications=supplier_product.supplier_specifications,
                    confidence_score=final_score,
                    manual_confirmed=False
                )
                scored_matches.append(match)

        # Sort by score and return top matches
        scored_matches.sort(key=lambda x: x.confidence_score, reverse=True)
        return scored_matches[:limit]

    async def confirm_match(self, match_id: int, user_id: int) -> SupplierProduct:
        """Confirm a product match."""

        query = select(SupplierProduct).where(SupplierProduct.id == match_id)
        result = await self.db.execute(query)
        match = result.scalar_one_or_none()

        if not match:
            raise ValueError(f"Match with ID {match_id} not found")

        match.manual_confirmed = True
        match.confirmed_by = user_id
        match.confirmed_at = datetime.utcnow()

        logger.info(f"Confirmed match {match_id} by user {user_id}")
        return match

    async def reject_match(self, match_id: int) -> None:
        """Reject a product match."""

        query = select(SupplierProduct).where(SupplierProduct.id == match_id)
        result = await self.db.execute(query)
        match = result.scalar_one_or_none()

        if not match:
            raise ValueError(f"Match with ID {match_id} not found")

        # Soft delete the match
        match.is_active = False
        logger.info(f"Rejected match {match_id}")

    async def auto_match_products_for_supplier(
        self,
        supplier_id: int,
        auto_confirm_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """Automatically match products for a supplier."""

        # Get unconfirmed supplier products
        unconfirmed_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                not SupplierProduct.manual_confirmed,
                SupplierProduct.is_active
            )
        )
        unconfirmed_result = await self.db.execute(unconfirmed_query)
        unconfirmed_products = unconfirmed_result.scalars().all()

        confirmed_count = 0
        rejected_count = 0

        for supplier_product in unconfirmed_products:
            # Get best match
            local_products_query = select(Product).where(Product.is_active)
            local_products_result = await self.db.execute(local_products_query)
            local_products = local_products_result.scalars().all()

            best_matches = await self._find_best_matches(supplier_product, local_products, limit=1)

            if best_matches and best_matches[0].confidence_score >= auto_confirm_threshold:
                # Auto-confirm high confidence matches
                best_match = best_matches[0]
                best_match.manual_confirmed = True
                best_match.confirmed_at = datetime.utcnow()
                confirmed_count += 1
                logger.info(f"Auto-confirmed match for supplier product {supplier_product.id}")
            else:
                # Mark low confidence matches as inactive
                supplier_product.is_active = False
                rejected_count += 1

        return {
            "confirmed": confirmed_count,
            "rejected": rejected_count,
            "total_processed": len(unconfirmed_products)
        }

    async def get_matching_statistics(self, supplier_id: Optional[int] = None) -> Dict[str, Any]:
        """Get matching statistics."""

        base_query = select(SupplierProduct)

        if supplier_id:
            base_query = base_query.where(SupplierProduct.supplier_id == supplier_id)

        # Get overall statistics
        total_query = base_query
        total_result = await self.db.execute(total_query)
        total_matches = len(total_result.scalars().all())

        # Get confirmed matches
        confirmed_query = base_query.where(SupplierProduct.manual_confirmed)
        confirmed_result = await self.db.execute(confirmed_query)
        confirmed_matches = len(confirmed_result.scalars().all())

        # Get average confidence score
        avg_confidence_query = select(func.avg(SupplierProduct.confidence_score)).where(
            SupplierProduct.confidence_score > 0
        )
        avg_confidence_result = await self.db.execute(avg_confidence_query)
        avg_confidence = avg_confidence_result.scalar() or 0

        return {
            "total_matches": total_matches,
            "confirmed_matches": confirmed_matches,
            "pending_matches": total_matches - confirmed_matches,
            "average_confidence": round(float(avg_confidence), 3),
            "confirmation_rate": round(confirmed_matches / total_matches * 100, 2) if total_matches > 0 else 0
        }
