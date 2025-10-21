#!/usr/bin/env python3
"""Create admin user for frontend (admin@magflow.com)."""

import sys
from datetime import datetime
from pathlib import Path

from passlib.hash import bcrypt
from sqlalchemy import create_engine, text

def create_frontend_admin():
    """Create admin user with credentials expected by frontend."""
    db_url = "postgresql+psycopg2://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@db:5432/magflow"
    engine = create_engine(db_url, echo=False)

    with engine.connect() as conn:
        # Set search path
        conn.execute(text("SET search_path TO app, public"))

        # Check if user exists
        result = conn.execute(
            text("SELECT COUNT(*) FROM users WHERE email = 'admin@magflow.com'")
        )
        user_exists = result.scalar()

        if user_exists:
            print("✅ Admin user (admin@magflow.com) already exists")
            return

        # Create admin user with frontend credentials
        hashed_password = bcrypt.hash("admin123")
        now = datetime.utcnow()
        
        conn.execute(
            text("""
            INSERT INTO users (
                email, hashed_password, full_name, 
                is_active, is_superuser, email_verified, 
                failed_login_attempts, created_at, updated_at
            )
            VALUES (
                :email, :password, :name, 
                :is_active, :is_superuser, :verified, 
                :failed_attempts, :created_at, :updated_at
            )
        """),
            {
                "email": "admin@magflow.com",
                "password": hashed_password,
                "name": "Admin User",
                "is_active": True,
                "is_superuser": True,
                "verified": True,
                "failed_attempts": 0,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Get role ID (admin role should already exist from migration)
        result = conn.execute(text("SELECT id FROM roles WHERE name = 'admin'"))
        role_id = result.scalar()

        # Get user ID
        result = conn.execute(
            text("SELECT id FROM users WHERE email = 'admin@magflow.com'")
        )
        user_id = result.scalar()

        # Assign role to user
        if role_id and user_id:
            conn.execute(
                text("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (:user_id, :role_id)
                ON CONFLICT (user_id, role_id) DO NOTHING
            """),
                {"user_id": user_id, "role_id": role_id},
            )
            print(f"✅ Assigned admin role to user")

        conn.commit()
        print("✅ Frontend admin user created successfully!")
        print("")
        print("📋 Login Credentials:")
        print("   Email:    admin@magflow.com")
        print("   Password: admin123")
        print("")


if __name__ == "__main__":
    create_frontend_admin()
