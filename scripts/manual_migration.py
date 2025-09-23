"""Script to manually create the database schema."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def run_migration():
    """Run the manual migration."""
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/magflow_test')
    
    try:
        async with engine.begin() as conn:
            # Create the app schema if it doesn't exist
            await conn.execute(text('CREATE SCHEMA IF NOT EXISTS app'))
            
            # Set the search path
            await conn.execute(text('SET search_path TO app, public'))
            
            # Create the alembic_version table in the public schema if it doesn't exist
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS public.alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            '''))
            
            # Insert the initial migration version
            await conn.execute(text('''
                INSERT INTO public.alembic_version (version_num) 
                VALUES ('0001_initial_migration_manual') 
                ON CONFLICT DO NOTHING
            '''))
            
            # Create the tables in the app schema
            # Create enum types
            await conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mappingstatus') THEN
                        CREATE TYPE mappingstatus AS ENUM ('active', 'inactive', 'pending', 'deprecated');
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mappingtype') THEN
                        CREATE TYPE mappingtype AS ENUM ('product_id', 'category_id', 'brand_id', 'characteristic_id');
                    END IF;
                END
                $$;
            """))
            
            # Create tables
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS app.emag_product_mappings (
                    id SERIAL PRIMARY KEY,
                    internal_id VARCHAR(100) NOT NULL,
                    emag_id INTEGER NOT NULL,
                    internal_name VARCHAR(255) NOT NULL,
                    emag_name VARCHAR(255) NOT NULL,
                    status mappingstatus NOT NULL DEFAULT 'active',
                    category_id INTEGER,
                    brand_id INTEGER,
                    metadata_ JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    CONSTRAINT uq_emag_product_mappings_internal_id UNIQUE (internal_id),
                    CONSTRAINT uq_emag_product_mappings_emag_id UNIQUE (emag_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_emag_product_mappings_internal_id ON app.emag_product_mappings (internal_id);
                CREATE INDEX IF NOT EXISTS idx_emag_product_mappings_emag_id ON app.emag_product_mappings (emag_id);
                CREATE INDEX IF NOT EXISTS idx_emag_product_mappings_category_id ON app.emag_product_mappings (category_id);
                CREATE INDEX IF NOT EXISTS idx_emag_product_mappings_brand_id ON app.emag_product_mappings (brand_id);
                CREATE INDEX IF NOT EXISTS idx_emag_product_mappings_status ON app.emag_product_mappings (status);
                
                CREATE TABLE IF NOT EXISTS app.emag_category_mappings (
                    id SERIAL PRIMARY KEY,
                    internal_id VARCHAR(100) NOT NULL,
                    emag_id INTEGER NOT NULL,
                    internal_name VARCHAR(255) NOT NULL,
                    emag_name VARCHAR(255) NOT NULL,
                    status mappingstatus NOT NULL DEFAULT 'active',
                    parent_id INTEGER,
                    metadata_ JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    CONSTRAINT uq_emag_category_mappings_internal_id UNIQUE (internal_id),
                    CONSTRAINT uq_emag_category_mappings_emag_id UNIQUE (emag_id),
                    CONSTRAINT fk_emag_category_mappings_parent_id FOREIGN KEY (parent_id) 
                        REFERENCES app.emag_category_mappings (id) ON DELETE SET NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_emag_category_mappings_internal_id ON app.emag_category_mappings (internal_id);
                CREATE INDEX IF NOT EXISTS idx_emag_category_mappings_emag_id ON app.emag_category_mappings (emag_id);
                CREATE INDEX IF NOT EXISTS idx_emag_category_mappings_parent_id ON app.emag_category_mappings (parent_id);
                CREATE INDEX IF NOT EXISTS idx_emag_category_mappings_status ON app.emag_category_mappings (status);
                
                CREATE TABLE IF NOT EXISTS app.emag_brand_mappings (
                    id SERIAL PRIMARY KEY,
                    internal_id VARCHAR(100) NOT NULL,
                    emag_id INTEGER NOT NULL,
                    internal_name VARCHAR(255) NOT NULL,
                    emag_name VARCHAR(255) NOT NULL,
                    status mappingstatus NOT NULL DEFAULT 'active',
                    metadata_ JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    CONSTRAINT uq_emag_brand_mappings_internal_id UNIQUE (internal_id),
                    CONSTRAINT uq_emag_brand_mappings_emag_id UNIQUE (emag_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_emag_brand_mappings_internal_id ON app.emag_brand_mappings (internal_id);
                CREATE INDEX IF NOT EXISTS idx_emag_brand_mappings_emag_id ON app.emag_brand_mappings (emag_id);
                CREATE INDEX IF NOT EXISTS idx_emag_brand_mappings_status ON app.emag_brand_mappings (status);
                
                CREATE TABLE IF NOT EXISTS app.emag_characteristic_mappings (
                    id SERIAL PRIMARY KEY,
                    internal_id VARCHAR(100) NOT NULL,
                    emag_id INTEGER NOT NULL,
                    internal_name VARCHAR(255) NOT NULL,
                    emag_name VARCHAR(255) NOT NULL,
                    category_id INTEGER NOT NULL,
                    status mappingstatus NOT NULL DEFAULT 'active',
                    metadata_ JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    CONSTRAINT uq_emag_characteristic_mappings_internal_id UNIQUE (internal_id),
                    CONSTRAINT uq_emag_characteristic_mappings_emag_id UNIQUE (emag_id),
                    CONSTRAINT fk_emag_characteristic_mappings_category_id FOREIGN KEY (category_id) 
                        REFERENCES app.emag_category_mappings (id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_emag_characteristic_mappings_internal_id ON app.emag_characteristic_mappings (internal_id);
                CREATE INDEX IF NOT EXISTS idx_emag_characteristic_mappings_emag_id ON app.emag_characteristic_mappings (emag_id);
                CREATE INDEX IF NOT EXISTS idx_emag_characteristic_mappings_category_id ON app.emag_characteristic_mappings (category_id);
                CREATE INDEX IF NOT EXISTS idx_emag_characteristic_mappings_status ON app.emag_characteristic_mappings (status);
                
                CREATE TABLE IF NOT EXISTS app.emag_field_mappings (
                    id SERIAL PRIMARY KEY,
                    product_mapping_id INTEGER NOT NULL,
                    internal_field VARCHAR(100) NOT NULL,
                    emag_field VARCHAR(100) NOT NULL,
                    transform_function VARCHAR(255),
                    default_value TEXT,
                    is_required BOOLEAN NOT NULL DEFAULT TRUE,
                    validation_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
                    metadata_ JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    CONSTRAINT uq_emag_field_mappings_product_field UNIQUE (product_mapping_id, internal_field),
                    CONSTRAINT fk_emag_field_mappings_product_mapping_id FOREIGN KEY (product_mapping_id) 
                        REFERENCES app.emag_product_mappings (id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_emag_field_mappings_product_mapping_id ON app.emag_field_mappings (product_mapping_id);
                
                CREATE TABLE IF NOT EXISTS app.emag_sync_history (
                    id SERIAL PRIMARY KEY,
                    product_mapping_id INTEGER,
                    operation VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    items_processed INTEGER NOT NULL DEFAULT 0,
                    items_succeeded INTEGER NOT NULL DEFAULT 0,
                    items_failed INTEGER NOT NULL DEFAULT 0,
                    duration_seconds DOUBLE PRECISION,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
                    metadata_ JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    CONSTRAINT fk_emag_sync_history_product_mapping_id FOREIGN KEY (product_mapping_id) 
                        REFERENCES app.emag_product_mappings (id) ON DELETE SET NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_emag_sync_history_product_mapping_id ON app.emag_sync_history (product_mapping_id);
                CREATE INDEX IF NOT EXISTS idx_emag_sync_history_status ON app.emag_sync_history (status);
                CREATE INDEX IF NOT EXISTS idx_emag_sync_history_created_at ON app.emag_sync_history (created_at);
                
                CREATE TABLE IF NOT EXISTS app.emag_mapping_configs (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    config JSONB NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
                    description TEXT,
                    metadata_ JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                    CONSTRAINT uq_emag_mapping_configs_name UNIQUE (name)
                );
                
                -- Add foreign key constraints
                ALTER TABLE app.emag_product_mappings 
                    ADD CONSTRAINT fk_emag_product_mappings_category_id 
                    FOREIGN KEY (category_id) 
                    REFERENCES app.emag_category_mappings (id) 
                    ON DELETE SET NULL;
                    
                ALTER TABLE app.emag_product_mappings 
                    ADD CONSTRAINT fk_emag_product_mappings_brand_id 
                    FOREIGN KEY (brand_id) 
                    REFERENCES app.emag_brand_mappings (id) 
                    ON DELETE SET NULL;
            '''))
            
            print("Database schema created successfully.")
            
    except Exception as e:
        print(f"An error occurred while creating the database schema: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("Running manual database migration...")
    asyncio.run(run_migration())
