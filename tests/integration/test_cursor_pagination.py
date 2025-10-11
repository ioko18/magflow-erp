from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category, Product
from app.main import app


@pytest.mark.skip(reason="Test needs network/Redis configuration - gaierror")
def test_cursor_pagination(db: Session):
    """Test cursor-based pagination with products."""
    # Create test data
    categories = [
        Category(name=f"Category {i}", description=f"Description {i}")
        for i in range(1, 4)
    ]
    db.add_all(categories)
    db.flush()

    # Create products with different creation times
    now = datetime.utcnow()
    products = []
    for i in range(1, 26):  # 25 test products
        product = Product(
            name=f"Product {i}",
            sku=f"SKU-{i:03d}",  # SKU is required
            description=f"Description {i}",
            base_price=10.0 * i,  # Changed from 'price' to 'base_price'
            created_at=now - timedelta(days=25 - i),  # Older products first
        )
        # Assign categories (each product gets 1-3 categories)
        for cat in categories[: (i % 3) + 1]:
            product.categories.append(cat)
        products.append(product)

    db.add_all(products)
    db.commit()

    # Test pagination
    client = TestClient(app)

    # First page (newest products first)
    response = client.get("/api/v1/products?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) == 10
    assert data["pagination"]["total"] == 25
    assert data["pagination"]["has_more"] is True

    # Verify order (newest first)
    product_dates = [p["created_at"] for p in data["data"]]
    assert product_dates == sorted(product_dates, reverse=True)

    # Get next page using cursor
    next_cursor = data["pagination"]["next"]
    response = client.get(f"/api/v1/products?limit=10&cursor={next_cursor}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 10

    # Get last page (should have 5 items)
    next_cursor = data["pagination"]["next"]
    response = client.get(f"/api/v1/products?limit=10&cursor={next_cursor}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 5
    assert data["pagination"]["has_more"] is False

    # Test filtering by category
    category_id = categories[0].id
    response = client.get(f"/api/v1/products?category_id={category_id}")
    assert response.status_code == 200
    data = response.json()
    # Each product should have the filtered category
    for product in data["data"]:
        assert any(cat["id"] == category_id for cat in product["categories"])

    # Test search
    response = client.get("/api/v1/products?q=Product 1")
    assert response.status_code == 200
    data = response.json()
    # Should find products with "1" in name (e.g., Product 1, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21)
    assert len(data["data"]) > 0

    # Clean up
    db.query(Product).delete()
    db.query(Category).delete()
    db.commit()
