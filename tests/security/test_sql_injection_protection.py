"""
Tests for SQL Injection Protection

These tests verify that the application properly protects against SQL injection
attacks by validating input and using parameterized queries.
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.main import app


class TestSQLInjectionProtection:
    """Test suite for SQL injection protection."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_limit_parameter(self):
        """Test that malicious limit parameter is rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # SQL injection payload in limit
            malicious_limit = "10; DROP TABLE users; --"
            
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": malicious_limit}
            )
            
            # Should return validation error, not execute SQL
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
    @pytest.mark.asyncio
    async def test_sql_injection_in_offset_parameter(self):
        """Test that malicious offset parameter is rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # SQL injection payload in offset
            malicious_offset = "0; DELETE FROM products WHERE 1=1; --"
            
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"offset": malicious_offset}
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_sql_injection_in_account_type(self):
        """Test that malicious account_type parameter is rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # SQL injection payload in account_type
            malicious_account = "main'; DROP TABLE emag_products; --"
            
            response = await client.get(
                "/api/v1/emag/offers/all",
                params={"account_type": malicious_account}
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_union_based_sql_injection(self):
        """Test protection against UNION-based SQL injection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # UNION-based SQL injection
            malicious_payload = "10 UNION SELECT * FROM users --"
            
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": malicious_payload}
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_boolean_based_sql_injection(self):
        """Test protection against boolean-based SQL injection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Boolean-based SQL injection
            malicious_payload = "1 OR 1=1"
            
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": malicious_payload}
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_time_based_sql_injection(self):
        """Test protection against time-based SQL injection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Time-based SQL injection
            malicious_payload = "1; WAITFOR DELAY '00:00:05' --"
            
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": malicious_payload}
            )
            
            # Should return validation error quickly (not wait 5 seconds)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_stacked_queries_injection(self):
        """Test protection against stacked queries injection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Stacked queries injection
            malicious_payload = "10; UPDATE users SET is_admin=1 WHERE id=1; --"
            
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": malicious_payload}
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_valid_parameters_accepted(self):
        """Test that valid parameters are accepted."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Valid parameters
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": 10, "page": 1}
            )
            
            # Should succeed (or return auth error, but not validation error)
            assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_negative_limit_rejected(self):
        """Test that negative limit is rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": -10}
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_zero_limit_rejected(self):
        """Test that zero limit is rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": 0}
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_excessive_limit_rejected(self):
        """Test that excessive limit is rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": 10000}  # Assuming max is 100
            )
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestInputValidation:
    """Test suite for input validation."""

    @pytest.mark.asyncio
    async def test_string_in_numeric_field(self):
        """Test that string values in numeric fields are rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": "abc"}
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_special_characters_in_account_type(self):
        """Test that special characters in account_type are rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/offers/all",
                params={"account_type": "main<script>alert('xss')</script>"}
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_null_byte_injection(self):
        """Test protection against null byte injection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": "10\x00"}
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestParameterizedQueries:
    """Test that parameterized queries are used correctly."""

    @pytest.mark.asyncio
    async def test_parameterized_query_with_valid_data(self):
        """Test that parameterized queries work with valid data."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": 50, "page": 2, "account_type": "main"}
            )
            
            # Should not return validation error
            # (may return auth error or success depending on auth state)
            assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_boundary_values(self):
        """Test boundary values for pagination."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test minimum valid limit
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": 1, "page": 1}
            )
            assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test maximum valid limit
            response = await client.get(
                "/api/v1/emag/products/all",
                params={"limit": 100, "page": 1}
            )
            assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
