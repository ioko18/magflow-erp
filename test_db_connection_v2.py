#!/usr/bin/env python3
"""
Simple database connection test
"""

from sqlalchemy import create_engine, text

def test_db_connection():
    """Test database connection"""
    try:
        engine = create_engine(
            "postgresql://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:6432/postgres",
            echo=True
        )

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✅ Database connection successful: {result.scalar()}")

            # Test inserting into emag_products
            conn.execute(text("""
                INSERT INTO app.emag_products (emag_id, name, characteristics, images, is_active, raw_data)
                VALUES (:emag_id, :name, :characteristics, :images, :is_active, :raw_data)
            """), {
                "emag_id": "test-101",
                "name": "Test Product 2",
                "characteristics": "{}",
                "images": "[]",
                "is_active": True,
                "raw_data": "{}"
            })
            conn.commit()
            print("✅ Product insertion successful")

            # Check count
            result = conn.execute(text("SELECT COUNT(*) FROM app.emag_products WHERE emag_id LIKE 'test-%'"))
            count = result.scalar()
            print(f"📊 Test products count: {count}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_db_connection()
