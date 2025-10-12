"""Script to check the Alembic version table."""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_alembic_version():
    """Check the Alembic version table."""
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/magflow_test')

    try:
        async with engine.connect() as conn:
            # Check if the alembic_version table exists
            result = await conn.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'alembic_version';
                """)
            )
            table_exists = result.scalar() is not None
            print(f"Alembic version table exists in 'public' schema: {table_exists}")

            if table_exists:
                # Get the current version
                result = await conn.execute(text("SELECT version_num FROM public.alembic_version;"))
                version = result.scalar()
                print(f"Current Alembic version: {version}")

            # Check if the app schema exists
            result = await conn.execute(
                text("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name = 'app';
                """)
            )
            schema_exists = result.scalar() is not None
            print(f"Schema 'app' exists: {schema_exists}")

            # List all schemas
            result = await conn.execute(text("SELECT schema_name FROM information_schema.schemata;"))
            schemas = [row[0] for row in result.fetchall()]
            print(f"All schemas: {schemas}")

    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("Checking Alembic version...")
    asyncio.run(check_alembic_version())
