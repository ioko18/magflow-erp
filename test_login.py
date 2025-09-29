#!/usr/bin/env python3
"""Test login functionality directly."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import get_async_session
from app.core.security import create_access_token, verify_password
from app.models.user import User
from sqlalchemy import select
from datetime import timedelta

async def test_login():
    """Test login functionality."""
    print("🔧 Testing login functionality...")
    
    try:
        async for session in get_async_session():
            # Get user
            result = await session.execute(
                select(User).where(User.email == "admin@magflow.local")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ User not found")
                return
                
            print(f"✅ User found: {user.email}")
            print(f"   Active: {user.is_active}")
            print(f"   Superuser: {user.is_superuser}")
            
            # Test password verification
            password_ok = verify_password("secret", user.hashed_password)
            print(f"   Password verification: {password_ok}")
            
            if not password_ok:
                print("❌ Password verification failed")
                return
                
            # Test token creation
            access_token = create_access_token(
                subject=user.email,
                expires_delta=timedelta(minutes=30)
            )
            
            print(f"✅ Access token created: {access_token[:50]}...")
            
            print("✅ All login components working correctly!")
            
    except Exception as e:
        print(f"❌ Error testing login: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_login())
