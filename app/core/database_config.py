"""Enhanced database configuration with performance optimizations."""

import os

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool


class DatabaseConfig:
    """Enhanced database configuration with optimizations."""

    @staticmethod
    def get_database_url():
        """Get database URL with proper configuration."""
        return (
            "postgresql+asyncpg://"
            f"{os.getenv('DB_USER', 'postgres')}:"
            f"{os.getenv('DB_PASS', 'password')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', 5432)}/"
            f"{os.getenv('DB_NAME', 'magflow')}"
        )

    @staticmethod
    def create_optimized_engine():
        """Create database engine with performance optimizations."""
        return create_async_engine(
            DatabaseConfig.get_database_url(),
            # Connection pool settings
            pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "30")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            # Performance settings
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            future=True,
            # Connection arguments for performance
            connect_args={
                "server_settings": {
                    "application_name": "MagFlow ERP",
                    "work_mem": "64MB",  # Increase working memory
                    "maintenance_work_mem": "256MB",  # Increase maintenance memory
                    "effective_cache_size": "1GB",  # Assume 1GB cache
                    "random_page_cost": "1.1",  # SSD optimization
                    # Remove effective_io_concurrency for macOS compatibility
                },
            },
        )

    @staticmethod
    def create_test_engine():
        """Create database engine for testing."""
        return create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )


# Production database optimizations
PRODUCTION_DB_SETTINGS = {
    "shared_buffers": "256MB",  # 25% of RAM
    "effective_cache_size": "1GB",  # 75% of RAM
    "work_mem": "64MB",  # Per-connection working memory
    "maintenance_work_mem": "256MB",  # Maintenance operations memory
    "checkpoint_segments": 32,  # Checkpoint frequency
    "checkpoint_completion_target": 0.9,  # Checkpoint target
    "wal_buffers": "16MB",  # WAL buffer size
    "random_page_cost": 1.1,  # SSD optimization
    "max_connections": 200,  # Maximum connections
}

# Development database settings
DEVELOPMENT_DB_SETTINGS = {
    "shared_buffers": "128MB",
    "effective_cache_size": "512MB",
    "work_mem": "32MB",
    "maintenance_work_mem": "128MB",
    "max_connections": 50,
}

# Testing database settings
TESTING_DB_SETTINGS = {
    "shared_buffers": "64MB",
    "effective_cache_size": "256MB",
    "work_mem": "16MB",
    "maintenance_work_mem": "64MB",
    "max_connections": 20,
}
