"""Logging configuration shim.

Provides `configure_logging()` and `get_logger()` used by the app, delegating
to the unified utilities in `app.core.logging`.
"""
from __future__ import annotations

from .logging import get_logger as _get_logger, _ensure_basic_config


def configure_logging() -> None:
    """Apply a basic logging configuration if not already configured."""
    _ensure_basic_config()


def get_logger(name: str | None = None):
    return _get_logger(name)
