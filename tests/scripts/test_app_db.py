#!/usr/bin/env python3
"""Test database connection using SQLAlchemy."""

import asyncio
import logging
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tests.config import test_config as cfg

# Ensure environment variables align with local development defaults before importing settings
os.environ.setdefault("DB_HOST", cfg.TEST_DB_HOST)
os.environ.setdefault("DB_PORT", str(cfg.TEST_DB_PORT))
os.environ.setdefault("DB_USER", cfg.TEST_DB_USER)
os.environ.setdefault("DB_PASS", cfg.TEST_DB_PASSWORD)
os.environ.setdefault("DB_NAME", cfg.TEST_DB_NAME)
os.environ.setdefault("DB_SCHEMA", cfg.TEST_DB_SCHEMA)
os.environ.setdefault("DATABASE_URL", cfg.TEST_DB_URL)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_engine():
    """Create async engine for the current event loop."""
    return create_async_engine(
        settings.DB_URI,
        echo=settings.DB_ECHO,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )


def get_session_factory(engine):
    """Create async session factory for the given engine."""
    return sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def test_connection():
    """Test database connection and basic queries."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            # Test raw SQL query
            logger.info(
                "Testing database connection %s...",
                settings.DB_URI,
            )
            result = await conn.execute(text("SELECT 1"))
            row = result.first()
            logger.info(f"✅ Database connection successful. Result: {row[0]}")
            
            # Test schema access
            result = await conn.execute(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema
                ORDER BY table_name
                """),
                {"schema": settings.DB_SCHEMA}
            )
            tables = [row[0] for row in result.fetchall()]
            logger.info(
                "📋 Found %s tables in '%s' schema: %s",
                len(tables),
                settings.DB_SCHEMA,
                ", ".join(tables),
            )
    finally:
        await engine.dispose()

async def test_models():
    """Test database models."""
    engine = get_engine()
    async_session_factory = get_session_factory(engine)
    
    try:
        async with async_session_factory() as session:
            try:
                # Test User model
                result = await session.execute(
                    text("SELECT email, is_superuser FROM app.users LIMIT 1")
                )
                user = result.first()
                if user:
                    logger.info(f"👤 Found user: {user.email} (Superuser: {user.is_superuser})")
                else:
                    logger.warning("⚠️ No users found in the database")
                
                # Test Role model
                result = await session.execute(
                    text("SELECT name, description FROM app.roles ORDER BY name")
                )
                roles = [f"{row[0]}" for row in result.fetchall()]
                if roles:
                    logger.info(f"🎭 Found roles: {', '.join(roles)}")
                
                # Commit any changes
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Error testing models: {e}", exc_info=True)
                raise
    finally:
        await engine.dispose()

async def main():
    """Run database tests."""
    logger.info("🚀 Starting database tests...")
    
    try:
        # Test connection
        await test_connection()
        
        # Test models
        await test_models()
        
        logger.info("\n✅ All database tests completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Database tests failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
