import asyncio

import asyncpg

from app.core.config import settings


async def test_connection():
    # Direct connection parameters (bypassing URL parsing)
    db_params = {
        "host": "pgbouncer",
        "port": 6432,
        "user": "app",
        "password": "app_password_change_me",
        "database": "magflow",
        "statement_cache_size": 0,  # Disable prepared statements
        "command_timeout": 30,
    }

    print(f"Connecting to database with params: {db_params}")

    try:
        # Create a connection with minimal parameters
        conn = await asyncpg.connect(**db_params)
        print("Successfully connected to database!")

        # Set the search path
        await conn.execute(f"SET search_path TO {settings.search_path}")

        # Test a simple query
        result = await conn.fetchval("SELECT 1")
        print(f"Test query result: {result}")

        # Test querying a table
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM products")
            print(f"Found {count} products in the database")
        except Exception as e:
            print(f"Note: Could not query products table: {e}")

    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise
    finally:
        if "conn" in locals():
            await conn.close()
            print("Database connection closed")


if __name__ == "__main__":
    asyncio.run(test_connection())
