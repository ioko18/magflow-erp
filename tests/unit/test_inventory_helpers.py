"""
Unit tests for inventory helper functions.

Tests the helper functions used in inventory management:
- calculate_stock_status
- calculate_reorder_quantity
"""

import pytest
from app.api.v1.endpoints.inventory.emag_inventory import (
    calculate_stock_status,
    calculate_reorder_quantity,
)


class TestCalculateStockStatus:
    """Test cases for calculate_stock_status function."""
    
    def test_out_of_stock(self):
        """Test out of stock status (stock = 0)."""
        assert calculate_stock_status(0) == "out_of_stock"
        assert calculate_stock_status(-1) == "out_of_stock"
    
    def test_critical_stock(self):
        """Test critical stock status (1-10 units)."""
        assert calculate_stock_status(1) == "critical"
        assert calculate_stock_status(5) == "critical"
        assert calculate_stock_status(10) == "critical"
    
    def test_low_stock(self):
        """Test low stock status (11-20 units)."""
        assert calculate_stock_status(11) == "low_stock"
        assert calculate_stock_status(15) == "low_stock"
        assert calculate_stock_status(20) == "low_stock"
    
    def test_in_stock(self):
        """Test in stock status (>20 units)."""
        assert calculate_stock_status(21) == "in_stock"
        assert calculate_stock_status(50) == "in_stock"
        assert calculate_stock_status(100) == "in_stock"
    
    def test_custom_thresholds(self):
        """Test with custom min_stock and reorder_point."""
        # Custom min_stock = 5, reorder_point = 15
        assert calculate_stock_status(0, min_stock=5, reorder_point=15) == "out_of_stock"
        assert calculate_stock_status(3, min_stock=5, reorder_point=15) == "critical"
        assert calculate_stock_status(5, min_stock=5, reorder_point=15) == "critical"
        assert calculate_stock_status(10, min_stock=5, reorder_point=15) == "low_stock"
        assert calculate_stock_status(15, min_stock=5, reorder_point=15) == "low_stock"
        assert calculate_stock_status(16, min_stock=5, reorder_point=15) == "in_stock"
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Exactly at thresholds
        assert calculate_stock_status(0) == "out_of_stock"
        assert calculate_stock_status(10) == "critical"
        assert calculate_stock_status(20) == "low_stock"
        assert calculate_stock_status(21) == "in_stock"


class TestCalculateReorderQuantity:
    """Test cases for calculate_reorder_quantity function."""
    
    def test_out_of_stock_reorder(self):
        """Test reorder quantity when out of stock."""
        # Should return max_stock
        assert calculate_reorder_quantity(0) == 100
        assert calculate_reorder_quantity(-1) == 100
        assert calculate_reorder_quantity(0, max_stock=50) == 50
    
    def test_below_target_reorder(self):
        """Test reorder quantity when below target stock."""
        # stock < 20: should return max_stock - stock_quantity
        assert calculate_reorder_quantity(5) == 95  # 100 - 5
        assert calculate_reorder_quantity(10) == 90  # 100 - 10
        assert calculate_reorder_quantity(19) == 81  # 100 - 19
    
    def test_at_target_reorder(self):
        """Test reorder quantity at target stock level."""
        # stock = 20: should return max(0, 50 - 20) = 30
        assert calculate_reorder_quantity(20) == 30
    
    def test_above_target_reorder(self):
        """Test reorder quantity above target stock."""
        # stock >= 20: should return max(0, 50 - stock_quantity)
        assert calculate_reorder_quantity(25) == 25  # 50 - 25
        assert calculate_reorder_quantity(40) == 10  # 50 - 40
        assert calculate_reorder_quantity(50) == 0   # 50 - 50
        assert calculate_reorder_quantity(60) == 0   # max(0, 50 - 60)
    
    def test_custom_parameters(self):
        """Test with custom max_stock and target_stock."""
        # max_stock=50, target_stock=10
        assert calculate_reorder_quantity(0, max_stock=50, target_stock=10) == 50
        assert calculate_reorder_quantity(5, max_stock=50, target_stock=10) == 45
        assert calculate_reorder_quantity(9, max_stock=50, target_stock=10) == 41
        assert calculate_reorder_quantity(10, max_stock=50, target_stock=10) == 40
        assert calculate_reorder_quantity(20, max_stock=50, target_stock=10) == 30
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Exactly at boundaries
        assert calculate_reorder_quantity(0) == 100
        assert calculate_reorder_quantity(20) == 30
        assert calculate_reorder_quantity(50) == 0
        assert calculate_reorder_quantity(100) == 0
    
    def test_negative_stock(self):
        """Test with negative stock (inventory discrepancy)."""
        # Should treat as out of stock
        assert calculate_reorder_quantity(-5) == 100
        assert calculate_reorder_quantity(-10, max_stock=50) == 50


class TestIntegration:
    """Integration tests for helper functions working together."""
    
    def test_status_and_reorder_consistency(self):
        """Test that status and reorder quantity are consistent."""
        test_cases = [
            (0, "out_of_stock", 100),
            (5, "critical", 95),
            (10, "critical", 90),
            (15, "low_stock", 85),
            (20, "low_stock", 30),
            (25, "in_stock", 25),
            (50, "in_stock", 0),
        ]
        
        for stock, expected_status, expected_reorder in test_cases:
            status = calculate_stock_status(stock)
            reorder = calculate_reorder_quantity(stock)
            
            assert status == expected_status, f"Stock {stock}: expected status {expected_status}, got {status}"
            assert reorder == expected_reorder, f"Stock {stock}: expected reorder {expected_reorder}, got {reorder}"
    
    def test_realistic_scenarios(self):
        """Test realistic inventory scenarios."""
        # Scenario 1: Product completely sold out
        stock = 0
        assert calculate_stock_status(stock) == "out_of_stock"
        assert calculate_reorder_quantity(stock) == 100  # Order full batch
        
        # Scenario 2: Product running low
        stock = 8
        assert calculate_stock_status(stock) == "critical"
        assert calculate_reorder_quantity(stock) == 92  # Order to reach max
        
        # Scenario 3: Product at reorder point
        stock = 15
        assert calculate_stock_status(stock) == "low_stock"
        assert calculate_reorder_quantity(stock) == 85  # Order to reach max
        
        # Scenario 4: Product well stocked
        stock = 45
        assert calculate_stock_status(stock) == "in_stock"
        assert calculate_reorder_quantity(stock) == 5  # Small top-up
        
        # Scenario 5: Product overstocked
        stock = 75
        assert calculate_stock_status(stock) == "in_stock"
        assert calculate_reorder_quantity(stock) == 0  # No need to order


@pytest.mark.parametrize("stock,expected_status", [
    (0, "out_of_stock"),
    (1, "critical"),
    (10, "critical"),
    (11, "low_stock"),
    (20, "low_stock"),
    (21, "in_stock"),
    (100, "in_stock"),
])
def test_stock_status_parametrized(stock, expected_status):
    """Parametrized test for stock status calculation."""
    assert calculate_stock_status(stock) == expected_status


@pytest.mark.parametrize("stock,max_stock,expected_reorder", [
    (0, 100, 100),
    (10, 100, 90),
    (20, 100, 30),
    (50, 100, 0),
    (0, 50, 50),
    (10, 50, 40),
    (25, 50, 25),
])
def test_reorder_quantity_parametrized(stock, max_stock, expected_reorder):
    """Parametrized test for reorder quantity calculation."""
    assert calculate_reorder_quantity(stock, max_stock=max_stock) == expected_reorder
