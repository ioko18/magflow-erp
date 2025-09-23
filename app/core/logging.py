"""Utility logger for the MagFlow app.

Exposes a module-level `logger` and a `get_logger` helper for modules/tests
expecting `app.utils.logging.logger` to be available.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("magflow")


def get_logger(name: str | None = None):
    return logging.getLogger(name or "magflow")


def _ensure_basic_config():
    """Ensure basic logging configuration is set up."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
