"""Enhanced database configuration with performance optimizations and PgBouncer support."""

import os
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, StaticPool


class DatabaseConfig:
    """Enhanced database configuration with optimizations for PgBouncer."""

    @staticmethod
    def get_database_url() -> str:
        """Get database URL with proper configuration for PgBouncer.
        
        Returns:
            str: The database connection URL
        """
        # Get base configuration
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = quote_plus(os.getenv("DB_PASS", "password"))
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "6432")  # Default to PgBouncer port
        db_name = os.getenv("DB_NAME", "magflow")

        # For PgBouncer, we need to use the transaction mode and add the application name
        return (
            f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?"
            "application_name=magflow_app&"
            "server_settings=application_name%3Dmagflow_app"
        )

    @classmethod
    def create_optimized_engine(cls) -> AsyncEngine:
        """Create database engine with performance optimizations for PgBouncer.
        
        Returns:
            AsyncEngine: The configured SQLAlchemy async engine
        """
        # Get pool settings
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        pool_pre_ping = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

        # When using PgBouncer in transaction mode, we need to disable SQLAlchemy's connection pooling
        # and let PgBouncer handle the pooling
        if os.getenv("PGBOUNCER_ENABLED", "true").lower() == "true":
            # For PgBouncer in transaction mode, use NullPool and let PgBouncer handle pooling
            return create_async_engine(
                cls.get_database_url(),
                poolclass=NullPool,  # Disable SQLAlchemy's connection pooling
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                future=True,
                connect_args={
                    "prepared_statement_cache_size": 0,  # Disable prepared statement cache
                    "statement_cache_size": 0,  # Disable statement cache
                    "server_settings": {
                        "application_name": "magflow_app",
                        "statement_timeout": "30000",  # 30 seconds
                        "idle_in_transaction_session_timeout": "30000",  # 30 seconds
                        "lock_timeout": "10000",  # 10 seconds
                        "idle_session_timeout": "60000",  # 60 seconds
                    },
                },
            )
        else:
            # Fallback to standard connection pooling if not using PgBouncer
            return create_async_engine(
                cls.get_database_url(),
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=pool_pre_ping,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                future=True,
                connect_args={
                    "server_settings": {
                        "application_name": "magflow_app",
                        "work_mem": os.getenv("DB_WORK_MEM", "16MB"),
                        "maintenance_work_mem": os.getenv("DB_MAINTENANCE_WORK_MEM", "128MB"),
                        "effective_cache_size": os.getenv("DB_EFFECTIVE_CACHE_SIZE", "1GB"),
                        "random_page_cost": os.getenv("DB_RANDOM_PAGE_COST", "1.1"),
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
