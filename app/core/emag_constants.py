"""
eMAG API Constants and Enumerations.

This module contains all constants, error codes, and enumerations
from eMAG Marketplace API v4.4.8 specification.
"""

from enum import Enum
from typing import Dict


class OrderStatus(Enum):
    """Order processing status codes."""
    CANCELED = 0
    NEW = 1
    IN_PROGRESS = 2
    PREPARED = 3
    FINALIZED = 4
    RETURNED = 5


class OrderCompleteness(Enum):
    """Order completeness status."""
    INCOMPLETE = 0
    COMPLETE = 1


class FulfillmentType(Enum):
    """Order fulfillment type."""
    FBE = 2  # Fulfilled by eMAG
    FBS = 3  # Fulfilled by Seller


class PaymentMode(Enum):
    """Payment method codes."""
    COD = 1  # Cash on Delivery
    BANK_TRANSFER = 2
    CARD_ONLINE = 3


class PaymentStatus(Enum):
    """Payment status for online payments."""
    NOT_PAID = 0
    PAID = 1


class DeliveryMode(Enum):
    """Delivery method types."""
    COURIER = "courier"  # Home delivery
    PICKUP = "pickup"  # Locker/pickup point


# Order Cancellation Reasons (Section 5.1.6 from guide)
CANCELLATION_REASONS: Dict[int, str] = {
    1: "Lipsă stoc",
    2: "Anulat de client",
    3: "Clientul nu poate fi contactat",
    15: "Termen livrare curier prea mare",
    16: "Taxă transport prea mare",
    17: "Termen livrare prea mare până la intrarea produsului în stoc",
    18: "Ofertă mai bună în alt magazin",
    19: "Plata nu a fost efectuată",
    20: "Comandă nelivrată (motive curier)",
    21: "Alte motive",
    22: "Comandă incompletă – anulare automată",
    23: "Clientul s-a răzgândit",
    24: "La solicitarea clientului",
    25: "Livrare eșuată",
    26: "Expediere întârziată",
    27: "Comandă irelevantă",
    28: "Anulat de SuperAdmin la cererea sellerului",
    29: "Client în lista neagră",
    30: "Lipsă factură cu TVA",
    31: "Partener Marketplace eMAG a cerut anularea",
    32: "Timp estimat de livrare prea lung",
    33: "Produsul nu mai este disponibil în stocul partenerului",
    34: "Alte motive (generic)",
    35: "Livrarea este prea scumpă",
    36: "Clientul a găsit preț mai bun în altă parte",
    37: "Clientul a plasat o comandă similară în eMAG",
    38: "Clientul s-a răzgândit, nu mai dorește produsul",
    39: "Client eligibil doar pentru achiziție în rate",
}


# eMAG API Error Codes (Section 2.3 from guide)
class EmagErrorCode(Enum):
    """eMAG API error codes."""
    # Authentication errors
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_IP_NOT_WHITELISTED = "AUTH_IP_NOT_WHITELISTED"

    # Validation errors
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Business logic errors
    BUSINESS_INVALID_SKU = "BUSINESS_INVALID_SKU"
    BUSINESS_DUPLICATE_SKU = "BUSINESS_DUPLICATE_SKU"
    BUSINESS_INSUFFICIENT_STOCK = "BUSINESS_INSUFFICIENT_STOCK"


ERROR_CODE_MESSAGES: Dict[str, str] = {
    "AUTH_INVALID_CREDENTIALS": "Credentiale invalide",
    "AUTH_IP_NOT_WHITELISTED": "IP neautorizat",
    "VALIDATION_MISSING_FIELD": "Câmp obligatoriu lipsă",
    "VALIDATION_INVALID_FORMAT": "Format invalid",
    "RATE_LIMIT_EXCEEDED": "Limită rate depășită",
    "BUSINESS_INVALID_SKU": "SKU invalid",
    "BUSINESS_DUPLICATE_SKU": "SKU duplicat",
    "BUSINESS_INSUFFICIENT_STOCK": "Stoc insuficient",
}


# Rate Limiting Configuration (Section 2.1 from guide)
class RateLimits:
    """eMAG API rate limits per resource type."""
    ORDERS_RPS = 12  # Requests per second for orders
    ORDERS_RPM = 720  # Requests per minute for orders
    OTHER_RPS = 3  # Requests per second for other resources
    OTHER_RPM = 180  # Requests per minute for other resources
    JITTER_MAX = 0.1  # Maximum jitter in seconds


# HTTP Status Codes
class HttpStatus:
    """HTTP status codes used by eMAG API."""
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500


# Sync Configuration
class SyncConfig:
    """Default synchronization configuration."""
    MAX_PAGES_PER_SYNC = 100
    ITEMS_PER_PAGE = 100
    DEFAULT_DELAY_BETWEEN_REQUESTS = 1.2  # seconds
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 2  # seconds for exponential backoff
    RETRY_MAX_DELAY = 64  # seconds maximum wait time
    LOG_RETENTION_DAYS = 30


# Product Status
class ProductStatus(Enum):
    """Product status codes."""
    INACTIVE = 0
    ACTIVE = 1


# Monitoring Thresholds (Section 2.6 from guide)
class MonitoringThresholds:
    """Thresholds for monitoring and alerting."""
    HIGH_ERROR_RATE = 0.05  # 5% error rate
    SLOW_RESPONSE_MS = 2000  # 2 seconds
    RATE_LIMIT_WARNING = 0.8  # 80% of rate limit
    SYNC_SUCCESS_RATE = 0.95  # 95% success rate


def get_cancellation_reason_text(code: int) -> str:
    """Get human-readable text for cancellation reason code.
    
    Args:
        code: Cancellation reason code (1-39)
        
    Returns:
        Human-readable description of the cancellation reason
    """
    return CANCELLATION_REASONS.get(code, f"Unknown reason (code: {code})")


def get_order_status_text(status: int) -> str:
    """Get human-readable text for order status code.
    
    Args:
        status: Order status code (0-5)
        
    Returns:
        Human-readable description of the order status
    """
    status_map = {
        0: "Anulată",
        1: "Nouă",
        2: "În procesare",
        3: "Pregătită",
        4: "Finalizată",
        5: "Returnată",
    }
    return status_map.get(status, f"Status necunoscut ({status})")


def get_payment_mode_text(mode: int) -> str:
    """Get human-readable text for payment mode.
    
    Args:
        mode: Payment mode code (1-3)
        
    Returns:
        Human-readable description of the payment mode
    """
    mode_map = {
        1: "Numerar la livrare (COD)",
        2: "Transfer bancar",
        3: "Plată cu cardul online",
    }
    return mode_map.get(mode, f"Mod de plată necunoscut ({mode})")
