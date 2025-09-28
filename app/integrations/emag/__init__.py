"""eMAG Marketplace Integration

This package provides integration with the eMAG Marketplace API, supporting both
Seller-Fulfilled (MAIN) and Fulfilled by eMAG (FBE) account types.
"""

__version__ = "0.1.0"

# Import main components for easier access
# from .services.http_client.base import EmagClient
# Initialize logging
import logging
import logging.handlers
from pathlib import Path

from .config import (
    EmagAccountType,
    EmagEnvironment,
    settings,
)

__all__ = ["EmagAccountType", "EmagEnvironment", "settings"]

# Ensure logs directory exists under project app root (avoid absolute path)
app_root = Path(__file__).resolve().parents[3]
log_dir = app_root / "logs"
log_dir.mkdir(parents=True, exist_ok=True, mode=0o755)

# Set up logging with rotating file handler
log_file = log_dir / "emag_integration.log"

# Create a custom formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Use RotatingFileHandler to handle log rotation
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8',
)
file_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []  # Clear any existing handlers
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

# Suppress noisy loggers
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# Create a logger for this module
logger = logging.getLogger(__name__)


def get_client(account_type: str, **kwargs):
    """Get an eMAG API client for the specified account type.

    Args:
        account_type: Either 'main' or 'fbe'
        **kwargs: Additional arguments to pass to EmagClient

    Returns:
        EmagClient: Configured client for the specified account type

    """
    from .services.http_client.base import EmagClient

    return EmagClient(account_type=account_type, **kwargs)


__all__ = [
    "EmagAccountType",
    "EmagClient",
    "EmagEnvironment",
    "get_client",
    "settings",
]
