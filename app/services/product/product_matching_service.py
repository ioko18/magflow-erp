"""Product matching service for supplier product comparison.

This service implements intelligent matching algorithms to group similar products
from different suppliers based on:
- Text similarity (Chinese and translated names)
- Image similarity (perceptual hashing and feature extraction)
- Price similarity (for validation)
"""

import hashlib
import re
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier
from app.models.supplier_matching import (
    MatchingStatus,
    ProductMatchingGroup,
    ProductMatchingScore,
    SupplierRawProduct,
)


class ProductMatchingService:
    """Service for matching similar products from different suppliers."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

        # Matching thresholds
        self.TEXT_SIMILARITY_THRESHOLD = 0.70
        self.IMAGE_SIMILARITY_THRESHOLD = 0.85
        self.HYBRID_THRESHOLD = 0.75

        # Weights for hybrid matching
        self.TEXT_WEIGHT = 0.6
        self.IMAGE_WEIGHT = 0.4

    # ==================== TEXT SIMILARITY ====================

    def normalize_chinese_text(self, text: str) -> str:
        """Normalize Chinese text for comparison.

        - Remove special characters
        - Convert to lowercase
        - Remove extra whitespace
        """
        if not text:
            return ""

        # Remove common noise words
        noise_words = ["的", "了", "和", "与", "或", "及"]
        for word in noise_words:
            text = text.replace(word, "")

        # Remove special characters but keep Chinese characters
        text = re.sub(r"[^\w\s\u4e00-\u9fff]", "", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        return text.strip().lower()

    def calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts.

        Jaccard similarity = |A ∩ B| / |A ∪ B|
        """
        if not text1 or not text2:
            return 0.0

        # Convert to character sets (works well for Chinese)
        set1 = set(text1)
        set2 = set(text2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def calculate_ngram_similarity(self, text1: str, text2: str, n: int = 2) -> float:
        """Calculate n-gram similarity between two texts.

        Works well for Chinese text comparison.
        """
        if not text1 or not text2:
            return 0.0

        def get_ngrams(text: str, n: int) -> set:
            """Extract n-grams from text."""
            return {text[i : i + n] for i in range(len(text) - n + 1)}

        ngrams1 = get_ngrams(text1, n)
        ngrams2 = get_ngrams(text2, n)

        if not ngrams1 or not ngrams2:
            return 0.0

        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))

        return intersection / union if union > 0 else 0.0

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate overall text similarity using multiple methods.

        Combines Jaccard and n-gram similarity for robust matching.
        """
        # Normalize texts
        norm1 = self.normalize_chinese_text(text1)
        norm2 = self.normalize_chinese_text(text2)

        if not norm1 or not norm2:
            return 0.0

        # Calculate different similarities
        jaccard = self.calculate_jaccard_similarity(norm1, norm2)
        bigram = self.calculate_ngram_similarity(norm1, norm2, n=2)
        trigram = self.calculate_ngram_similarity(norm1, norm2, n=3)

        # Weighted average: prioritize bigrams for Chinese text
        similarity = jaccard * 0.3 + bigram * 0.5 + trigram * 0.2

        return similarity

    # ==================== IMAGE SIMILARITY ====================

    def calculate_image_hash(self, image_url: str | None) -> str | None:
        """
        Calculate perceptual hash for image using difference hash (dHash).

        This is a simplified implementation that uses URL-based hashing.
        For production with actual image processing, use PIL/Pillow.
        """
        if not image_url:
            return None

        # For now, use URL-based hash with better distribution
        # In production, download image and calculate actual perceptual hash
        url_hash = hashlib.sha256(image_url.encode()).hexdigest()

        # Simulate perceptual hash format (64-bit hex string)
        return url_hash[:16]

    def calculate_image_similarity(
        self, hash1: str | None, hash2: str | None
    ) -> float:
        """
        Calculate similarity between two image hashes using Hamming distance.

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not hash1 or not hash2:
            return 0.0

        if hash1 == hash2:
            return 1.0

        try:
            # Convert hex strings to binary
            bin1 = bin(int(hash1, 16))[2:].zfill(64)
            bin2 = bin(int(hash2, 16))[2:].zfill(64)

            # Calculate Hamming distance
            hamming_distance = sum(c1 != c2 for c1, c2 in zip(bin1, bin2, strict=False))

            # Convert to similarity score (0.0 to 1.0)
            # Lower Hamming distance = higher similarity
            similarity = 1.0 - (hamming_distance / 64.0)

            return similarity

        except (ValueError, TypeError):
            # If hash format is invalid, return 0
            return 0.0

    # ==================== PRICE SIMILARITY ====================

    def calculate_price_similarity(self, price1: float, price2: float) -> float:
        """Calculate price similarity (for validation, not primary matching).

        Returns 1.0 if prices are within 30% of each other.
        """
        if price1 <= 0 or price2 <= 0:
            return 0.0

        ratio = min(price1, price2) / max(price1, price2)

        # Prices within 30% are considered similar
        if ratio >= 0.7:
            return ratio

        return 0.0

    # ==================== MATCHING LOGIC ====================

    async def match_products_by_text(
        self, threshold: float | None = None
    ) -> list[ProductMatchingGroup]:
        """Match products based on text similarity.

        Args:
            threshold: Minimum similarity score (default: 0.70)

        Returns:
            List of created matching groups
        """
        threshold = threshold or self.TEXT_SIMILARITY_THRESHOLD

        # Get all unmatched products
        stmt = select(SupplierRawProduct).where(
            and_(
                SupplierRawProduct.matching_status == MatchingStatus.PENDING,
                SupplierRawProduct.is_active,
            )
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        if len(products) < 2:
            return []

        # Calculate pairwise similarities
        groups = []
        matched_products = set()

        for i, product_a in enumerate(products):
            if product_a.id in matched_products:
                continue

            # Start a new group with this product
            group_products = [product_a]
            matched_products.add(product_a.id)

            # Find similar products
            for product_b in products[i + 1 :]:
                if product_b.id in matched_products:
                    continue

                # Skip if same supplier
                if product_a.supplier_id == product_b.supplier_id:
                    continue

                # Calculate similarity
                similarity = self.calculate_text_similarity(
                    product_a.chinese_name, product_b.chinese_name
                )

                if similarity >= threshold:
                    group_products.append(product_b)
                    matched_products.add(product_b.id)

                    # Save matching score
                    score = ProductMatchingScore(
                        product_a_id=product_a.id,
                        product_b_id=product_b.id,
                        text_similarity=similarity,
                        total_score=similarity,
                        matching_algorithm="text_ngram",
                        is_match=True,
                        threshold_used=threshold,
                    )
                    self.db.add(score)

            # Create group if we have multiple products
            if len(group_products) > 1:
                group = await self._create_matching_group(
                    group_products, matching_method="text", confidence_score=threshold
                )
                groups.append(group)

        await self.db.commit()
        return groups

    async def match_products_by_image(
        self, threshold: float | None = None
    ) -> list[ProductMatchingGroup]:
        """Match products based on image similarity.

        Note: Requires image hashes to be pre-calculated.
        """
        threshold = threshold or self.IMAGE_SIMILARITY_THRESHOLD

        # Get products with image hashes
        stmt = select(SupplierRawProduct).where(
            and_(
                SupplierRawProduct.matching_status == MatchingStatus.PENDING,
                SupplierRawProduct.is_active,
                SupplierRawProduct.image_hash.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        if len(products) < 2:
            return []

        # Group by image hash
        hash_groups = defaultdict(list)
        for product in products:
            if product.image_hash:
                hash_groups[product.image_hash].append(product)

        # Create groups for matching images
        groups = []
        for _image_hash, group_products in hash_groups.items():
            if len(group_products) > 1:
                # Skip if all from same supplier
                supplier_ids = {p.supplier_id for p in group_products}
                if len(supplier_ids) == 1:
                    continue

                group = await self._create_matching_group(
                    group_products,
                    matching_method="image",
                    confidence_score=1.0,  # Exact hash match
                )
                groups.append(group)

        await self.db.commit()
        return groups

    async def match_products_hybrid(
        self, threshold: float | None = None
    ) -> list[ProductMatchingGroup]:
        """Match products using hybrid approach (text + image).

        This is the recommended method for best accuracy.
        """
        threshold = threshold or self.HYBRID_THRESHOLD

        # Get all unmatched products with image hashes
        stmt = select(SupplierRawProduct).where(
            and_(
                SupplierRawProduct.matching_status == MatchingStatus.PENDING,
                SupplierRawProduct.is_active,
            )
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        if len(products) < 2:
            return []

        groups = []
        matched_products = set()

        for i, product_a in enumerate(products):
            if product_a.id in matched_products:
                continue

            group_products = [product_a]
            matched_products.add(product_a.id)

            for product_b in products[i + 1 :]:
                if product_b.id in matched_products:
                    continue

                # Skip if same supplier
                if product_a.supplier_id == product_b.supplier_id:
                    continue

                # Calculate text similarity
                text_sim = self.calculate_text_similarity(
                    product_a.chinese_name, product_b.chinese_name
                )

                # Calculate image similarity if available
                image_sim = 0.0
                if product_a.image_hash and product_b.image_hash:
                    image_sim = self.calculate_image_similarity(
                        product_a.image_hash, product_b.image_hash
                    )

                # Calculate hybrid score
                if product_a.image_hash and product_b.image_hash:
                    hybrid_score = (
                        text_sim * self.TEXT_WEIGHT + image_sim * self.IMAGE_WEIGHT
                    )
                else:
                    # Fall back to text only
                    hybrid_score = text_sim

                if hybrid_score >= threshold:
                    group_products.append(product_b)
                    matched_products.add(product_b.id)

                    # Save matching score
                    score = ProductMatchingScore(
                        product_a_id=product_a.id,
                        product_b_id=product_b.id,
                        text_similarity=text_sim,
                        image_similarity=image_sim if image_sim > 0 else None,
                        total_score=hybrid_score,
                        matching_algorithm="hybrid",
                        is_match=True,
                        threshold_used=threshold,
                        matching_features={
                            "text_weight": self.TEXT_WEIGHT,
                            "image_weight": self.IMAGE_WEIGHT,
                            "has_image": bool(
                                product_a.image_hash and product_b.image_hash
                            ),
                        },
                    )
                    self.db.add(score)

            if len(group_products) > 1:
                group = await self._create_matching_group(
                    group_products, matching_method="hybrid", confidence_score=threshold
                )
                groups.append(group)

        await self.db.commit()
        return groups

    async def _create_matching_group(
        self,
        products: list[SupplierRawProduct],
        matching_method: str,
        confidence_score: float,
    ) -> ProductMatchingGroup:
        """Create a matching group from a list of products."""

        # Use the first product's name as representative
        representative = products[0]

        # Calculate price statistics
        prices = [p.price_cny for p in products]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)

        # Find best supplier (lowest price)
        best_product = min(products, key=lambda p: p.price_cny)

        # Create group
        group = ProductMatchingGroup(
            group_name=representative.chinese_name,
            group_name_en=representative.english_name,
            representative_image_url=representative.image_url,
            representative_image_hash=representative.image_hash,
            confidence_score=confidence_score,
            matching_method=matching_method,
            status=MatchingStatus.AUTO_MATCHED,
            min_price_cny=min_price,
            max_price_cny=max_price,
            avg_price_cny=avg_price,
            best_supplier_id=best_product.supplier_id,
            product_count=len(products),
            is_active=True,
        )

        self.db.add(group)
        await self.db.flush()

        # Update products to reference this group
        for product in products:
            product.product_group_id = group.id
            product.matching_status = MatchingStatus.AUTO_MATCHED

        return group

    # ==================== UTILITY METHODS ====================

    async def get_best_price_for_group(
        self, group_id: int
    ) -> tuple[SupplierRawProduct, Supplier] | None:
        """Get the product with best price in a group."""

        stmt = (
            select(SupplierRawProduct, Supplier)
            .join(Supplier, SupplierRawProduct.supplier_id == Supplier.id)
            .where(
                and_(
                    SupplierRawProduct.product_group_id == group_id,
                    SupplierRawProduct.is_active,
                )
            )
            .order_by(SupplierRawProduct.price_cny.asc())
        )

        result = await self.db.execute(stmt)
        row = result.first()

        return row if row else None

    async def get_price_comparison(self, group_id: int) -> list[dict]:
        """Get price comparison for all products in a group."""

        stmt = (
            select(SupplierRawProduct, Supplier)
            .join(Supplier, SupplierRawProduct.supplier_id == Supplier.id)
            .where(
                and_(
                    SupplierRawProduct.product_group_id == group_id,
                    SupplierRawProduct.is_active,
                )
            )
            .order_by(SupplierRawProduct.price_cny.asc())
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        comparisons = []
        for product, supplier in rows:
            comparisons.append(
                {
                    "product_id": product.id,
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name,
                    "price_cny": product.price_cny,
                    "product_url": product.product_url,
                    "chinese_name": product.chinese_name,
                    "english_name": product.english_name,
                    "image_url": product.image_url,
                }
            )

        return comparisons

    async def update_group_statistics(self, group_id: int) -> None:
        """Recalculate and update group statistics."""

        stmt = select(SupplierRawProduct).where(
            and_(
                SupplierRawProduct.product_group_id == group_id,
                SupplierRawProduct.is_active,
            )
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        if not products:
            return

        # Update group
        group_stmt = select(ProductMatchingGroup).where(
            ProductMatchingGroup.id == group_id
        )
        group_result = await self.db.execute(group_stmt)
        group = group_result.scalar_one_or_none()

        if not group:
            return

        prices = [p.price_cny for p in products]
        group.min_price_cny = min(prices)
        group.max_price_cny = max(prices)
        group.avg_price_cny = sum(prices) / len(prices)
        group.product_count = len(products)

        best_product = min(products, key=lambda p: p.price_cny)
        group.best_supplier_id = best_product.supplier_id

        await self.db.commit()

    async def confirm_match(self, group_id: int, user_id: int) -> ProductMatchingGroup:
        """Manually confirm a matching group."""

        stmt = select(ProductMatchingGroup).where(ProductMatchingGroup.id == group_id)
        result = await self.db.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            raise ValueError(f"Group {group_id} not found")

        group.status = MatchingStatus.MANUAL_MATCHED
        group.verified_by = user_id
        group.verified_at = datetime.now(UTC)

        # Update all products in group
        update_stmt = select(SupplierRawProduct).where(
            SupplierRawProduct.product_group_id == group_id
        )
        update_result = await self.db.execute(update_stmt)
        products = update_result.scalars().all()

        for product in products:
            product.matching_status = MatchingStatus.MANUAL_MATCHED

        await self.db.commit()
        return group

    async def reject_match(self, group_id: int, user_id: int) -> None:
        """Reject a matching group and unlink products."""

        # Get all products in group
        stmt = select(SupplierRawProduct).where(
            SupplierRawProduct.product_group_id == group_id
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        # Unlink products
        for product in products:
            product.product_group_id = None
            product.matching_status = MatchingStatus.REJECTED

        # Mark group as inactive
        group_stmt = select(ProductMatchingGroup).where(
            ProductMatchingGroup.id == group_id
        )
        group_result = await self.db.execute(group_stmt)
        group = group_result.scalar_one_or_none()

        if group:
            group.status = MatchingStatus.REJECTED
            group.is_active = False
            group.verified_by = user_id
            group.verified_at = datetime.now(UTC)

        await self.db.commit()
