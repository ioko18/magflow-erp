#!/usr/bin/env python3
"""
Check database connectivity and table existence.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_async_session


async def check_database():
    """Check database connectivity and table existence."""
    print("🔍 Checking database connectivity...")

    try:
        async for session in get_async_session():
            # Test basic connectivity
            await session.execute(text("SELECT 1"))
            print("✅ Database connection successful")

            # Check if schema exists
            schema_result = await session.execute(
                text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'app'"
                )
            )
            schema_exists = schema_result.fetchone()

            if not schema_exists:
                print("❌ Schema 'app' does not exist")
                print("Creating schema 'app'...")
                await session.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
                await session.commit()
                print("✅ Schema 'app' created")
            else:
                print("✅ Schema 'app' exists")

            # Check if emag_product_offers table exists
            table_result = await session.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'app'
                    AND table_name = 'emag_product_offers'
                """
                )
            )
            table_exists = table_result.fetchone()

            if not table_exists:
                print("❌ Table 'app.emag_product_offers' does not exist")
                print("💡 You need to run database migrations:")
                print("   alembic upgrade head")
                return False
            else:
                print("✅ Table 'app.emag_product_offers' exists")

                # Check table structure
                columns_result = await session.execute(
                    text(
                        """
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_schema = 'app'
                        AND table_name = 'emag_product_offers'
                        ORDER BY ordinal_position
                    """
                    )
                )
                columns = columns_result.fetchall()
                print(f"📋 Table has {len(columns)} columns:")
                for col in columns[:5]:  # Show first 5 columns
                    print(f"   - {col[0]} ({col[1]})")
                if len(columns) > 5:
                    print(f"   ... and {len(columns) - 5} more columns")

            return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        print(f"🔧 Database URL: {settings.DATABASE_URL}")
        return False


async def main():
    """Main function."""
    print("🚀 MagFlow Database Check")
    print("=" * 40)

    success = await check_database()

    if success:
        print("\n✅ Database check completed successfully")
        print("💡 The backend should be able to connect to the database")
    else:
        print("\n❌ Database check failed")
        print("💡 Please fix the database issues before starting the backend")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
