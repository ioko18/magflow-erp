"""Script to check the database schema."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check_tables():
    """Check if tables were created in the app schema."""
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/magflow_test')
    
    try:
        async with engine.connect() as conn:
            # Check if tables exist in the app schema
            result = await conn.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'app';
                """)
            )
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables in 'app' schema: {tables}")
            
            # Check if the migration was recorded
            result = await conn.execute(
                text("""
                    SELECT version_num 
                    FROM app.alembic_version;
                """)
            )
            version = result.scalar()
            print(f"Current migration version: {version}")
            
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("Checking database schema...")
    asyncio.run(check_tables())
