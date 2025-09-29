#!/usr/bin/env python3
"""Simple admin user creation script."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import get_async_session
from app.core.security import get_password_hash
from app.models.user import User
from app.models.role import Role
from sqlalchemy import select

async def create_admin_user():
    """Create admin user using SQLAlchemy models."""
    print("🔧 Creating admin user...")
    
    try:
        async for session in get_async_session():
            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.email == "admin@magflow.local")
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("✅ Admin user already exists")
                print(f"   Email: {existing_user.email}")
                return
            
            # Create admin user
            hashed_password = get_password_hash("secret")
            admin_user = User(
                email="admin@magflow.local",
                hashed_password=hashed_password,
                full_name="Admin User",
                is_superuser=True,
                is_active=True,
                email_verified=True
            )
            
            session.add(admin_user)
            await session.flush()  # Get the user ID
            
            # Check if admin role exists
            result = await session.execute(
                select(Role).where(Role.name == "admin")
            )
            admin_role = result.scalar_one_or_none()
            
            if not admin_role:
                admin_role = Role(
                    name="admin",
                    description="Administrator role",
                    is_system_role=True
                )
                session.add(admin_role)
                await session.flush()
            
            # Assign role to user
            admin_user.roles.append(admin_role)
            
            await session.commit()
            
            print("✅ Admin user created successfully!")
            print("   Email: admin@magflow.local")
            print("   Password: secret")
            print("   Role: admin")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_admin_user())
