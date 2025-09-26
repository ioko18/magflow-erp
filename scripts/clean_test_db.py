#!/usr/bin/env python3
"""
Script to clean up the test database.
"""
import asyncio
import asyncpg
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clean_database():
    """Clean up the test database."""
    conn = await asyncpg.connect('postgresql://postgres:@localhost:5432/magflow_test')
    try:
        logger.info("Starting database cleanup...")
        
        # Get all schemas except system schemas
        schemas = await conn.fetch("""
            SELECT nspname 
            FROM pg_catalog.pg_namespace 
            WHERE nspname NOT LIKE 'pg_%' 
            AND nspname != 'information_schema'
        """)
        
        # Drop all non-system schemas
        for schema in schemas:
            schema_name = schema['nspname']
            logger.info(f"Dropping schema: {schema_name}")
            await conn.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')
        
        # Recreate public and test schemas
        logger.info("Recreating schemas...")
        await conn.execute('CREATE SCHEMA public;')
        await conn.execute('CREATE SCHEMA test;')
        
        # Set default privileges
        await conn.execute('''
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO public;
            GRANT ALL ON SCHEMA test TO postgres;
            GRANT ALL ON SCHEMA test TO public;
        ''')
        
        # Set default search path
        await conn.execute('ALTER DATABASE magflow_test SET search_path TO test, public;')
        
        logger.info("Test database cleaned up successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning test database: {e}")
        return False
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(clean_database())
