#!/usr/bin/env python3
"""
MagFlow ERP - Configuration and Health Check Script

This script validates the application configuration and database connectivity
before starting the application.
"""

import asyncio
import sys
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

import logging

from core.config import get_settings
from core.exceptions import ConfigurationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s (%(name)s)',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def validate_configuration():
    """Validate application configuration."""
    logger.info("🔧 Validating configuration...")

    try:
        settings = get_settings()
        logger.info("✅ Configuration validation passed")
        return settings
    except ConfigurationError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected configuration error: {e}")
        sys.exit(1)


async def validate_database(settings):
    """Validate database connectivity."""
    logger.info("🗄️  Validating database connectivity...")

    try:
        from core.database import health_checker

        # Check database health
        is_healthy = await health_checker.check_health()

        if not is_healthy:
            logger.error("❌ Database health check failed")
            sys.exit(1)

        logger.info("✅ Database connectivity validated")
        return True

    except Exception as e:
        logger.error(f"❌ Database validation failed: {e}")
        sys.exit(1)


async def validate_redis(settings):
    """Validate Redis connectivity if enabled."""
    if not settings.REDIS_ENABLED:
        logger.info("🔴 Redis is disabled, skipping validation")
        return True

    logger.info("🔴 Validating Redis connectivity...")

    try:
        import redis.asyncio as redis

        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            ssl=settings.REDIS_SSL
        )

        # Test connection
        await client.ping()
        logger.info("✅ Redis connectivity validated")
        return True

    except Exception as e:
        logger.error(f"❌ Redis validation failed: {e}")
        sys.exit(1)


async def main():
    """Main validation function."""
    logger.info("🚀 Starting MagFlow ERP validation...")

    try:
        # Validate configuration
        settings = await validate_configuration()

        # Validate database
        await validate_database(settings)

        # Validate Redis (if enabled)
        await validate_redis(settings)

        logger.info("🎉 All validations passed! System is ready.")
        logger.info(f"📊 Environment: {settings.APP_ENV}")
        logger.info(f"🔗 Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        logger.info(f"🔴 Redis: {'Enabled' if settings.REDIS_ENABLED else 'Disabled'}")

        return 0

    except KeyboardInterrupt:
        logger.info("🛑 Validation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Unexpected error during validation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
