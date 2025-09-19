"""Logging utilities for MagFlow.

Provides a simple `get_logger` helper to standardize logger creation across the codebase.
This module acts as a compatibility shim for modules importing `app.core.logging`.
"""
import logging
from pathlib import Path

# Ensure logs directory exists under the project app root
APP_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = APP_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_basic_config() -> None:
    """Ensure a basic logging configuration is applied once."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(LOG_DIR / "app.log"),
            ],
        )


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Optional logger name. Defaults to module name if None.

    Returns:
        logging.Logger: A configured logger instance.
    """
    _ensure_basic_config()
    return logging.getLogger(name or __name__)
