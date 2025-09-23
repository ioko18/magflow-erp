"""Script to check database connection and schema creation."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check_schema():
    """Check if the app schema exists and can be used."""
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/magflow_test')
    
    try:
        async with engine.connect() as conn:
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
            
            if not schema_exists:
                # Try to create the schema
                print("Creating 'app' schema...")
                await conn.execute(text("CREATE SCHEMA app"))
                await conn.commit()
                print("Schema 'app' created successfully.")
            
            # Check current search path
            result = await conn.execute(text("SHOW search_path;"))
            search_path = result.scalar()
            print(f"Current search_path: {search_path}")
            
            # Try to create a test table
            print("Creating test table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app.test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """))
            await conn.commit()
            print("Test table created successfully in 'app' schema.")
            
            # Verify the test table exists
            result = await conn.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'app' AND table_name = 'test_table';
                """)
            )
            table_exists = result.scalar() is not None
            print(f"Test table exists in 'app' schema: {table_exists}")
            
    except Exception as e:
        print(f"Error checking/creating schema: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("Checking database connection and schema...")
    asyncio.run(check_schema())
