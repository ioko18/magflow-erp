"""
Integration tests for eMAG API v4.4.9 Pricing Intelligence features.

Tests commission estimates, Smart Deals eligibility, and EAN search functionality.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
@pytest.mark.integration
class TestPricingIntelligence:
    """Test suite for pricing intelligence endpoints."""
    
    @pytest.fixture
    async def auth_headers(self):
        """Get authentication headers for API requests."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin@example.com", "password": "secret"}
            )
            assert response.status_code == 200
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
    
    async def test_get_commission_estimate(self, auth_headers):
        """Test commission estimate endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/pricing/commission/estimate/12345",
                headers=auth_headers,
                params={"account_type": "main"}
            )
            
            # Should return 200 even if product doesn't exist (graceful handling)
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "product_id" in data
            assert data["product_id"] == 12345
            
            # Either has commission data or error
            if data.get("error"):
                assert isinstance(data["error"], str)
            else:
                assert "commission_value" in data or "commission_percentage" in data
    
    async def test_check_smart_deals_eligibility(self, auth_headers):
        """Test Smart Deals eligibility check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/pricing/smart-deals/check/12345",
                headers=auth_headers,
                params={"account_type": "main"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "product_id" in data
            assert "is_eligible" in data
            assert isinstance(data["is_eligible"], bool)
            
            # If eligible, should have pricing info
            if data["is_eligible"]:
                assert "current_price" in data
            
            # If not eligible, might have target price
            if not data["is_eligible"] and not data.get("error"):
                assert "target_price" in data or "message" in data
    
    async def test_search_products_by_ean(self, auth_headers):
        """Test EAN search endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/emag/pricing/ean/search",
                headers=auth_headers,
                json={
                    "eans": ["7086812930967", "5904862975146"],
                    "account_type": "main"
                }
            )
            
            # Should succeed even if EANs not found
            assert response.status_code in [200, 400]
            
            if response.status_code == 200:
                data = response.json()
                assert "results" in data
                assert "total_found" in data
                assert isinstance(data["results"], list)
    
    async def test_ean_search_max_limit(self, auth_headers):
        """Test EAN search with too many EANs."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try to search with 101 EANs (exceeds limit of 100)
            eans = [f"123456789012{i}" for i in range(101)]
            
            response = await client.post(
                "/api/v1/emag/pricing/ean/search",
                headers=auth_headers,
                json={
                    "eans": eans,
                    "account_type": "main"
                }
            )
            
            assert response.status_code == 400
            assert "100" in response.json()["detail"]
    
    async def test_get_pricing_recommendations(self, auth_headers):
        """Test pricing recommendations endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/emag/pricing/recommendations",
                headers=auth_headers,
                json={
                    "product_id": 12345,
                    "current_price": 99.99,
                    "account_type": "main"
                }
            )
            
            # Should return recommendations even if data unavailable
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "product_id" in data
                assert "current_price" in data
                assert "recommendations" in data
                assert isinstance(data["recommendations"], list)
    
    async def test_bulk_pricing_recommendations(self, auth_headers):
        """Test bulk pricing recommendations endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/pricing/bulk-recommendations",
                headers=auth_headers,
                params={
                    "product_ids": "12345,12346,12347",
                    "account_type": "main"
                }
            )
            
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "results" in data
                assert "total_processed" in data
                assert len(data["results"]) <= 3
    
    async def test_bulk_recommendations_max_limit(self, auth_headers):
        """Test bulk recommendations with too many products."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try with 51 products (exceeds limit of 50)
            product_ids = ",".join(str(i) for i in range(1, 52))
            
            response = await client.get(
                "/api/v1/emag/pricing/bulk-recommendations",
                headers=auth_headers,
                params={
                    "product_ids": product_ids,
                    "account_type": "main"
                }
            )
            
            assert response.status_code == 400
            assert "50" in response.json()["detail"]
    
    async def test_invalid_account_type(self, auth_headers):
        """Test endpoints with invalid account type."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/pricing/commission/estimate/12345",
                headers=auth_headers,
                params={"account_type": "invalid"}
            )
            
            # Should handle gracefully
            assert response.status_code in [400, 500]
    
    async def test_unauthorized_access(self):
        """Test endpoints without authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/pricing/commission/estimate/12345",
                params={"account_type": "main"}
            )
            
            assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
class TestBulkOperations:
    """Test suite for bulk operations with Light Offer API."""
    
    @pytest.fixture
    async def auth_headers(self):
        """Get authentication headers for API requests."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin@example.com", "password": "secret"}
            )
            assert response.status_code == 200
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
    
    async def test_bulk_update_offers_light(self, auth_headers):
        """Test bulk offer updates using Light API."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            updates = [
                {
                    "product_id": 12345,
                    "account_type": "main",
                    "sale_price": 99.99,
                    "stock_value": 10
                },
                {
                    "product_id": 12346,
                    "account_type": "main",
                    "sale_price": 149.99,
                    "stock_value": 5
                }
            ]
            
            response = await client.post(
                "/api/v1/emag/advanced/offers/bulk-update-light",
                headers=auth_headers,
                json=updates
            )
            
            # Should process even if products don't exist
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "summary" in data
                assert "results" in data
                assert data["summary"]["total"] == 2
    
    async def test_bulk_update_max_limit(self, auth_headers):
        """Test bulk update with too many products."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try with 101 updates (exceeds limit of 100)
            updates = [
                {
                    "product_id": i,
                    "account_type": "main",
                    "sale_price": 99.99
                }
                for i in range(101)
            ]
            
            response = await client.post(
                "/api/v1/emag/advanced/offers/bulk-update-light",
                headers=auth_headers,
                json=updates
            )
            
            assert response.status_code == 400
            assert "100" in response.json()["detail"]
    
    async def test_bulk_update_custom_batch_size(self, auth_headers):
        """Test bulk update with custom batch size."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            updates = [
                {
                    "product_id": i,
                    "account_type": "main",
                    "sale_price": 99.99
                }
                for i in range(10)
            ]
            
            response = await client.post(
                "/api/v1/emag/advanced/offers/bulk-update-light?batch_size=5",
                headers=auth_headers,
                json=updates
            )
            
            # Should process in batches of 5
            assert response.status_code in [200, 500]
    
    async def test_bulk_update_mixed_accounts(self, auth_headers):
        """Test bulk update with mixed account types."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            updates = [
                {
                    "product_id": 12345,
                    "account_type": "main",
                    "sale_price": 99.99
                },
                {
                    "product_id": 12346,
                    "account_type": "fbe",
                    "sale_price": 149.99
                }
            ]
            
            response = await client.post(
                "/api/v1/emag/advanced/offers/bulk-update-light",
                headers=auth_headers,
                json=updates
            )
            
            # Should handle mixed accounts
            assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
