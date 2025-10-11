#!/usr/bin/env python3
"""Test script to reproduce the 500 errors on suppliers and products endpoints."""

import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')

from app.models.supplier import Supplier
from app.models.product import Product

DATABASE_URL = "postgresql+asyncpg://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:5433/magflow"

async def test_suppliers_query():
    """Test the suppliers query that's failing."""
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("\n=== Testing Suppliers Query ===")
            query = select(Supplier).where(Supplier.is_active).limit(10)
            result = await session.execute(query)
            suppliers = result.scalars().all()
            print(f"✓ Found {len(suppliers)} suppliers")
            for supplier in suppliers:
                print(f"  - {supplier.name} (ID: {supplier.id})")
        except Exception as e:
            print(f"✗ Error querying suppliers: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()

async def test_products_query():
    """Test the products query that's failing."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("\n=== Testing Products Query ===")
            query = select(Product).limit(20)
            result = await session.execute(query)
            products = result.scalars().all()
            print(f"✓ Found {len(products)} products")
            for product in products[:5]:
                print(f"  - {product.name} (SKU: {product.sku})")
        except Exception as e:
            print(f"✗ Error querying products: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()

async def main():
    """Run all tests."""
    await test_suppliers_query()
    await test_products_query()

if __name__ == "__main__":
    asyncio.run(main())
