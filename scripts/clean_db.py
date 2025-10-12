#!/usr/bin/env python3
"""Script to clean the database for development."""
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent / "app")
sys.path.insert(0, app_dir)

from sqlalchemy import text

from app.db.session import engine


def drop_schemas():
    """Drop all schemas and recreate them."""
    with engine.connect() as conn:
        # Drop all schemas and recreate them
        conn.execute(text("DROP SCHEMA IF EXISTS app CASCADE"))
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("CREATE SCHEMA app"))

        # Create extensions
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS " +
                         "uuid-ossp WITH SCHEMA public"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS " +
                         "pg_trgm WITH SCHEMA public"))

        conn.commit()

if __name__ == "__main__":
    if os.getenv("APP_ENV") != "development":
        print("Error: This script can only be run in development environment.")
        sys.exit(1)

    print("Dropping all schemas...")
    drop_schemas()
    print("Database cleaned successfully!")
