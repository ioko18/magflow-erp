import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, app_dir)

# Import the settings to get the database schema
from app.core.config import settings  # noqa: E402

# Import the Base class to get the metadata
from app.db.base_class import Base  # noqa: E402

# Import all models to ensure they are registered with SQLAlchemy's metadata
# This is necessary for Alembic to detect all models
import app.models  # noqa: F401, E402

# Set the schema for all tables using sanitized value
schema_name = settings.db_schema_safe
for table in Base.metadata.tables.values():
    table.schema = schema_name

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

if config is not None:
    # Align Alembic configuration with runtime settings to avoid stale URLs
    config.set_main_option("sqlalchemy.url", settings.alembic_url)
    config.set_section_option("alembic", "search_path", f"{schema_name},public")
    config.set_section_option("alembic", "version_table_schema", schema_name)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def do_run_migrations(connection: Connection) -> None:
    """Run migrations in the given connection.
    
    Args:
        connection: SQLAlchemy connection to use for migrations
    """
    # Configure context with schema settings
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,  # Include all schemas in autogenerate
        version_table_schema=schema_name,  # Store version in app schema
        include_name=include_name,  # Function to filter object names
        compare_type=True,  # Check for column type changes
        compare_server_default=True,  # Check for server default changes
    )
    
    # Create the schema if it doesn't exist
    with context.begin_transaction():
        connection.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
        )

        # Set the search path for this connection
        connection.execute(
            text(f'SET search_path TO "{schema_name}", public')
        )
        
        # Run migrations
        context.run_migrations()


def include_name(name, type_, parent_names):
    """Filter which tables to include in autogenerate.
    
    Args:
        name: The name of the object
        type_: Type of the object (e.g., 'table', 'column', 'index', etc.)
        parent_names: Dictionary of parent object names
        
    Returns:
        bool: Whether to include the object in autogenerate
    """
    if type_ == 'schema':
        # Only include the app schema
        return name == schema_name
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=schema_name,
        include_name=include_name,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
        )
        context.execute(
            text(f'SET search_path TO "{schema_name}", public')
        )
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using AsyncEngine.

    In this scenario we need to create an AsyncEngine
    and associate a connection with the context.
    """
    # Create an async engine
    connectable = create_async_engine(settings.DB_URI, future=True)
    
    async with connectable.connect() as connection:
        # Set the search path for this connection
        await connection.execute(
            text(f'SET search_path TO "{schema_name}", public')
        )
        
        # Create the schema if it doesn't exist
        await connection.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
        )
        await connection.commit()
        
        # Run migrations
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()


if __name__ == "__main__":
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())
