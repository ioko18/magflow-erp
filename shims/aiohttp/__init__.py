# Local shim for aiohttp used only by tests.
# Provides a minimal `web` submodule with a `Response` class exposing `.json()`.
from . import web  # noqa: F401
