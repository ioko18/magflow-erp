#!/usr/bin/env python3
"""
Script pentru crearea sigură a tabelelor eMAG V2.
"""

import asyncio
from app.core.database import get_async_session, engine
from sqlalchemy import text


async def create_emag_tables_safe():
    """Creează tabelele eMAG V2 în mod sigur."""

    print("🗄️  Creez tabelele eMAG V2 în mod sigur...")

    try:
        async for db in get_async_session():
            # Creează tabelul emag_products_v2
            await db.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS emag_products_v2 (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    emag_id VARCHAR(50),
                    sku VARCHAR(100) NOT NULL,
                    name VARCHAR(500) NOT NULL,
                    account_type VARCHAR(10) NOT NULL DEFAULT 'main',
                    source_account VARCHAR(50),
                    description TEXT,
                    brand VARCHAR(200),
                    manufacturer VARCHAR(200),
                    price FLOAT,
                    currency VARCHAR(3) NOT NULL DEFAULT 'RON',
                    stock_quantity INTEGER DEFAULT 0,
                    category_id VARCHAR(50),
                    emag_category_id VARCHAR(50),
                    emag_category_name VARCHAR(200),
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    status VARCHAR(50),
                    images JSONB,
                    images_overwrite BOOLEAN NOT NULL DEFAULT false,
                    green_tax FLOAT,
                    supply_lead_time INTEGER,
                    safety_information TEXT,
                    manufacturer_info JSONB,
                    eu_representative JSONB,
                    emag_characteristics JSONB,
                    attributes JSONB,
                    specifications JSONB,
                    sync_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    last_synced_at TIMESTAMP,
                    sync_error TEXT,
                    sync_attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    emag_created_at TIMESTAMP,
                    emag_modified_at TIMESTAMP,
                    raw_emag_data JSONB
                )
            """
                )
            )

            # Creează indexuri pentru emag_products_v2
            await db.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_emag_products_sku_account ON emag_products_v2 (sku, account_type)
            """
                )
            )

            await db.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_emag_products_emag_id ON emag_products_v2 (emag_id)
            """
                )
            )

            await db.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_emag_products_sync_status ON emag_products_v2 (sync_status)
            """
                )
            )

            await db.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_emag_products_last_synced ON emag_products_v2 (last_synced_at)
            """
                )
            )

            # Creează constraint unic pentru SKU + account_type
            await db.execute(
                text(
                    """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'uq_emag_products_v2_sku_account'
                    ) THEN
                        ALTER TABLE emag_products_v2 
                        ADD CONSTRAINT uq_emag_products_v2_sku_account 
                        UNIQUE (sku, account_type);
                    END IF;
                END $$;
            """
                )
            )

            # Creează tabelul emag_sync_logs
            await db.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS emag_sync_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    sync_type VARCHAR(50) NOT NULL,
                    account_type VARCHAR(10) NOT NULL,
                    operation VARCHAR(50) NOT NULL,
                    sync_params JSONB,
                    status VARCHAR(50) NOT NULL DEFAULT 'running',
                    total_items INTEGER NOT NULL DEFAULT 0,
                    processed_items INTEGER NOT NULL DEFAULT 0,
                    created_items INTEGER NOT NULL DEFAULT 0,
                    updated_items INTEGER NOT NULL DEFAULT 0,
                    failed_items INTEGER NOT NULL DEFAULT 0,
                    errors JSONB,
                    warnings JSONB,
                    duration_seconds FLOAT,
                    pages_processed INTEGER NOT NULL DEFAULT 0,
                    api_requests_made INTEGER NOT NULL DEFAULT 0,
                    rate_limit_hits INTEGER NOT NULL DEFAULT 0,
                    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    triggered_by VARCHAR(100),
                    sync_version VARCHAR(20)
                )
            """
                )
            )

            await db.commit()
            print("✅ Tabelele eMAG V2 au fost create cu succes!")

            # Verifică tabelele create
            result = await db.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%emag%'
                ORDER BY table_name
            """
                )
            )
            tables = result.fetchall()

            print("\n📋 Tabele eMAG create:")
            for table in tables:
                print(f"  ✓ {table[0]}")

            break

    except Exception as e:
        print(f"❌ Eroare la crearea tabelelor: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_emag_tables_safe())
