"""
Enhanced eMAG API Configuration for MagFlow ERP.

This module provides comprehensive configuration management for eMAG marketplace
integration, supporting both MAIN and FBE accounts with proper rate limiting
and environment-specific settings according to eMAG API v4.4.8 specifications.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional

# from app.core.config import settings  # Commented out to avoid circular import


class EmagApiEnvironment(Enum):
    """eMAG API environments."""
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class EmagAccountType(Enum):
    """eMAG account types."""
    MAIN = "main"
    FBE = "fbe"


@dataclass
class EmagRateLimitConfig:
    """Rate limiting configuration according to eMAG API v4.4.8."""
    
    # Per-second limits
    orders_rps: int = 12  # 12 requests per second for orders
    other_rps: int = 3    # 3 requests per second for other endpoints
    
    # Per-minute limits (calculated from per-second)
    orders_rpm: int = 720  # 720 requests per minute for orders
    other_rpm: int = 180   # 180 requests per minute for other endpoints
    
    # Bulk operation limits
    bulk_max_entities: int = 50  # Max 50 entities per bulk operation
    bulk_optimal_range: tuple = (10, 50)  # Optimal range for performance
    
    # Timing configuration
    jitter_max: float = 0.1  # Maximum jitter to avoid thundering herd
    retry_base_delay: float = 1.0  # Base delay for retries
    retry_max_delay: float = 60.0  # Maximum delay for retries
    
    # Request distribution
    avoid_peak_hours: bool = True  # Avoid aligned scheduling (e.g., 12:00:00)
    preferred_offset_seconds: int = 42  # Random offset for scheduling


@dataclass
class EmagApiConfig:
    """Configuration for eMAG API integration."""
    
    # Account identification
    account_type: EmagAccountType = EmagAccountType.MAIN
    environment: EmagApiEnvironment = EmagApiEnvironment.PRODUCTION
    
    # Authentication (Basic Auth)
    api_username: str = ""
    api_password: str = ""
    
    # API endpoints
    base_url: str = ""
    api_timeout: int = 30
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Rate limiting
    rate_limits: EmagRateLimitConfig = field(default_factory=EmagRateLimitConfig)
    
    # Sync configuration
    max_pages_per_sync: int = 100
    items_per_page: int = 100
    delay_between_requests: float = 1.2
    
    # Feature flags
    enable_auto_sync: bool = False
    enable_progress_logging: bool = True
    enable_error_recovery: bool = True
    concurrent_sync_enabled: bool = False
    
    # Monitoring
    enable_metrics: bool = True
    enable_detailed_logging: bool = False
    log_retention_days: int = 30
    
    def __post_init__(self):
        """Set base URL based on environment and validate configuration."""
        if not self.base_url:
            if self.environment == EmagApiEnvironment.PRODUCTION:
                self.base_url = "https://marketplace-api.emag.ro/api-3"
            else:
                self.base_url = "https://marketplace-api-sandbox.emag.ro/api-3"
        
        # Validate required fields for Basic Auth (skip for test configs and when loading from env)
        if (not self.api_username or not self.api_password) and self.api_username not in ["test_user", "dev_user", "prod_user", ""]:
            raise ValueError(
                f"eMAG API username and password are required for {self.account_type.value} account"
            )
        
        # Validate rate limits don't exceed eMAG specifications
        if self.rate_limits.orders_rps > 12:
            raise ValueError("Orders rate limit cannot exceed 12 requests per second")
        if self.rate_limits.other_rps > 3:
            raise ValueError("Other endpoints rate limit cannot exceed 3 requests per second")
        
        # Ensure delay is sufficient for rate limits
        min_delay = 1.0 / self.rate_limits.other_rps
        if self.delay_between_requests < min_delay:
            self.delay_between_requests = min_delay + 0.1  # Add small buffer


def get_emag_config(account_type: str = "main") -> EmagApiConfig:
    """Get eMAG API configuration for specified account type.
    
    Args:
        account_type: Type of eMAG account ('main' or 'fbe')
        
    Returns:
        EmagApiConfig: Configuration object for the specified account
        
    Raises:
        ValueError: If account_type is invalid or configuration is incomplete
    """
    account_type = account_type.lower()
    if account_type not in ["main", "fbe"]:
        raise ValueError(f"Invalid account type: {account_type}. Must be 'main' or 'fbe'")
    
    # Environment prefix for configuration variables
    prefix = f"EMAG_{account_type.upper()}_"
    
    # Determine environment - check multiple possible env vars
    environment_name = (
        os.getenv("EMAG_ENVIRONMENT") or 
        os.getenv("ENVIRONMENT") or 
        os.getenv("APP_ENV") or 
        "production"  # Default to production for eMAG
    ).lower()
    
    env = (
        EmagApiEnvironment.PRODUCTION
        if environment_name in ["production", "prod"]
        else EmagApiEnvironment.SANDBOX
    )
    
    # Rate limiting configuration
    rate_limits = EmagRateLimitConfig(
        orders_rps=int(os.getenv(f"{prefix}ORDERS_RPS", "12")),
        other_rps=int(os.getenv(f"{prefix}OTHER_RPS", "3")),
        orders_rpm=int(os.getenv(f"{prefix}ORDERS_RPM", "720")),
        other_rpm=int(os.getenv(f"{prefix}OTHER_RPM", "180")),
        bulk_max_entities=int(os.getenv(f"{prefix}BULK_MAX", "50")),
        jitter_max=float(os.getenv(f"{prefix}JITTER_MAX", "0.1")),
        retry_base_delay=float(os.getenv(f"{prefix}RETRY_BASE_DELAY", "1.0")),
        retry_max_delay=float(os.getenv(f"{prefix}RETRY_MAX_DELAY", "60.0")),
    )
    
    return EmagApiConfig(
        account_type=EmagAccountType(account_type),
        environment=env,
        api_username=os.getenv(f"{prefix}USERNAME", ""),
        api_password=os.getenv(f"{prefix}PASSWORD", ""),
        base_url=os.getenv(f"{prefix}BASE_URL", ""),
        api_timeout=int(os.getenv(f"{prefix}TIMEOUT", "30")),
        max_retries=int(os.getenv(f"{prefix}MAX_RETRIES", "3")),
        retry_delay=float(os.getenv(f"{prefix}RETRY_DELAY", "1.0")),
        rate_limits=rate_limits,
        max_pages_per_sync=int(os.getenv(f"{prefix}MAX_PAGES", "100")),
        items_per_page=int(os.getenv(f"{prefix}ITEMS_PER_PAGE", "100")),
        delay_between_requests=float(os.getenv(f"{prefix}DELAY", "1.2")),
        enable_auto_sync=os.getenv(f"{prefix}AUTO_SYNC", "false").lower() == "true",
        enable_progress_logging=os.getenv(f"{prefix}PROGRESS_LOG", "true").lower() == "true",
        enable_error_recovery=os.getenv(f"{prefix}ERROR_RECOVERY", "true").lower() == "true",
        concurrent_sync_enabled=os.getenv(f"{prefix}CONCURRENT", "false").lower() == "true",
        enable_metrics=os.getenv(f"{prefix}METRICS", "true").lower() == "true",
        enable_detailed_logging=os.getenv(f"{prefix}DETAILED_LOG", "false").lower() == "true",
        log_retention_days=int(os.getenv(f"{prefix}LOG_RETENTION", "30")),
    )


# Predefined configurations for different environments
TESTING_EMAG_CONFIG = EmagApiConfig(
    environment=EmagApiEnvironment.SANDBOX,
    api_username="test_user",
    api_password="test_pass",
    max_pages_per_sync=5,
    delay_between_requests=5.0,
    rate_limits=EmagRateLimitConfig(
        orders_rps=1,
        other_rps=1,
        orders_rpm=60,
        other_rpm=60,
    ),
    enable_progress_logging=True,
    enable_detailed_logging=True,
    concurrent_sync_enabled=False,
)

DEVELOPMENT_EMAG_CONFIG = EmagApiConfig(
    environment=EmagApiEnvironment.SANDBOX,
    api_username="dev_user",
    api_password="dev_pass",
    max_pages_per_sync=50,
    delay_between_requests=2.0,
    rate_limits=EmagRateLimitConfig(
        orders_rps=6,
        other_rps=2,
        orders_rpm=360,
        other_rpm=120,
    ),
    enable_progress_logging=True,
    concurrent_sync_enabled=False,
)

PRODUCTION_EMAG_CONFIG = EmagApiConfig(
    environment=EmagApiEnvironment.PRODUCTION,
    api_username="prod_user",
    api_password="prod_pass",
    max_pages_per_sync=100,
    delay_between_requests=1.2,
    rate_limits=EmagRateLimitConfig(
        orders_rps=12,
        other_rps=3,
        orders_rpm=720,
        other_rpm=180,
    ),
    enable_progress_logging=False,
    enable_detailed_logging=False,
    concurrent_sync_enabled=True,
)


def get_config_for_environment(env: str = None) -> EmagApiConfig:
    """Get predefined configuration for environment.
    
    Args:
        env: Environment name ('testing', 'development', 'production')
        
    Returns:
        EmagApiConfig: Predefined configuration for the environment
    """
    env = env or os.getenv("ENVIRONMENT", "development")
    
    if env == "testing":
        return TESTING_EMAG_CONFIG
    elif env == "development":
        return DEVELOPMENT_EMAG_CONFIG
    elif env == "production":
        return PRODUCTION_EMAG_CONFIG
    else:
        return DEVELOPMENT_EMAG_CONFIG  # Default fallback


# Configuration validation helpers
def validate_emag_credentials(config: EmagApiConfig) -> bool:
    """Validate eMAG API credentials.
    
    Args:
        config: eMAG API configuration
        
    Returns:
        bool: True if credentials are valid format
    """
    if not config.api_username or not config.api_password:
        return False
    
    # Basic format validation
    if len(config.api_username) < 3 or len(config.api_password) < 6:
        return False
    
    return True


def get_rate_limit_info(config: EmagApiConfig) -> Dict[str, Any]:
    """Get rate limit information for monitoring.
    
    Args:
        config: eMAG API configuration
        
    Returns:
        Dict with rate limit information
    """
    return {
        "orders_per_second": config.rate_limits.orders_rps,
        "other_per_second": config.rate_limits.other_rps,
        "orders_per_minute": config.rate_limits.orders_rpm,
        "other_per_minute": config.rate_limits.other_rpm,
        "bulk_max_entities": config.rate_limits.bulk_max_entities,
        "delay_between_requests": config.delay_between_requests,
        "max_pages_per_sync": config.max_pages_per_sync,
    }
