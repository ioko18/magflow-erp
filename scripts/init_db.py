#!/usr/bin/env python3
"""Initialize the database schema directly."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def init_db():
    """Initialize the database schema."""
    # Create engine without schema and disable prepared statements for PgBouncer
    db_url = "postgresql+asyncpg://app:app_password_change_me@pgbouncer:6432/magflow"
    engine = create_async_engine(
        db_url,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )

    # Create schema and tables
    async with engine.begin() as conn:
        # Create schema if not exists
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS app"))

        # Create extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))

        # Create products table
        await conn.execute(
            text("""
        CREATE TABLE IF NOT EXISTS app.products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            price NUMERIC(12, 2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        )

        # Create categories table
        await conn.execute(
            text("""
        CREATE TABLE IF NOT EXISTS app.categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        )

        # Create product_categories join table
        await conn.execute(
            text("""
        CREATE TABLE IF NOT EXISTS app.product_categories (
            product_id INTEGER REFERENCES app.products(id) ON DELETE CASCADE,
            category_id INTEGER REFERENCES app.categories(id) ON DELETE CASCADE,
            PRIMARY KEY (product_id, category_id)
        )
        """)
        )

        # Create indexes
        await conn.execute(
            text("""
        CREATE INDEX IF NOT EXISTS idx_products_name_lower
        ON app.products (lower(name))
        """)
        )

        await conn.execute(
            text("""
        CREATE INDEX IF NOT EXISTS idx_products_price
        ON app.products (price)
        """)
        )

        await conn.execute(
            text("""
        CREATE INDEX IF NOT EXISTS idx_products_created_at
        ON app.products (created_at)
        """)
        )

        print("Database schema initialized successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
