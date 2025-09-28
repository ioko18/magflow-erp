"""
Simple Performance Tests for MagFlow ERP
========================================

Robust, reliable performance tests using the Simple Performance Monitor.
This test suite focuses on stability and accurate performance measurement.
"""

import time
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.category import Category
from app.db.base_class import Base
from tests.simple_performance_monitor import get_simple_monitor

# Initialize simple monitor
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/magflow_test"
monitor = get_simple_monitor(TEST_DATABASE_URL)


# Set up test database (function-scoped for asyncio compatibility, but reuses engine)
@pytest_asyncio.fixture
async def db_engine():
    """Set up test database engine."""
    engine = await monitor.get_engine()
    # Ensure tables exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine


# Clean up database between tests
@pytest_asyncio.fixture(autouse=True)
async def clean_tables(db_engine):
    """Clean up database tables between tests."""
    async with db_engine.begin() as conn:
        # Delete all data from tables in reverse order of dependency
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(delete(table))
        await conn.commit()


# Database session fixture
@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a new database session for a test."""
    async with AsyncSession(db_engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_simple_create_product(db_session):
    """Test product creation with simple monitoring."""
    test_context = monitor.start_test("simple_create_product")

    try:
        # Create category
        category = Category(
            name=f"Simple Category {uuid.uuid4().hex[:8]}",
            description="Simple test category",
        )
        db_session.add(category)
        await db_session.flush()

        # Mark setup complete
        test_context["setup_time"] = time.time() - test_context["start_time"]

        # Create product
        product = Product(
            name=f"Simple Product {uuid.uuid4().hex[:8]}",
            sku=f"SMP-{uuid.uuid4().hex[:8]}",
            base_price=99.99,
            currency="USD",
            description="Simple test product",
            is_active=True,
        )

        product.categories.append(category)
        db_session.add(product)
        await db_session.flush()
        await db_session.refresh(product)

        # Verify creation
        assert product.id is not None
        assert product.name.startswith("Simple Product")
        assert product.sku.startswith("SMP-")
        assert float(product.base_price) == 99.99
        assert product.is_active is True
        assert len(product.categories) == 1

        await monitor.end_test(test_context)

    except Exception as e:
        await monitor.end_test(test_context, error=str(e))
        raise


@pytest.mark.asyncio
async def test_simple_query_products(db_session):
    """Test product querying with simple monitoring."""
    test_context = monitor.start_test("simple_query_products")

    try:
        # Create test data
        category = Category(name=f"Query Category {uuid.uuid4().hex[:8]}")
        db_session.add(category)
        await db_session.flush()

        # Create products in a single batch
        products = [
            Product(
                name=f"Query Product {i}",
                sku=f"QRY-{i}-{uuid.uuid4().hex[:6]}",
                base_price=100.0 + i * 10,
                currency="USD",
                is_active=True,
                categories=[category],
            )
            for i in range(3)
        ]

        db_session.add_all(products)
        await db_session.flush()

        # Mark setup complete
        test_context["setup_time"] = time.time() - test_context["start_time"]

        # Query products with explicit join for better performance
        result = await db_session.execute(
            select(Product)
            .where(Product.name.like("Query%"))
            .limit(10)
            .execution_options(populate_existing=True)
        )

        retrieved_products = result.scalars().all()

        # Verify query results
        assert (
            len(retrieved_products) == 3
        ), f"Expected 3 products, got {len(retrieved_products)}"

        # Check each expected product exists
        product_names = {p.name for p in retrieved_products}
        for i in range(3):
            expected_name = f"Query Product {i}"
            assert (
                expected_name in product_names
            ), f"Product {expected_name} not found in {product_names}"

        await monitor.end_test(test_context)

    except Exception as e:
        await monitor.end_test(test_context, error=str(e))
        raise


@pytest.mark.asyncio
async def test_simple_update_product(db_session):
    """Test product update with simple monitoring."""
    test_context = monitor.start_test("simple_update_product")

    try:
        # Create product to update
        product = Product(
            name=f"Update Product {uuid.uuid4().hex[:8]}",
            sku=f"UPD-{uuid.uuid4().hex[:8]}",
            base_price=199.99,
            currency="USD",
            description="Original description",
            is_active=True,
        )

        db_session.add(product)
        await db_session.flush()

        # Mark setup complete
        test_context["setup_time"] = time.time() - test_context["start_time"]

        # Update product
        product.name = "Updated Simple Product"
        product.description = "Updated description"
        product.base_price = 299.99
        product.is_active = False

        await db_session.flush()
        await db_session.refresh(product)

        # Verify update
        assert product.name == "Updated Simple Product"
        assert product.description == "Updated description"
        assert float(product.base_price) == 299.99
        assert not product.is_active

        await monitor.end_test(test_context)

    except Exception as e:
        await monitor.end_test(test_context, error=str(e))
        raise


@pytest.mark.asyncio
async def test_simple_delete_product(db_session):
    """Test product deletion with simple monitoring."""
    test_context = monitor.start_test("simple_delete_product")

    try:
        # Create product to delete
        product = Product(
            name=f"Delete Product {uuid.uuid4().hex[:8]}",
            sku=f"DEL-{uuid.uuid4().hex[:8]}",
            base_price=99.99,
            currency="USD",
            is_active=True,
        )

        db_session.add(product)
        await db_session.flush()  # Flush to get the ID without committing
        product_id = product.id

        # Mark setup complete
        test_context["setup_time"] = time.time() - test_context["start_time"]

        # Delete product
        product_to_delete = await db_session.get(Product, product_id)
        if product_to_delete:
            await db_session.delete(product_to_delete)
            await db_session.flush()

        # Verify deletion
        result = await db_session.execute(select(Product).filter_by(id=product_id))
        deleted_product = result.scalar_one_or_none()
        assert deleted_product is None, "Product was not deleted"

        await monitor.end_test(test_context)

    except Exception as e:
        await monitor.end_test(test_context, error=str(e))
        raise


@pytest.mark.asyncio
async def test_simple_performance_report():
    """Generate and verify simple performance report."""
    print("\n" + "=" * 60)
    print("🚀 Simple Performance Report - MagFlow ERP")
    print("=" * 60)

    # Generate comprehensive report
    report = monitor.generate_report()
    print(report)

    # Get summary
    summary = monitor.metrics.get_summary()

    # Verify we have data
    total_tests = summary.get("total_tests", 0)
    assert total_tests > 0, "No test data collected"

    # Performance verification
    avg_time = summary.get("avg_test_time", 0)
    performance_score = summary.get("performance_score", 0)
    total_errors = summary.get("total_errors", 0)

    print("🎯 Performance Verification:")
    print(f"  • Average test time: {avg_time:.3f}s")
    print(f"  • Performance score: {performance_score:.1f}/100")
    print(f"  • Total tests: {total_tests}")
    print(f"  • Total errors: {total_errors}")

    # Save metrics for analysis
    monitor.save_metrics()

    # Check for slow tests
    if avg_time > 0.5:  # 500ms threshold
        print("⚠️  Warning: Average test time is above 500ms")

    # Check for performance score
    if performance_score < 50:
        print(f"⚠️  Warning: Performance score is low ({performance_score:.1f}/100)")

    # Check for errors
    if total_errors > 0:
        print(f"❌ Found {total_errors} test errors")

    # Final assertions with more helpful error messages
    assert (
        avg_time < 3.0
    ), f"Average test time {avg_time:.3f}s is too slow. Consider optimizing slow tests."
    assert (
        performance_score >= 25
    ), f"Performance score {performance_score:.1f} is too low. Check for slow or failing tests."
    assert (
        total_errors == 0
    ), f"Found {total_errors} test errors. Fix failing tests first."

    print("\n✅ Simple performance monitoring system working correctly!")
    print("=" * 60)
