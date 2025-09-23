"""eMAG Integration Services

This package contains service modules for interacting with the eMAG Marketplace API.
"""

# Import services for easier access
from .conflict_resolution_service import ConflictResolutionService
from .data_transformation_service import DataTransformationService
from .emag_import_service import EmagImportService
from .emag_offer_import_service import EmagOfferImportService
from .http_client.base import EmagClient
from .http_client.exceptions import (
    EmagAPIError,
    EmagAuthenticationError,
    EmagConflictError,
    EmagConnectionError,
    EmagError,
    EmagRateLimitError,
    EmagResourceNotFoundError,
    EmagServerError,
    EmagTimeoutError,
    EmagValidationError,
    get_exception_for_status,
)

__all__ = [
    "ConflictResolutionService",
    "DataTransformationService",
    "EmagAPIError",
    "EmagAuthenticationError",
    "EmagClient",
    "EmagConflictError",
    "EmagConnectionError",
    "EmagError",
    "EmagImportService",
    "EmagOfferImportService",
    "EmagRateLimitError",
    "EmagResourceNotFoundError",
    "EmagServerError",
    "EmagTimeoutError",
    "EmagValidationError",
    "get_exception_for_status",
]
