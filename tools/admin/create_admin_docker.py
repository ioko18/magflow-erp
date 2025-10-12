#!/usr/bin/env python3
"""Create admin user."""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from datetime import datetime

from passlib.hash import bcrypt
from sqlalchemy import create_engine, text


def create_admin_user():
    """Create admin user."""
    db_url = "postgresql+psycopg2://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@db:5432/magflow"
    engine = create_engine(db_url, echo=True)

    with engine.connect() as conn:
        # Set search path
        conn.execute(text("SET search_path TO app, public"))

        # Check if user exists
        result = conn.execute(text("SELECT COUNT(*) FROM users WHERE email = 'admin@magflow.local'"))
        user_exists = result.scalar()

        if user_exists:
            print("Admin user already exists")
            return

        # Create admin user
        hashed_password = bcrypt.hash("secret")
        now = datetime.utcnow()
        conn.execute(text("""
            INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser, email_verified, failed_login_attempts, created_at, updated_at)
            VALUES (:email, :password, :name, :is_active, :is_superuser, :verified, :failed_attempts, :created_at, :updated_at)
        """), {
            "email": "admin@magflow.local",
            "password": hashed_password,
            "name": "Admin User",
            "is_active": True,
            "is_superuser": True,
            "verified": True,
            "failed_attempts": 0,
            "created_at": now,
            "updated_at": now
        })

        # Get role ID (admin role should already exist from migration)
        result = conn.execute(text("SELECT id FROM roles WHERE name = 'admin'"))
        role_id = result.scalar()

        # Get user ID
        result = conn.execute(text("SELECT id FROM users WHERE email = 'admin@magflow.local'"))
        user_id = result.scalar()

        # Assign role to user
        if role_id and user_id:
            conn.execute(text("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (:user_id, :role_id)
                ON CONFLICT (user_id, role_id) DO NOTHING
            """), {
                "user_id": user_id,
                "role_id": role_id
            })

        conn.commit()
        print("✅ Admin user created successfully!")

if __name__ == "__main__":
    create_admin_user()
