#!/usr/bin/env python3
"""Script to reset the database to a clean state for development.

WARNING: This will drop all tables and data in the database!
Only run this in development environments.
"""
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent / "app")
sys.path.insert(0, app_dir)

from app.db.session import engine  # noqa: E402
from app.models.base import Base  # noqa: E402

def confirm_reset() -> bool:
    """Ask for confirmation before resetting the database."""
    if os.getenv("APP_ENV") != "development":
        print("Error: This script can only be run in development environment.")
        return False
        
    confirmation = input("""
    WARNING: This will DROP ALL TABLES in the database and recreate them.
    This will DELETE ALL DATA in the database.
    
    Type 'RESET' to confirm: """)
    return confirmation.strip().upper() == "RESET"

def reset_database() -> None:
    """Drop all tables and recreate them."""
    print("Dropping all tables...")
    
    # Drop all tables
    with engine.begin() as conn:
        # Drop all tables in the public and app schemas
        for schema in ["public", "app"]:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {schema}"))
        
        # Create extensions
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS " + 
                         "uuid-ossp WITH SCHEMA public"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS " + 
                         "pg_trgm WITH SCHEMA public"))
    
    print("Creating all tables...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("Database reset complete!")

if __name__ == "__main__":
    if confirm_reset():
        try:
            reset_database()
        except SQLAlchemyError as e:
            print(f"Error resetting database: {e}")
            sys.exit(1)
    else:
        print("Database reset cancelled.")
        sys.exit(0)
