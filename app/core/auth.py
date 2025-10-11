"""Simple authentication utilities."""


from fastapi import Request


async def get_current_user(request: Request) -> str | None:
    """Get current user (no-op for now)."""
    # Mock user for when auth is not available
    return "mock_user"
