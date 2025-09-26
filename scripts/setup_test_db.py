#!/usr/bin/env python3
"""
Script to set up the test database for MagFlow ERP.

This script will:
1. Connect to the PostgreSQL server
2. Create the test database if it doesn't exist
3. Create the test schema if it doesn't exist
"""
import asyncio
import asyncpg
import sys

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,  # Default PostgreSQL port
    'user': 'postgres',
    'password': '',  # Empty password for local development
    'database': 'postgres'  # Connect to default database first
}

# Test database configuration
TEST_DB_NAME = 'magflow_test'
TEST_SCHEMA = 'test'

async def setup_test_database():
    """Set up the test database and schema."""
    print("Setting up test database...")
    
    try:
        # Connect to the default 'postgres' database
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Check if the test database exists
        db_exists = await conn.fetchval(
            'SELECT 1 FROM pg_database WHERE datname = $1', 
            TEST_DB_NAME
        )
        
        # Create the test database if it doesn't exist
        if not db_exists:
            print(f"Creating database '{TEST_DB_NAME}'...")
            await conn.execute(f'CREATE DATABASE {TEST_DB_NAME}')
        else:
            print(f"Database '{TEST_DB_NAME}' already exists")
        
        # Close the connection to the default database
        await conn.close()
        
        # Update config to connect to the test database
        db_config = DB_CONFIG.copy()
        db_config['database'] = TEST_DB_NAME
        
        # Connect to the test database
        conn = await asyncpg.connect(**db_config)
        
        # Check if the schema exists
        schema_exists = await conn.fetchval(
            'SELECT 1 FROM information_schema.schemata WHERE schema_name = $1',
            TEST_SCHEMA
        )
        
        # Create the schema if it doesn't exist
        if not schema_exists:
            print(f"Creating schema '{TEST_SCHEMA}'...")
            await conn.execute(f'CREATE SCHEMA {TEST_SCHEMA}')
        else:
            print(f"Schema '{TEST_SCHEMA}' already exists")
        
        # Set the search path to the test schema
        await conn.execute(f'SET search_path TO {TEST_SCHEMA}, public')
        
        print("Test database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error setting up test database: {e}")
        return False
    finally:
        # Close the connection if it's open
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    # Run the async setup function
    result = asyncio.run(setup_test_database())
    sys.exit(0 if result else 1)

async def create_database():
    """Create the test database if it doesn't exist."""
    # Connect to the default 'postgres' database
    conn = await asyncpg.connect(
        host=test_config.TEST_DB_HOST,
        port=test_config.TEST_DB_PORT,
        user=test_config.TEST_DB_USER,
        password=test_config.TEST_DB_PASSWORD,
        database='postgres'
    )
    
    try:
        # Check if database exists
        db_exists = await conn.fetchval(
            'SELECT 1 FROM pg_database WHERE datname = $1',
            test_config.TEST_DB_NAME
        )
        
        if not db_exists:
            print(f"Creating database: {test_config.TEST_DB_NAME}")
            # Create the database with UTF-8 encoding
            await conn.execute(
                f'CREATE DATABASE {test_config.TEST_DB_NAME} ENCODING = \'UTF8\''
            )
            print(f"Database '{test_config.TEST_DB_NAME}' created successfully.")
        else:
            print(f"Database '{test_config.TEST_DB_NAME}' already exists.")
            
    except Exception as e:
        print(f"Error creating database: {e}")
        raise
    finally:
        await conn.close()

async def create_schema():
    """Create the test schema if it doesn't exist."""
    conn = await asyncpg.connect(
        host=test_config.TEST_DB_HOST,
        port=test_config.TEST_DB_PORT,
        user=test_config.TEST_DB_USER,
        password=test_config.TEST_DB_PASSWORD,
        database=test_config.TEST_DB_NAME
    )
    
    try:
        # Check if schema exists
        schema_exists = await conn.fetchval(
            'SELECT 1 FROM information_schema.schemata WHERE schema_name = $1',
            test_config.TEST_DB_SCHEMA
        )
        
        if not schema_exists:
            print(f"Creating schema: {test_config.TEST_DB_SCHEMA}")
            await conn.execute(f'CREATE SCHEMA {test_config.TEST_DB_SCHEMA}')
            print(f"Schema '{test_config.TEST_DB_SCHEMA}' created successfully.")
        else:
            print(f"Schema '{test_config.TEST_DB_SCHEMA}' already exists.")
            
    except Exception as e:
        print(f"Error creating schema: {e}")
        raise
    finally:
        await conn.close()

async def main():
    """Run the database setup."""
    print("Setting up test database...")
    print(f"Host: {test_config.TEST_DB_HOST}")
    print(f"Port: {test_config.TEST_DB_PORT}")
    print(f"User: {test_config.TEST_DB_USER}")
    print(f"Database: {test_config.TEST_DB_NAME}")
    print(f"Schema: {test_config.TEST_DB_SCHEMA}")
    
    try:
        await create_database()
        await create_schema()
        print("Test database setup completed successfully!")
    except Exception as e:
        print(f"Error setting up test database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
