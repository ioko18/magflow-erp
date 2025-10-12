#!/usr/bin/env python3
"""
Test direct pentru endpoint-ul de produse.
"""

import asyncio

from sqlalchemy import text

from app.core.database import get_async_session


async def test_endpoint_query():
    """Testează direct query-ul folosit în endpoint."""

    print("🔍 Testez query-ul din endpoint...")

    async for db in get_async_session():
        # Testez query-ul exact ca în endpoint
        account_type = "main"
        include_inactive = False
        max_pages_per_account = 1

        # Build the WHERE clause based on parameters
        where_conditions = []
        params = {}

        if account_type != "both":
            where_conditions.append("account_type = :account_type")
            params["account_type"] = account_type

        if not include_inactive:
            where_conditions.append("is_active = true")

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        # Execute raw SQL query
        query = f"""
            SELECT id, sku, name, account_type, price, currency, stock_quantity,
                   is_active, status, brand, emag_category_name, last_synced_at, sync_status
            FROM app.emag_products_v2
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT :limit
        """
        params["limit"] = max_pages_per_account * 100

        print(f"Query: {query}")
        print(f"Params: {params}")

        result = await db.execute(text(query), params)
        products = result.fetchall()

        print(f"✅ Găsite {len(products)} produse")

        if products:
            print("🔍 Primele 3 produse:")
            for i, product in enumerate(products[:3]):
                print(
                    f"  {i+1}. {product.sku} - {product.name[:50]}... ({product.account_type})"
                )
        else:
            # Să verific ce produse există în general
            result2 = await db.execute(
                text(
                    "SELECT COUNT(*), account_type FROM app.emag_products_v2 GROUP BY account_type"
                )
            )
            counts = result2.fetchall()
            print("📊 Produse per cont:")
            for count in counts:
                print(f"  {count.account_type}: {count.count}")

            # Să verific valorile is_active
            result3 = await db.execute(
                text(
                    "SELECT COUNT(*), is_active FROM app.emag_products_v2 GROUP BY is_active"
                )
            )
            active_counts = result3.fetchall()
            print("📊 Produse per status activ:")
            for count in active_counts:
                print(f"  is_active={count.is_active}: {count.count}")

        break


if __name__ == "__main__":
    asyncio.run(test_endpoint_query())
