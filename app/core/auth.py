"""Simple authentication utilities."""

from typing import Optional

from fastapi import Request


async def get_current_user(request: Request) -> Optional[str]:
    """Get current user (no-op for now)."""
    # Mock user for when auth is not available
    return "mock_user"
