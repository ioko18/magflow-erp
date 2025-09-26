#!/usr/bin/env python3
"""Create database tables."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from app.db.base_class import Base

# Load environment variables
load_dotenv()

def create_tables():
    """Create all tables."""
    # Get database URL from environment
    db_url = os.getenv("DB_URI") or f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    print(f"Database URL: {db_url}")
    engine = create_engine(db_url, echo=True)

    with engine.connect() as conn:
        # Set search path to app schema
        conn.execute(text(f"SET search_path TO {os.getenv('DB_SCHEMA', 'app')}, public"))
        Base.metadata.create_all(bind=engine)

    engine.dispose()
    print("✅ Tables created successfully!")

if __name__ == "__main__":
    create_tables()
