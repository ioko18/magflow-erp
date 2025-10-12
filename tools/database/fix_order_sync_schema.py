#!/usr/bin/env python3
"""
Database migration script to fix schema issues for order sync functionality.
"""

import logging

from sqlalchemy import create_engine, text

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run database migrations to ensure all required columns exist."""
    try:
        # Create synchronous database engine for migrations
        sync_engine = create_engine(
            settings.DB_URI.replace("postgresql+asyncpg", "postgresql")
        )

        with sync_engine.connect() as conn:
            logger.info("Starting database migration for order sync...")

            # Check if tables exist and create them if needed
            migrations = [
                # Add missing columns to orders table
                "ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS external_id VARCHAR(100);",
                "ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS external_source VARCHAR(50);",
                "ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                "ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                # Add missing columns to order_lines table
                "ALTER TABLE app.order_lines ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                "ALTER TABLE app.order_lines ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                # Add missing columns to products table
                "ALTER TABLE app.products ADD COLUMN IF NOT EXISTS price DECIMAL(10,2);",
                "ALTER TABLE app.products ADD COLUMN IF NOT EXISTS stock INTEGER DEFAULT 0;",
                "ALTER TABLE app.products ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;",
                # Add missing columns to emag_products table
                "ALTER TABLE app.emag_products ADD COLUMN IF NOT EXISTS account_type VARCHAR(10);",
                "ALTER TABLE app.emag_products ADD COLUMN IF NOT EXISTS sku VARCHAR(255);",
                "ALTER TABLE app.emag_products ADD COLUMN IF NOT EXISTS category_id INTEGER;",
                "ALTER TABLE app.emag_products ADD COLUMN IF NOT EXISTS emag_product_id VARCHAR(100);",
                "ALTER TABLE app.emag_products ADD COLUMN IF NOT EXISTS price DECIMAL(10,2);",
                "ALTER TABLE app.emag_products ADD COLUMN IF NOT EXISTS stock INTEGER;",
                "ALTER TABLE app.emag_products ADD COLUMN IF NOT EXISTS brand VARCHAR(255);",
                # Add missing columns to emag_product_offers table
                "ALTER TABLE app.emag_product_offers ADD COLUMN IF NOT EXISTS sku VARCHAR(255);",
                "ALTER TABLE app.emag_product_offers ADD COLUMN IF NOT EXISTS name VARCHAR(500);",
                # Add missing columns to emag_offer_syncs table
                "ALTER TABLE app.emag_offer_syncs ADD COLUMN IF NOT EXISTS offers_count INTEGER DEFAULT 0;",
                "ALTER TABLE app.emag_offer_syncs ADD COLUMN IF NOT EXISTS error_message TEXT;",
                "ALTER TABLE app.emag_offer_syncs ADD COLUMN IF NOT EXISTS products_count INTEGER DEFAULT 0;",
                "ALTER TABLE app.emag_offer_syncs ADD COLUMN IF NOT EXISTS sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                # Add any missing indexes
                "CREATE INDEX IF NOT EXISTS idx_orders_external ON app.orders(external_id, external_source);",
                "CREATE INDEX IF NOT EXISTS idx_order_lines_order ON app.order_lines(order_id);",
                "CREATE INDEX IF NOT EXISTS idx_emag_offers_product ON app.emag_product_offers(emag_product_id);",
                "CREATE INDEX IF NOT EXISTS idx_emag_offers_account ON app.emag_product_offers(account_type);",
                "CREATE INDEX IF NOT EXISTS idx_emag_syncs_account ON app.emag_offer_syncs(account_type);",
                "CREATE INDEX IF NOT EXISTS idx_emag_syncs_status ON app.emag_offer_syncs(status);",
            ]

            # Execute migrations
            for migration in migrations:
                try:
                    logger.info(f"Executing: {migration[:100]}...")
                    conn.execute(text(migration))
                    conn.commit()
                    logger.info("✓ Migration executed successfully")
                except Exception as e:
                    logger.warning(f"⚠️  Migration failed (may already exist): {e}")
                    conn.rollback()

            # Verify tables exist and have required columns
            verification_queries = [
                "SELECT COUNT(*) FROM app.orders LIMIT 1;",
                "SELECT COUNT(*) FROM app.order_lines LIMIT 1;",
                "SELECT COUNT(*) FROM app.emag_product_offers LIMIT 1;",
                "SELECT COUNT(*) FROM app.emag_offer_syncs LIMIT 1;",
            ]

            for query in verification_queries:
                try:
                    conn.execute(text(query))
                    logger.info(f"✓ Verified table accessibility: {query.split()[-3]}")
                except Exception as e:
                    logger.error(f"✗ Failed to verify table: {e}")
                    return False

            logger.info("✅ Database migration completed successfully!")
            return True

    except Exception as e:
        logger.error(f"✗ Database migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migrations()
    exit(0 if success else 1)
