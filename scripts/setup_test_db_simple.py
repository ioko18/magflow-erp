#!/usr/bin/env python3
"""
Simple script to set up the test database for MagFlow ERP.
"""
import asyncio
import asyncpg
import sys

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': '',
    'database': 'postgres'
}
TEST_DB = 'magflow_test'
TEST_SCHEMA = 'test'

async def setup_db():
    """Set up test database and schema."""
    try:
        # Connect to default DB
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Create test DB if needed
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB):
            await conn.execute(f'CREATE DATABASE {TEST_DB}')
        
        # Connect to test DB
        await conn.close()
        db_config = DB_CONFIG.copy()
        db_config['database'] = TEST_DB
        conn = await asyncpg.connect(**db_config)
        
        # Create schema if needed
        if not await conn.fetchval("SELECT 1 FROM information_schema.schemata WHERE schema_name = $1", TEST_SCHEMA):
            await conn.execute(f'CREATE SCHEMA {TEST_SCHEMA}')
        
        await conn.execute(f'SET search_path TO {TEST_SCHEMA}, public')
        print("Test database setup complete!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    result = asyncio.run(setup_db())
    sys.exit(0 if result else 1)
