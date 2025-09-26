"""Simple products API endpoint for testing."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/products", tags=["products"])

# Mock products data for testing
MOCK_PRODUCTS = [
    {
        "id": 1,
        "name": "Laptop Dell XPS 13",
        "price": 4599.99,
        "stock": 15,
        "status": "active",
        "categories": ["Electronics", "Computers"]
    },
    {
        "id": 2,
        "name": "iPhone 15 Pro",
        "price": 5999.99,
        "stock": 8,
        "status": "active",
        "categories": ["Electronics", "Mobile"]
    },
    {
        "id": 3,
        "name": "Samsung Galaxy S24",
        "price": 4299.99,
        "stock": 12,
        "status": "active",
        "categories": ["Electronics", "Mobile"]
    },
    {
        "id": 4,
        "name": "MacBook Air M2",
        "price": 6499.99,
        "stock": 5,
        "status": "active",
        "categories": ["Electronics", "Computers"]
    },
    {
        "id": 5,
        "name": "Sony WH-1000XM5",
        "price": 1299.99,
        "stock": 20,
        "status": "active",
        "categories": ["Electronics", "Audio"]
    },
    {
        "id": 6,
        "name": "Gaming Chair Pro",
        "price": 899.99,
        "stock": 0,
        "status": "inactive",
        "categories": ["Furniture", "Gaming"]
    }
]


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]], include_in_schema=False)
async def list_products():
    """List all products (mock data for testing)."""
    return MOCK_PRODUCTS


@router.get("/{product_id}", response_model=Dict[str, Any])
async def get_product(product_id: str):
    """Get a specific product by ID."""

    resolved_id: int | None
    if product_id.isdigit():
        resolved_id = int(product_id)
    else:
        resolved_id = None

    if resolved_id is not None:
        for product in MOCK_PRODUCTS:
            if product["id"] == resolved_id:
                return product

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product with ID '{product_id}' not found",
    )
