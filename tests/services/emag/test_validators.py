"""
Tests for eMAG validation utilities.
"""

import pytest
from app.services.emag.utils.validators import (
    validate_product_data,
    validate_order_data,
    validate_credentials,
    validate_sync_params,
)
from app.core.exceptions import ValidationError


class TestProductValidation:
    """Test product data validation."""
    
    def test_valid_product(self):
        """Test validation of valid product data."""
        product = {
            "id": 12345,
            "name": "Test Product",
            "price": 99.99,
        }
        
        assert validate_product_data(product) is True
    
    def test_missing_required_field(self):
        """Test validation fails for missing required field."""
        product = {
            "name": "Test Product",
        }
        
        with pytest.raises(ValidationError, match="Missing required field: id"):
            validate_product_data(product)
    
    def test_invalid_price(self):
        """Test validation fails for invalid price."""
        product = {
            "id": 12345,
            "name": "Test Product",
            "price": -10.0,
        }
        
        with pytest.raises(ValidationError, match="price cannot be negative"):
            validate_product_data(product)
    
    def test_empty_name(self):
        """Test validation fails for empty name."""
        product = {
            "id": 12345,
            "name": "",
        }
        
        with pytest.raises(ValidationError, match="name must be a non-empty string"):
            validate_product_data(product)


class TestOrderValidation:
    """Test order data validation."""
    
    def test_valid_order(self):
        """Test validation of valid order data."""
        order = {
            "id": 67890,
            "status": 1,
            "products": [
                {"id": 12345, "quantity": 2}
            ],
        }
        
        assert validate_order_data(order) is True
    
    def test_missing_required_field(self):
        """Test validation fails for missing required field."""
        order = {
            "id": 67890,
        }
        
        with pytest.raises(ValidationError, match="Missing required field: status"):
            validate_order_data(order)
    
    def test_invalid_products_type(self):
        """Test validation fails for invalid products type."""
        order = {
            "id": 67890,
            "status": 1,
            "products": "not a list",
        }
        
        with pytest.raises(ValidationError, match="products must be a list"):
            validate_order_data(order)
    
    def test_product_without_id(self):
        """Test validation fails for product without ID."""
        order = {
            "id": 67890,
            "status": 1,
            "products": [
                {"quantity": 2}
            ],
        }
        
        with pytest.raises(ValidationError, match="Product in order must have an ID"):
            validate_order_data(order)


class TestCredentialsValidation:
    """Test credentials validation."""
    
    def test_valid_credentials(self):
        """Test validation of valid credentials."""
        assert validate_credentials("test_user", "test_password") is True
    
    def test_empty_username(self):
        """Test validation fails for empty username."""
        with pytest.raises(ValidationError, match="Invalid username"):
            validate_credentials("", "test_password")
    
    def test_empty_password(self):
        """Test validation fails for empty password."""
        with pytest.raises(ValidationError, match="Invalid password"):
            validate_credentials("test_user", "")
    
    def test_short_username(self):
        """Test validation fails for short username."""
        with pytest.raises(ValidationError, match="Username too short"):
            validate_credentials("ab", "test_password")
    
    def test_short_password(self):
        """Test validation fails for short password."""
        with pytest.raises(ValidationError, match="Password too short"):
            validate_credentials("test_user", "12345")


class TestSyncParamsValidation:
    """Test sync parameters validation."""
    
    def test_valid_params(self):
        """Test validation of valid sync parameters."""
        assert validate_sync_params("main", full_sync=True, limit=100) is True
    
    def test_invalid_account_type(self):
        """Test validation fails for invalid account type."""
        with pytest.raises(ValidationError, match="Invalid account type"):
            validate_sync_params("invalid")
    
    def test_invalid_limit(self):
        """Test validation fails for invalid limit."""
        with pytest.raises(ValidationError, match="limit must be a positive integer"):
            validate_sync_params("main", limit=-1)
    
    def test_limit_too_large(self):
        """Test validation fails for limit too large."""
        with pytest.raises(ValidationError, match="limit too large"):
            validate_sync_params("main", limit=20000)
