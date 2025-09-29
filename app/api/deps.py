# Compatibility shim for legacy imports
# This module re-exports the public symbols from `dependencies.py` so that
# existing code (including tests) that does `from app.api import deps` continues to work.

from .dependencies import *  # noqa: F403,F401
