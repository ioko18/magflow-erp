"""Test data factories for MagFlow ERP tests."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import random
import string


def random_string(length: int = 10) -> str:
    """Generate a random string of fixed length."""
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for _ in range(length))


def create_product_data(
    name: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[float] = None,
    quantity: Optional[int] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create test product data with sensible defaults."""
    return {
        "name": name or f"Test Product {random_string(5)}",
        "description": description or f"Description for {name or 'test product'}",
        "price": price or round(random.uniform(1.0, 1000.0), 2),
        "quantity": quantity or random.randint(1, 1000),
        "created_at": datetime.now(timezone.utc),
        **kwargs,
    }


def create_batch_products(count: int = 10, **overrides) -> List[Dict[str, Any]]:
    """Create a batch of test products."""
    return [create_product_data(**overrides) for _ in range(count)]


def create_test_table_sql(table_name: str = "test_products") -> str:
    """Generate SQL for creating a test products table."""
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        price DECIMAL(10, 2) NOT NULL,
        quantity INTEGER NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ,
        metadata JSONB
    )
    """


def drop_test_table_sql(table_name: str = "test_products") -> str:
    """Generate SQL for dropping a test table."""
    return f"DROP TABLE IF EXISTS {table_name} CASCADE"
