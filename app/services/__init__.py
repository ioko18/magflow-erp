# Local shim for aiohttp used only by tests.
from unittest.mock import AsyncMock

from . import web

ClientSession = AsyncMock
ClientTimeout = AsyncMock
ClientError = AsyncMock
ClientResponse = AsyncMock

__all__ = ["ClientError", "ClientResponse", "ClientSession", "ClientTimeout", "web"]
