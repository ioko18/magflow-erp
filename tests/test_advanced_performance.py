"""
Advanced Performance Tests for MagFlow ERP
==========================================

This test suite demonstrates the new Advanced Test Monitor system with:
- Real-time performance monitoring
- Intelligent database connection management
- Memory usage tracking
- Automated performance optimization
- Zero-configuration setup
- Robust error handling and cleanup
"""

import asyncio
import time
import uuid

import pytest
from sqlalchemy import select

from app.models.category import Category
from app.models.product import Product
from tests.advanced_test_monitor import get_advanced_monitor, monitor_test_performance

# Initialize advanced monitor
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/magflow_test"
monitor = get_advanced_monitor(TEST_DATABASE_URL)

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
@monitor_test_performance
async def test_advanced_create_product():
    """Test product creation with advanced monitoring."""
    test_context = monitor.start_test("advanced_create_product")

    try:
        async with monitor.get_session() as session:
            # Create category
            category = Category(
                name=f"Advanced Category {uuid.uuid4().hex[:8]}",
                description="Advanced test category",
            )
            session.add(category)
            await session.commit()
            await session.refresh(category)

            # Mark setup complete
            test_context["setup_time"] = time.time() - test_context["start_time"]

            # Create product
            product = Product(
                name=f"Advanced Product {uuid.uuid4().hex[:8]}",
                sku=f"ADV-{uuid.uuid4().hex[:8]}",
                base_price=149.99,
                currency="USD",
                description="Advanced test product",
                is_active=True,
            )

            product.categories.append(category)
            session.add(product)
            await session.commit()
            await session.refresh(product)

            # Verify creation
            assert product.id is not None
            assert product.name.startswith("Advanced Product")
            assert product.sku.startswith("ADV-")
            assert float(product.base_price) == 149.99
            assert product.is_active is True
            assert len(product.categories) == 1

            print(f"✅ Advanced product created: {product.name}")

    except Exception as e:
        monitor.end_test(test_context, error=str(e))
        raise
    else:
        monitor.end_test(test_context)


@pytest.mark.asyncio
@monitor_test_performance
async def test_advanced_query_products():
    """Test product querying with advanced monitoring."""
    test_context = monitor.start_test("advanced_query_products")

    try:
        async with monitor.get_session() as session:
            # Create test data
            category = Category(name=f"Query Category {uuid.uuid4().hex[:8]}")
            session.add(category)
            await session.commit()

            products = []
            for i in range(5):
                product = Product(
                    name=f"Query Product {i}",
                    sku=f"QRY-{i}-{uuid.uuid4().hex[:6]}",
                    base_price=100.0 + i * 10,
                    currency="USD",
                    is_active=True,
                )
                product.categories.append(category)
                products.append(product)

            session.add_all(products)
            await session.commit()

            # Mark setup complete
            test_context["setup_time"] = time.time() - test_context["start_time"]

            # Query products
            result = await session.execute(
                select(Product).where(Product.name.like("Query Product%")).limit(10)
            )
            retrieved_products = result.scalars().all()

            # Verify query results
            assert len(retrieved_products) == 5
            product_names = [p.name for p in retrieved_products]

            for i in range(5):
                assert f"Query Product {i}" in product_names

            print(f"✅ Successfully queried {len(retrieved_products)} products")

    except Exception as e:
        monitor.end_test(test_context, error=str(e))
        raise
    else:
        monitor.end_test(test_context)


@pytest.mark.asyncio
@monitor_test_performance
async def test_advanced_update_product():
    """Test product update with advanced monitoring."""
    test_context = monitor.start_test("advanced_update_product")

    try:
        async with monitor.get_session() as session:
            # Create product to update
            product = Product(
                name=f"Update Product {uuid.uuid4().hex[:8]}",
                sku=f"UPD-{uuid.uuid4().hex[:8]}",
                base_price=199.99,
                currency="USD",
                description="Original description",
                is_active=True,
            )

            session.add(product)
            await session.commit()
            await session.refresh(product)

            # Mark setup complete
            test_context["setup_time"] = time.time() - test_context["start_time"]

            # Update product
            original_name = product.name
            product.name = "Updated Advanced Product"
            product.description = "Updated description"
            product.base_price = 299.99
            product.is_active = False

            await session.commit()
            await session.refresh(product)

            # Verify update
            assert product.name == "Updated Advanced Product"
            assert product.name != original_name
            assert product.description == "Updated description"
            assert float(product.base_price) == 299.99
            assert not product.is_active

            print(f"✅ Product updated successfully: {product.name}")

    except Exception as e:
        monitor.end_test(test_context, error=str(e))
        raise
    else:
        monitor.end_test(test_context)


@pytest.mark.asyncio
@monitor_test_performance
async def test_advanced_delete_product():
    """Test product deletion with advanced monitoring."""
    test_context = monitor.start_test("advanced_delete_product")

    try:
        async with monitor.get_session() as session:
            # Create product to delete
            product = Product(
                name=f"Delete Product {uuid.uuid4().hex[:8]}",
                sku=f"DEL-{uuid.uuid4().hex[:8]}",
                base_price=99.99,
                currency="USD",
                is_active=True,
            )

            session.add(product)
            await session.commit()
            await session.refresh(product)

            product_id = product.id
            product_name = product.name

            # Mark setup complete
            test_context["setup_time"] = time.time() - test_context["start_time"]

            # Delete product
            await session.delete(product)
            await session.commit()

            # Verify deletion
            result = await session.execute(select(Product).filter_by(id=product_id))
            deleted_product = result.scalar_one_or_none()
            assert deleted_product is None

            print(f"✅ Product deleted successfully: {product_name}")

    except Exception as e:
        monitor.end_test(test_context, error=str(e))
        raise
    else:
        monitor.end_test(test_context)


@pytest.mark.asyncio
async def test_advanced_performance_report():
    """Generate and verify advanced performance report."""
    print("\n" + "=" * 80)
    print("🚀 Advanced Test Performance Report - MagFlow ERP")
    print("=" * 80)

    # Generate comprehensive report
    report = monitor.generate_report()
    print(report)

    # Get dashboard data
    dashboard = monitor.get_dashboard_data()

    # Verify we have data
    summary = dashboard.get("summary", {})
    assert summary.get("total_tests", 0) > 0, "No test data collected"

    # Performance verification
    avg_time = summary.get("avg_test_time", 0)
    performance_score = summary.get("performance_score", 0)

    print("\n🎯 Performance Verification:")
    print(f"  • Average test time: {avg_time:.3f}s")
    print(f"  • Performance score: {performance_score:.1f}/100")
    print(f"  • Total tests: {summary.get('total_tests', 0)}")
    print(f"  • Total errors: {summary.get('total_errors', 0)}")
    print(f"  • Memory usage: {summary.get('avg_memory_usage', 0):.1f} MB")

    # Save metrics for analysis
    monitor.save_metrics()

    # Reasonable performance assertions
    assert avg_time < 2.0, f"Average test time {avg_time:.3f}s is too slow"
    assert (
        performance_score >= 30
    ), f"Performance score {performance_score:.1f} is too low"
    assert (
        summary.get("total_errors", 0) == 0
    ), f"Found {summary.get('total_errors', 0)} errors"

    print("\n✅ Advanced performance monitoring system working correctly!")
    print("=" * 80)


@pytest.mark.asyncio
async def test_stress_database_connections():
    """Stress test database connection management."""
    test_context = monitor.start_test("stress_database_connections")

    try:
        # Test multiple concurrent connections
        tasks = []

        async def create_product_task(i):
            async with monitor.get_session() as session:
                product = Product(
                    name=f"Stress Product {i}",
                    sku=f"STRESS-{i}",
                    base_price=50.0 + i,
                    currency="USD",
                    is_active=True,
                )
                session.add(product)
                await session.commit()
                return product.id

        # Mark setup complete
        test_context["setup_time"] = time.time() - test_context["start_time"]

        # Create 10 concurrent tasks
        for i in range(10):
            tasks.append(create_product_task(i))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        successful_creates = [r for r in results if isinstance(r, int)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert (
            len(successful_creates) >= 8
        ), f"Only {len(successful_creates)}/10 products created successfully"
        assert len(errors) <= 2, f"Too many errors: {len(errors)}"

        print(
            "✅ Stress test completed: "
            f"{len(successful_creates)}/10 successful, "
            f"{len(errors)} errors"
        )

        if errors:
            monitor.end_test(
                test_context,
                warning=f"{len(errors)} connection errors during stress test",
            )
        else:
            monitor.end_test(test_context)

    except Exception as e:
        monitor.end_test(test_context, error=str(e))
        raise
