"""
Test fuzzy matching and n-gram similarity for JiebaMatchingService
"""

import pytest
from app.services.jieba_matching_service import JiebaMatchingService


class TestFuzzyMatching:
    """Test fuzzy matching functionality"""

    def test_fuzzy_token_match_exact(self):
        """Test exact match returns 1.0"""
        score = JiebaMatchingService.fuzzy_token_match("100x60x10mm", "100x60x10mm")
        assert score == 1.0

    def test_fuzzy_token_match_substring(self):
        """Test substring match - '100x60x10m' should match '100x60x10mm'"""
        score = JiebaMatchingService.fuzzy_token_match("100x60x10m", "100x60x10mm")
        # Should be high similarity since one is substring of other
        assert score >= 0.9, f"Expected score >= 0.9, got {score}"

    def test_fuzzy_token_match_partial(self):
        """Test partial match"""
        score = JiebaMatchingService.fuzzy_token_match("100x60", "100x60x10mm")
        assert score >= 0.5, f"Expected score >= 0.5, got {score}"

    def test_ngram_similarity(self):
        """Test n-gram similarity"""
        # Similar strings should have high n-gram similarity
        score = JiebaMatchingService.ngram_similarity("100x60x10m", "100x60x10mm")
        assert score >= 0.8, f"Expected score >= 0.8, got {score}"

    def test_ngram_similarity_different(self):
        """Test n-gram similarity with different strings"""
        score = JiebaMatchingService.ngram_similarity("abc", "xyz")
        assert score < 0.3, f"Expected score < 0.3, got {score}"

    def test_enhanced_similarity_exact_match(self):
        """Test enhanced similarity with exact matches"""
        search_tokens = {"100x60x10mm", "radiator"}
        product_tokens = {"100x60x10mm", "radiator", "aluminum"}

        similarity, matched, details = JiebaMatchingService.calculate_enhanced_similarity(
            search_tokens, product_tokens
        )

        assert similarity == 1.0, f"Expected 1.0, got {similarity}"
        assert len(matched) == 2
        assert details['exact_count'] == 2

    def test_enhanced_similarity_fuzzy_match(self):
        """Test enhanced similarity with fuzzy matching"""
        search_tokens = {"100x60x10m"}  # Missing last 'm'
        product_tokens = {"100x60x10mm"}

        similarity, matched, details = JiebaMatchingService.calculate_enhanced_similarity(
            search_tokens, product_tokens, fuzzy_threshold=0.85
        )

        # Should match with fuzzy matching
        assert similarity >= 0.85, f"Expected similarity >= 0.85, got {similarity}"
        assert len(matched) >= 1
        assert details['fuzzy_count'] >= 1 or details['partial_count'] >= 1

    def test_enhanced_similarity_no_match(self):
        """Test enhanced similarity with no matches"""
        search_tokens = {"abc", "def"}
        product_tokens = {"xyz", "uvw"}

        similarity, matched, details = JiebaMatchingService.calculate_enhanced_similarity(
            search_tokens, product_tokens
        )

        assert similarity == 0.0
        assert len(matched) == 0

    def test_tokenize_clean(self):
        """Test tokenization"""
        tokens = JiebaMatchingService.tokenize_clean("100X60X10mm")
        assert len(tokens) > 0
        # Should normalize and tokenize
        assert any('100' in token.lower() for token in tokens)

    def test_tokenize_clean_chinese(self):
        """Test tokenization with Chinese characters"""
        tokens = JiebaMatchingService.tokenize_clean("散热器100X60X10mm")
        assert len(tokens) > 0
        # Should handle both Chinese and alphanumeric


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
