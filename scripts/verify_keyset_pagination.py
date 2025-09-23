"""Script to verify keyset pagination index usage."""

import asyncio
from sqlalchemy import text
from app.db import async_session


async def check_index_usage():
    """Check if the composite index is being used for keyset pagination."""
    queries = [
        """
        EXPLAIN ANALYZE
        SELECT * FROM products
        WHERE (created_at, id) < (NOW(), 1000)
        ORDER BY created_at DESC, id DESC
        LIMIT 25;
        """,
        """
        EXPLAIN ANALYZE
        SELECT * FROM categories
        WHERE (created_at, id) < (NOW(), 1000)
        ORDER BY created_at DESC, id DESC
        LIMIT 25;
        """,
    ]

    async with async_session() as session:
        for query in queries:
            print("\n" + "=" * 80)
            print("Checking query:")
            print(query.strip())
            print("\nQuery Plan:")
            result = await session.execute(text(query))
            for row in result:
                print(row[0])


if __name__ == "__main__":
    asyncio.run(check_index_usage())
