"""
Advanced Product Matching Service using jieba tokenization.

This service provides intelligent Chinese product matching using:
- jieba tokenization for Chinese text
- Token-based similarity calculation
- Model normalization (ABC-123 -> ABC123)
- Fuzzy matching for partial tokens
- N-gram similarity for substring matching
- Configurable thresholds
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.supplier import Supplier, SupplierProduct

logger = logging.getLogger(__name__)

# Try to import jieba, fallback to simple tokenization if not available
try:
    import jieba

    JIEBA_AVAILABLE = True
    logger.info("jieba library loaded successfully")
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba library not available, using simple tokenization")


class JiebaMatchingService:
    """Advanced matching service using jieba tokenization for Chinese text."""

    # Matching thresholds
    DEFAULT_THRESHOLD = 0.3  # 30% common tokens minimum
    HIGH_CONFIDENCE_THRESHOLD = 0.7  # 70% for high confidence
    MIN_TOKEN_LENGTH = 2  # Minimum token length to consider

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def normalize_model_tokens(text: str) -> str:
        """
        Normalize model tokens (e.g., ABC-123 -> ABC123).

        This helps match product codes that may have different separators.
        """
        if not text:
            return ""
        return re.sub(r"([A-Za-z]+)[-_](\d+)", r"\1\2", text)

    @staticmethod
    def tokenize_clean(text: str, min_token_len: int = MIN_TOKEN_LENGTH) -> list[str]:
        """
        Tokenize and clean text using jieba (if available) or simple tokenization.

        Args:
            text: Text to tokenize
            min_token_len: Minimum token length to keep

        Returns:
            List of cleaned tokens
        """
        if not text or not text.strip():
            return []

        # Normalize model tokens first
        text = JiebaMatchingService.normalize_model_tokens(text)
        tokens = []

        if JIEBA_AVAILABLE:
            # Use jieba for Chinese text
            for token in jieba.cut(text):
                cleaned_token = token.strip().lower()
                # Keep tokens with alphanumeric or Chinese characters
                if (
                    cleaned_token
                    and re.search(r"[a-zA-Z0-9\u4e00-\u9fff]", cleaned_token)
                    and len(cleaned_token) >= min_token_len
                ):
                    tokens.append(cleaned_token)
        else:
            # Fallback: simple word splitting
            # Extract Chinese characters, alphanumeric sequences
            pattern = r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+"
            matches = re.findall(pattern, text)
            for match in matches:
                cleaned = match.strip().lower()
                if len(cleaned) >= min_token_len:
                    tokens.append(cleaned)

        return tokens

    @staticmethod
    def fuzzy_token_match(token1: str, token2: str, threshold: float = 0.8) -> float:
        """
        Calculate fuzzy similarity between two tokens using SequenceMatcher.

        Args:
            token1: First token
            token2: Second token
            threshold: Minimum similarity to consider a match

        Returns:
            Similarity score (0.0-1.0)
        """
        if token1 == token2:
            return 1.0

        # Check if one token is a substring of another
        if token1 in token2 or token2 in token1:
            # Calculate ratio based on length difference
            shorter = min(len(token1), len(token2))
            longer = max(len(token1), len(token2))
            return shorter / longer

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, token1, token2).ratio()

    @staticmethod
    def generate_ngrams(text: str, n: int = 3) -> set[str]:
        """
        Generate character n-grams from text.

        Args:
            text: Input text
            n: N-gram size

        Returns:
            Set of n-grams
        """
        if len(text) < n:
            return {text}
        return {text[i:i+n] for i in range(len(text) - n + 1)}

    @staticmethod
    def ngram_similarity(text1: str, text2: str, n: int = 3) -> float:
        """
        Calculate similarity using character n-grams.

        Args:
            text1: First text
            text2: Second text
            n: N-gram size

        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0

        ngrams1 = JiebaMatchingService.generate_ngrams(text1.lower(), n)
        ngrams2 = JiebaMatchingService.generate_ngrams(text2.lower(), n)

        if not ngrams1 or not ngrams2:
            return 0.0

        common = ngrams1 & ngrams2
        return len(common) / max(len(ngrams1), len(ngrams2))

    @staticmethod
    def calculate_similarity(
        search_tokens: set[str], product_tokens: set[str]
    ) -> tuple[float, set[str]]:
        """
        Calculate similarity between two token sets.

        Args:
            search_tokens: Tokens from search term
            product_tokens: Tokens from product name

        Returns:
            Tuple of (similarity_score, common_tokens)
        """
        if not search_tokens or not product_tokens:
            return 0.0, set()

        common_tokens = search_tokens & product_tokens

        # Similarity = common tokens / search tokens
        # This means: "how much of the search term is found in the product"
        similarity = len(common_tokens) / len(search_tokens)

        return similarity, common_tokens

    @staticmethod
    def calculate_enhanced_similarity(
        search_tokens: set[str],
        product_tokens: set[str],
        fuzzy_threshold: float = 0.85
    ) -> tuple[float, set[str], dict[str, Any]]:
        """
        Calculate enhanced similarity with fuzzy matching and n-gram support.

        Args:
            search_tokens: Tokens from search term
            product_tokens: Tokens from product name
            fuzzy_threshold: Minimum fuzzy match threshold

        Returns:
            Tuple of (similarity_score, matched_tokens, match_details)
        """
        if not search_tokens or not product_tokens:
            return 0.0, set(), {}

        # Exact matches
        exact_matches = search_tokens & product_tokens
        matched_search_tokens = set(exact_matches)

        # Track fuzzy matches
        fuzzy_matches = []
        partial_matches = []

        # For each unmatched search token, try fuzzy matching
        unmatched_search = search_tokens - exact_matches
        unmatched_product = product_tokens - exact_matches

        for search_token in unmatched_search:
            best_match = None
            best_score = 0.0
            match_type = None

            for product_token in unmatched_product:
                # Try fuzzy matching
                fuzzy_score = JiebaMatchingService.fuzzy_token_match(
                    search_token, product_token, fuzzy_threshold
                )

                if fuzzy_score >= fuzzy_threshold and fuzzy_score > best_score:
                    best_score = fuzzy_score
                    best_match = product_token
                    match_type = 'fuzzy'

                # Try n-gram similarity for partial matches
                ngram_score = JiebaMatchingService.ngram_similarity(
                    search_token, product_token, n=2
                )

                if ngram_score >= 0.7 and ngram_score > best_score:
                    best_score = ngram_score
                    best_match = product_token
                    match_type = 'ngram'

            if best_match:
                matched_search_tokens.add(search_token)
                if match_type == 'fuzzy':
                    fuzzy_matches.append({
                        'search': search_token,
                        'product': best_match,
                        'score': best_score
                    })
                else:
                    partial_matches.append({
                        'search': search_token,
                        'product': best_match,
                        'score': best_score
                    })

        # Calculate weighted similarity
        # Exact matches: full weight (1.0)
        # Fuzzy matches: 0.9 weight
        # Partial matches: 0.7 weight
        exact_weight = len(exact_matches) * 1.0
        fuzzy_weight = len(fuzzy_matches) * 0.9
        partial_weight = len(partial_matches) * 0.7

        total_weight = exact_weight + fuzzy_weight + partial_weight
        similarity = total_weight / len(search_tokens)

        match_details = {
            'exact_matches': list(exact_matches),
            'fuzzy_matches': fuzzy_matches,
            'partial_matches': partial_matches,
            'exact_count': len(exact_matches),
            'fuzzy_count': len(fuzzy_matches),
            'partial_count': len(partial_matches)
        }

        return similarity, matched_search_tokens, match_details

    @staticmethod
    def calculate_min_common_tokens(search_tokens: set[str]) -> int:
        """
        Calculate minimum number of common tokens required for a match.

        Logic:
        - 1 token with length >= 4: Need 1 match
        - Multiple tokens: Need at least 2 matches
        - Otherwise: No match possible
        """
        token_lengths = [len(token) for token in search_tokens]

        if len(search_tokens) == 1 and all(length >= 4 for length in token_lengths):
            return 1
        elif len(search_tokens) > 1:
            return 2
        else:
            return 0  # Not enough criteria

    async def find_matches_for_local_product(
        self,
        local_product_id: int,
        threshold: float = DEFAULT_THRESHOLD,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Find supplier products that match a local product using jieba tokenization.

        Args:
            local_product_id: ID of local product to match
            threshold: Minimum similarity threshold (0.0-1.0)
            limit: Maximum number of results

        Returns:
            List of matching supplier products with similarity scores
        """
        # Get local product
        local_product_query = select(Product).where(Product.id == local_product_id)
        local_result = await self.db.execute(local_product_query)
        local_product = local_result.scalar_one_or_none()

        if not local_product:
            logger.warning(f"Local product {local_product_id} not found")
            return []

        # Use chinese_name if available, otherwise name
        search_term = local_product.chinese_name or local_product.name
        if not search_term:
            logger.warning(f"Local product {local_product_id} has no name")
            return []

        return await self.search_supplier_products(search_term, threshold, limit)

    async def search_supplier_products(
        self,
        search_term: str,
        threshold: float = DEFAULT_THRESHOLD,
        limit: int = 200,
        supplier_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search supplier products using jieba tokenization.

        Args:
            search_term: Chinese or mixed text to search for
            threshold: Minimum similarity threshold (0.0-1.0)
            limit: Maximum number of results
            supplier_id: Optional supplier ID to filter by

        Returns:
            List of matching products with similarity scores
        """
        if not search_term or not search_term.strip():
            logger.warning("Search term is empty")
            return []

        logger.info(f"Searching for: '{search_term}' with threshold {threshold}")

        # Tokenize search term
        search_tokens = set(self.tokenize_clean(search_term))
        if not search_tokens:
            logger.warning("No tokens generated from search term")
            return []

        logger.info(f"Search tokens: {search_tokens}")

        # Calculate minimum common tokens required
        min_common_tokens = self.calculate_min_common_tokens(search_tokens)
        if min_common_tokens == 0:
            logger.warning("Search criteria not sufficient")
            return []

        # Get supplier products (default: active ones)
        query = select(SupplierProduct).where(SupplierProduct.is_active.is_(True))

        if supplier_id:
            query = query.where(SupplierProduct.supplier_id == supplier_id)

        result = await self.db.execute(query)
        supplier_products = result.scalars().all()

        logger.info(f"Checking {len(supplier_products)} supplier products")

        # Calculate similarity for each product
        matches = []
        for sp in supplier_products:
            # Use chinese name if available
            product_name = sp.supplier_product_chinese_name or sp.supplier_product_name
            if not product_name:
                continue

            # Tokenize product name
            product_tokens = set(self.tokenize_clean(product_name))
            if not product_tokens:
                continue

            # Calculate enhanced similarity with fuzzy matching
            similarity, matched_tokens, match_details = self.calculate_enhanced_similarity(
                search_tokens, product_tokens, fuzzy_threshold=0.85
            )

            # Check if meets criteria (relaxed for fuzzy matches)
            # Accept if similarity meets threshold OR if we have enough matched tokens
            if similarity >= threshold or len(matched_tokens) >= min_common_tokens:
                # Get supplier name
                supplier_query = select(Supplier.name).where(
                    Supplier.id == sp.supplier_id
                )
                supplier_result = await self.db.execute(supplier_query)
                supplier_name = supplier_result.scalar()

                # Get local product if matched
                local_product = None
                if sp.local_product_id:
                    local_product_query = select(
                        Product.id,
                        Product.name,
                        Product.sku,
                        Product.brand,
                        Product.image_url,
                        Product.chinese_name,
                    ).where(Product.id == sp.local_product_id)
                    local_product_result = await self.db.execute(local_product_query)
                    local_product_row = local_product_result.first()

                    if local_product_row:
                        local_product = {
                            "id": local_product_row[0],
                            "name": local_product_row[1],
                            "sku": local_product_row[2],
                            "brand": local_product_row[3],
                            "image_url": local_product_row[4],
                            "chinese_name": local_product_row[5],
                        }

                matches.append(
                    {
                        "id": sp.id,  # Pentru compatibilitate cu tabelul
                        "supplier_product_id": sp.id,
                        "supplier_id": sp.supplier_id,
                        "supplier_name": supplier_name,
                        "supplier_product_name": sp.supplier_product_name,
                        "supplier_product_chinese_name": sp.supplier_product_chinese_name,
                        "supplier_product_specification": sp.supplier_product_specification,
                        "supplier_product_url": sp.supplier_product_url,
                        "supplier_image_url": sp.supplier_image_url,
                        "supplier_price": float(sp.supplier_price)
                        if sp.supplier_price
                        else 0.0,
                        "supplier_currency": sp.supplier_currency,
                        "local_product_id": sp.local_product_id,
                        "local_product": local_product,
                        "confidence_score": round(similarity, 4),
                        "manual_confirmed": sp.manual_confirmed,
                        "is_active": sp.is_active,
                        "created_at": sp.created_at.isoformat()
                        if sp.created_at
                        else None,
                        "similarity_score": round(similarity, 4),
                        "similarity_percent": round(similarity * 100, 2),
                        "common_tokens": list(matched_tokens),
                        "common_tokens_count": len(matched_tokens),
                        "search_tokens_count": len(search_tokens),
                        "product_tokens_count": len(product_tokens),
                        "match_details": match_details,
                    }
                )

        # Sort by similarity (descending)
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Limit results
        if len(matches) > limit:
            logger.info(f"Found {len(matches)} matches, limiting to {limit}")
            matches = matches[:limit]
        else:
            logger.info(f"Found {len(matches)} matches")

        return matches

    async def search_local_products(
        self,
        search_term: str,
        threshold: float = DEFAULT_THRESHOLD,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Search local products using jieba tokenization."""

        if not search_term or not search_term.strip():
            logger.warning("Search term is empty")
            return []

        search_tokens = set(self.tokenize_clean(search_term))
        if not search_tokens:
            logger.warning("No tokens generated from search term")
            return []

        min_common_tokens = self.calculate_min_common_tokens(search_tokens)
        if min_common_tokens == 0:
            logger.warning("Search criteria not sufficient for local product search")
            return []

        query = select(Product).where(Product.is_active.is_(True))
        result = await self.db.execute(query)
        local_products = result.scalars().all()

        matches: list[dict[str, Any]] = []

        for product in local_products:
            product_name = product.chinese_name or product.name
            if not product_name:
                continue

            product_tokens = set(self.tokenize_clean(product_name))
            if not product_tokens:
                continue

            # Use enhanced similarity for better matching
            similarity, matched_tokens, match_details = self.calculate_enhanced_similarity(
                search_tokens, product_tokens, fuzzy_threshold=0.85
            )

            if similarity >= threshold or len(matched_tokens) >= min_common_tokens:
                matches.append(
                    {
                        "id": product.id,
                        "name": product.name,
                        "chinese_name": product.chinese_name,
                        "sku": product.sku,
                        "brand": product.brand,
                        "image_url": product.image_url,
                        "similarity_score": round(similarity, 4),
                        "similarity_percent": round(similarity * 100, 2),
                        "common_tokens": list(matched_tokens),
                        "common_tokens_count": len(matched_tokens),
                        "match_details": match_details,
                    }
                )

        matches.sort(key=lambda x: x["similarity_score"], reverse=True)

        if len(matches) > limit:
            matches = matches[:limit]

        if matches:
            match_ids = [match["id"] for match in matches]
            counts_query = (
                select(
                    SupplierProduct.local_product_id,
                    func.count(SupplierProduct.id),
                )
                .where(SupplierProduct.local_product_id.in_(match_ids))
                .group_by(SupplierProduct.local_product_id)
            )
            counts_result = await self.db.execute(counts_query)
            counts = {
                row[0]: row[1]
                for row in counts_result.all()
                if row[0] is not None
            }

            for match in matches:
                match["supplier_match_count"] = counts.get(match["id"], 0)

        return matches

    async def auto_match_supplier_products(
        self,
        supplier_id: int,
        threshold: float = DEFAULT_THRESHOLD,
        auto_confirm_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Automatically match supplier products with local products using jieba.

        Args:
            supplier_id: Supplier ID to match products for
            threshold: Minimum similarity threshold
            auto_confirm_threshold: Threshold for auto-confirmation (>= this will be confirmed)
            dry_run: If True, don't save matches, just return results

        Returns:
            Dictionary with matching statistics
        """
        logger.info(f"Auto-matching products for supplier {supplier_id}")

        # Get all local products with chinese names
        local_products_query = select(Product).where(
            and_(Product.is_active, Product.chinese_name.isnot(None))
        )
        local_result = await self.db.execute(local_products_query)
        local_products = local_result.scalars().all()

        logger.info(f"Found {len(local_products)} local products with Chinese names")

        # Get unmatched supplier products
        supplier_products_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.local_product_id.is_(None),
            )
        )
        sp_result = await self.db.execute(supplier_products_query)
        supplier_products = sp_result.scalars().all()

        logger.info(f"Found {len(supplier_products)} unmatched supplier products")

        matched_count = 0
        high_confidence_count = 0
        low_confidence_count = 0
        matches_details = []

        for sp in supplier_products:
            product_name = sp.supplier_product_chinese_name or sp.supplier_product_name
            if not product_name:
                continue

            # Tokenize supplier product
            sp_tokens = set(self.tokenize_clean(product_name))
            if not sp_tokens:
                continue

            best_match = None
            best_similarity = 0.0
            best_common_tokens = set()

            # Compare with all local products
            for local_product in local_products:
                search_term = local_product.chinese_name or local_product.name
                if not search_term:
                    continue

                # Tokenize local product
                local_tokens = set(self.tokenize_clean(search_term))
                if not local_tokens:
                    continue

                # Calculate similarity
                similarity, common_tokens = self.calculate_similarity(
                    local_tokens, sp_tokens
                )

                # Check minimum common tokens
                min_common = self.calculate_min_common_tokens(local_tokens)

                if similarity >= threshold and len(common_tokens) >= min_common:
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = local_product
                        best_common_tokens = common_tokens

            # If found a match
            if best_match:
                matched_count += 1

                # Determine if high confidence
                is_high_confidence = best_similarity >= auto_confirm_threshold
                if is_high_confidence:
                    high_confidence_count += 1
                else:
                    low_confidence_count += 1

                match_detail = {
                    "supplier_product_id": sp.id,
                    "supplier_product_name": product_name,
                    "local_product_id": best_match.id,
                    "local_product_name": best_match.name,
                    "local_product_chinese_name": best_match.chinese_name,
                    "similarity_score": round(best_similarity, 4),
                    "similarity_percent": round(best_similarity * 100, 2),
                    "common_tokens": list(best_common_tokens),
                    "auto_confirmed": is_high_confidence,
                }
                matches_details.append(match_detail)

                # Save match if not dry run
                if not dry_run:
                    sp.local_product_id = best_match.id
                    sp.confidence_score = best_similarity
                    sp.manual_confirmed = (
                        is_high_confidence  # Auto-confirm if high confidence
                    )

        # Commit changes if not dry run
        if not dry_run and matched_count > 0:
            await self.db.commit()
            logger.info(f"Committed {matched_count} matches to database")

        return {
            "total_checked": len(supplier_products),
            "matched_count": matched_count,
            "high_confidence_count": high_confidence_count,
            "low_confidence_count": low_confidence_count,
            "threshold_used": threshold,
            "auto_confirm_threshold": auto_confirm_threshold,
            "matches": matches_details[:50],  # Return first 50 for preview
            "dry_run": dry_run,
        }

    async def find_matches_for_supplier_product(
        self,
        supplier_product_id: int,
        threshold: float = DEFAULT_THRESHOLD,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Find potential local product matches for a supplier product.

        Args:
            supplier_product_id: Supplier product ID
            threshold: Minimum similarity threshold
            limit: Maximum number of results

        Returns:
            List of potential matches with similarity scores
        """
        # Get supplier product
        sp_query = select(SupplierProduct).where(
            SupplierProduct.id == supplier_product_id
        )
        sp_result = await self.db.execute(sp_query)
        sp = sp_result.scalar_one_or_none()

        if not sp:
            logger.warning(f"Supplier product {supplier_product_id} not found")
            return []

        product_name = sp.supplier_product_chinese_name or sp.supplier_product_name
        if not product_name:
            logger.warning(f"Supplier product {supplier_product_id} has no name")
            return []

        # Tokenize supplier product
        sp_tokens = set(self.tokenize_clean(product_name))
        if not sp_tokens:
            return []

        min_common = self.calculate_min_common_tokens(sp_tokens)

        # Get all active local products with Chinese names
        local_products_query = select(Product).where(
            and_(Product.is_active, Product.chinese_name.isnot(None))
        )
        local_result = await self.db.execute(local_products_query)
        local_products = local_result.scalars().all()

        matches = []

        for local_product in local_products:
            search_term = local_product.chinese_name or local_product.name
            if not search_term:
                continue

            # Tokenize local product
            local_tokens = set(self.tokenize_clean(search_term))
            if not local_tokens:
                continue

            # Calculate similarity
            similarity, common_tokens = self.calculate_similarity(
                sp_tokens, local_tokens
            )

            if similarity >= threshold and len(common_tokens) >= min_common:
                matches.append(
                    {
                        "local_product_id": local_product.id,
                        "local_product_name": local_product.name,
                        "local_product_chinese_name": local_product.chinese_name,
                        "local_product_sku": local_product.sku,
                        "local_product_brand": local_product.brand,
                        "local_product_image_url": local_product.image_url,
                        "similarity_score": round(similarity, 4),
                        "similarity_percent": round(similarity * 100, 2),
                        "common_tokens": list(common_tokens),
                        "common_tokens_count": len(common_tokens),
                        "confidence_level": "high"
                        if similarity >= self.HIGH_CONFIDENCE_THRESHOLD
                        else "medium"
                        if similarity >= 0.5
                        else "low",
                    }
                )

        # Sort by similarity (descending)
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Limit results
        if len(matches) > limit:
            matches = matches[:limit]

        logger.info(
            f"Found {len(matches)} matches for supplier product {supplier_product_id}"
        )

        return matches

    async def get_matching_statistics(self, supplier_id: int) -> dict[str, Any]:
        """
        Get matching statistics for a supplier.

        Args:
            supplier_id: Supplier ID

        Returns:
            Dictionary with statistics
        """
        # Total products
        total_query = select(func.count(SupplierProduct.id)).where(
            SupplierProduct.supplier_id == supplier_id
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar()

        # Matched products
        matched_query = select(func.count(SupplierProduct.id)).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.local_product_id.isnot(None),
            )
        )
        matched_result = await self.db.execute(matched_query)
        matched = matched_result.scalar()

        # High confidence matches (>= 0.7)
        high_conf_query = select(func.count(SupplierProduct.id)).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.local_product_id.isnot(None),
                SupplierProduct.confidence_score >= self.HIGH_CONFIDENCE_THRESHOLD,
            )
        )
        high_conf_result = await self.db.execute(high_conf_query)
        high_confidence = high_conf_result.scalar()

        # Average confidence
        avg_query = select(func.avg(SupplierProduct.confidence_score)).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.local_product_id.isnot(None),
            )
        )
        avg_result = await self.db.execute(avg_query)
        avg_confidence = avg_result.scalar() or 0.0

        return {
            "total_products": total,
            "matched_products": matched,
            "unmatched_products": total - matched,
            "high_confidence_matches": high_confidence,
            "medium_low_confidence_matches": matched - high_confidence,
            "average_confidence": round(float(avg_confidence), 4),
            "match_rate": round((matched / total * 100), 2) if total > 0 else 0.0,
        }
