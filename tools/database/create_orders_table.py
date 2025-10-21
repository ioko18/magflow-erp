#!/usr/bin/env python3
"""
Script to create emag_orders table in the database.
Run this to fix the missing table issue.
"""

import asyncio

from sqlalchemy import text

from app.core.database import async_session_factory


async def create_orders_table():
    """Create the emag_orders table with all required fields."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS app.emag_orders (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        emag_order_id INTEGER NOT NULL,
        account_type VARCHAR(10) NOT NULL DEFAULT 'main',

        -- Order status and type
        status INTEGER NOT NULL,
        status_name VARCHAR(50),
        type INTEGER,
        is_complete BOOLEAN NOT NULL DEFAULT FALSE,

        -- Customer information
        customer_id INTEGER,
        customer_name VARCHAR(200),
        customer_email VARCHAR(200),
        customer_phone VARCHAR(50),

        -- Financial information
        total_amount FLOAT NOT NULL DEFAULT 0.0,
        currency VARCHAR(3) NOT NULL DEFAULT 'RON',

        -- Payment information
        payment_method VARCHAR(50),
        payment_mode_id INTEGER,
        detailed_payment_method VARCHAR(100),
        payment_status INTEGER,
        cashed_co FLOAT,
        cashed_cod FLOAT,

        -- Shipping information
        delivery_mode VARCHAR(50),
        shipping_tax FLOAT,
        shipping_tax_voucher_split JSONB,
        shipping_address JSONB,
        billing_address JSONB,

        -- Delivery details
        locker_id VARCHAR(50),
        locker_name VARCHAR(200),

        -- AWB and tracking
        awb_number VARCHAR(100),
        courier_name VARCHAR(100),

        -- Documents
        invoice_url TEXT,
        invoice_uploaded_at TIMESTAMP,

        -- Order items and vouchers
        products JSONB,
        vouchers JSONB,
        attachments JSONB,

        -- Special flags
        is_storno BOOLEAN NOT NULL DEFAULT FALSE,

        -- Order lifecycle timestamps
        acknowledged_at TIMESTAMP,
        finalized_at TIMESTAMP,

        -- Sync tracking
        sync_status VARCHAR(50) NOT NULL DEFAULT 'pending',
        last_synced_at TIMESTAMP,
        sync_error TEXT,
        sync_attempts INTEGER NOT NULL DEFAULT 0,

        -- Timestamps
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        order_date TIMESTAMP,
        emag_created_at TIMESTAMP,
        emag_modified_at TIMESTAMP,

        -- Raw eMAG data
        raw_emag_data JSONB,

        -- Constraints
        CONSTRAINT uq_emag_orders_id_account UNIQUE (emag_order_id, account_type),
        CONSTRAINT ck_emag_orders_account_type CHECK (account_type IN ('main', 'fbe')),
        CONSTRAINT ck_emag_orders_status CHECK (status IN (0,1,2,3,4,5)),
        CONSTRAINT ck_emag_orders_type CHECK (type IN (2,3))
    );
    """

    indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_emag_orders_emag_id_account "
            "ON app.emag_orders (emag_order_id, account_type)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_emag_orders_account "
            "ON app.emag_orders (account_type)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_emag_orders_status "
            "ON app.emag_orders (status)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_emag_orders_sync_status "
            "ON app.emag_orders (sync_status)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_emag_orders_order_date "
            "ON app.emag_orders (order_date)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_emag_orders_customer_email "
            "ON app.emag_orders (customer_email)"
        ),
    ]

    async with async_session_factory() as session:
        try:
            print("Creating emag_orders table...")
            await session.execute(text(create_table_sql))

            print("Creating indexes...")
            for idx_sql in indexes:
                await session.execute(text(idx_sql))

            await session.commit()
            print("✅ Successfully created emag_orders table and indexes!")

            # Verify table exists
            result = await session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'app' AND table_name = 'emag_orders'
            """))
            count = result.scalar()

            if count > 0:
                print("✅ Verified: emag_orders table exists in app schema")
            else:
                print("❌ Warning: Table creation may have failed")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating table: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(create_orders_table())
