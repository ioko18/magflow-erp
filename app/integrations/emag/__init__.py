"""eMAG Marketplace Integration

This package provides integration with the eMAG Marketplace API, supporting both
Seller-Fulfilled (MAIN) and Fulfilled by eMAG (FBE) account types.
"""

__version__ = "0.1.0"

# Import main components for easier access
# from .services.http_client.base import EmagClient
# Initialize logging
import logging
from pathlib import Path

from .config import EmagAccountType, EmagEnvironment, settings

# Ensure logs directory exists under project app root (avoid absolute path)
app_root = Path(__file__).resolve().parents[3]
log_dir = app_root / "logs"
log_dir.mkdir(parents=True, exist_ok=True, mode=0o755)

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "emag_integration.log"),
    ],
)

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
