#!/usr/bin/env python3
"""Simple database connection test."""

import asyncio
import logging
import os
import sys
from typing import List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env.local if it exists
if os.path.exists('.env.local'):
    from dotenv import load_dotenv
    load_dotenv('.env.local')

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'magflow',
    'user': 'app',
    'password': 'pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0',
    'schema': 'app'
}

# Create database URL
DB_URL = f"postgresql+asyncpg://{DB_PARAMS['user']}:{DB_PARAMS['password']}@{DB_PARAMS['host']}:{DB_PARAMS['port']}/{DB_PARAMS['database']}"

async def test_connection():
    """Test database connection."""
    engine = create_async_engine(DB_URL, echo=True)
    
    try:
        async with engine.connect() as conn:
            # Set search path
            await conn.execute(text(f'SET search_path TO {DB_PARAMS["schema"]}, public'))
            
            # Test connection
            result = await conn.execute(text('SELECT 1'))
            logger.info(f"✅ Connection successful. Result: {result.scalar()}")
            
            # List tables
            result = await conn.execute(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema
                ORDER BY table_name
                """),
                {"schema": DB_PARAMS["schema"]}
            )
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"📋 Tables in schema: {', '.join(tables)}")
            
            # Show users
            if 'users' in tables:
                result = await conn.execute(text('SELECT email, is_superuser FROM users LIMIT 5'))
                users = [f"{row[0]}" for row in result.fetchall()]
                logger.info(f"👤 Users: {', '.join(users)}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False
    finally:
        await engine.dispose()

async def main():
    """Run the test."""
    logger.info("🚀 Starting database connection test...")
    success = await test_connection()
    if success:
        logger.info("✅ All tests completed successfully!")
    else:
        logger.error("❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
