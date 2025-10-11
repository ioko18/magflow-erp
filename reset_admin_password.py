#!/usr/bin/env python3
"""Reset admin password."""

import asyncio
import sys
sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.security import get_password_hash
from app.models.user import User

DATABASE_URL = "postgresql+asyncpg://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:5433/magflow"

async def reset_password():
    """Reset admin password to 'admin123'."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Get admin user
            result = await session.execute(
                select(User).where(User.email == 'admin@example.com')
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ Admin user not found")
                return
            
            # Hash new password
            new_password = "admin123"
            hashed_password = get_password_hash(new_password)
            
            # Update password
            user.hashed_password = hashed_password
            await session.commit()
            
            print(f"✓ Password reset successfully for {user.email}")
            print(f"  New password: {new_password}")
            
        except Exception as e:
            print(f"❌ Error resetting password: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_password())
