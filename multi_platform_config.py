#!/usr/bin/env python3
"""
Multi-Platform eMAG/FD Marketplace Configuration
Supports: eMAG RO/BG/HU, Fashion Days RO/BG
Enhanced configuration with platform-specific settings and validation
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PlatformType(Enum):
    """Supported marketplace platforms"""
    EMAG_RO = "emag_ro"
    EMAG_BG = "emag_bg"
    EMAG_HU = "emag_hu"
    FD_RO = "fd_ro"
    FD_BG = "fd_bg"

class AccountType(Enum):
    """Account types for authentication"""
    MAIN = "main"
    FBE = "fbe"
    SANDBOX = "sandbox"

@dataclass
class PlatformConfig:
    """Platform-specific configuration"""
    platform: PlatformType
    api_base_url: str
    marketplace_url: str
    currency: str
    language: str
    country_code: str
    rate_limits: Dict[str, int]
    features: List[str] = field(default_factory=list)
    special_rules: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "platform": self.platform.value,
            "api_base_url": self.api_base_url,
            "marketplace_url": self.marketplace_url,
            "currency": self.currency,
            "language": self.language,
            "country_code": self.country_code,
            "rate_limits": self.rate_limits,
            "features": self.features,
            "special_rules": self.special_rules
        }

class MultiPlatformConfigManager:
    """Manager for multi-platform eMAG/FD configurations"""

    # Platform configurations based on API documentation
    PLATFORM_CONFIGS = {
        PlatformType.EMAG_RO: PlatformConfig(
            platform=PlatformType.EMAG_RO,
            api_base_url="https://marketplace-api.emag.ro/api-3",
            marketplace_url="https://marketplace.emag.ro",
            currency="RON",
            language="ro_RO",
            country_code="RO",
            rate_limits={
                "orders": 12,  # requests per second
                "offers": 3,
                "other": 3
            },
            features=[
                "green_tax",
                "gpsr_fields",
                "smart_deals",
                "campaigns",
                "multi_deals"
            ],
            special_rules={
                "max_input_vars": 4000,
                "bulk_save_limit": 50,
                "start_date_min_days": 1,
                "start_date_max_days": 60
            }
        ),
        PlatformType.EMAG_BG: PlatformConfig(
            platform=PlatformType.EMAG_BG,
            api_base_url="https://marketplace-api.emag.bg/api-3",
            marketplace_url="https://marketplace.emag.bg",
            currency="BGN",
            language="bg_BG",
            country_code="BG",
            rate_limits={
                "orders": 12,
                "offers": 3,
                "other": 3
            },
            features=[
                "gpsr_fields",
                "campaigns"
            ],
            special_rules={
                "max_input_vars": 4000,
                "bulk_save_limit": 50,
                "start_date_min_days": 1,
                "start_date_max_days": 60
            }
        ),
        PlatformType.EMAG_HU: PlatformConfig(
            platform=PlatformType.EMAG_HU,
            api_base_url="https://marketplace-api.emag.hu/api-3",
            marketplace_url="https://marketplace.emag.hu",
            currency="HUF",
            language="hu_HU",
            country_code="HU",
            rate_limits={
                "orders": 12,
                "offers": 3,
                "other": 3
            },
            features=[
                "gpsr_fields",
                "campaigns"
            ],
            special_rules={
                "max_input_vars": 4000,
                "bulk_save_limit": 50,
                "start_date_min_days": 1,
                "start_date_max_days": 60
            }
        ),
        PlatformType.FD_RO: PlatformConfig(
            platform=PlatformType.FD_RO,
            api_base_url="https://marketplace-ro-api.fashiondays.com/api-3",
            marketplace_url="https://marketplace-ro.fashiondays.com",
            currency="RON",
            language="ro_RO",
            country_code="RO",
            rate_limits={
                "orders": 12,
                "offers": 3,
                "other": 3
            },
            features=[
                "campaigns",
                "fashion_days_specific"
            ],
            special_rules={
                "max_input_vars": 4000,
                "bulk_save_limit": 50,
                "order_types": [2],  # FBE only
                "start_date_min_days": 1,
                "start_date_max_days": 60
            }
        ),
        PlatformType.FD_BG: PlatformConfig(
            platform=PlatformType.FD_BG,
            api_base_url="https://marketplace-bg-api.fashiondays.com/api-3",
            marketplace_url="https://marketplace-bg.fashiondays.com",
            currency="BGN",
            language="bg_BG",
            country_code="BG",
            rate_limits={
                "orders": 12,
                "offers": 3,
                "other": 3
            },
            features=[
                "campaigns",
                "fashion_days_specific"
            ],
            special_rules={
                "max_input_vars": 4000,
                "bulk_save_limit": 50,
                "order_types": [2],  # FBE only
                "start_date_min_days": 1,
                "start_date_max_days": 60
            }
        )
    }

    def __init__(self):
        self.current_platform: Optional[PlatformType] = None
        self.active_account: Optional[AccountType] = None
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from environment variables"""
        # Determine current platform
        platform_str = os.getenv('EMAG_PLATFORM', 'emag_ro').lower()
        try:
            self.current_platform = PlatformType(platform_str)
        except ValueError:
            logger.warning(f"Invalid platform '{platform_str}', defaulting to eMAG RO")
            self.current_platform = PlatformType.EMAG_RO

        # Determine account type
        account_str = os.getenv('EMAG_ACCOUNT_TYPE', 'main').lower()
        try:
            self.active_account = AccountType(account_str)
        except ValueError:
            logger.warning(f"Invalid account type '{account_str}', defaulting to MAIN")
            self.active_account = AccountType.MAIN

        logger.info(f"Initialized multi-platform config: {self.current_platform.value} ({self.active_account.value})")

    def get_current_platform_config(self) -> PlatformConfig:
        """Get configuration for current platform"""
        return self.PLATFORM_CONFIGS[self.current_platform]

    def get_platform_config(self, platform: PlatformType) -> PlatformConfig:
        """Get configuration for specific platform"""
        return self.PLATFORM_CONFIGS[platform]

    def get_api_credentials(self) -> Dict[str, str]:
        """Get API credentials for current platform and account"""
        platform_config = self.get_current_platform_config()

        # Build credential environment variable names
        platform_prefix = self.current_platform.value.upper()
        account_suffix = f"_{self.active_account.value.upper()}"

        credentials = {}

        # Username
        username_key = f"{platform_prefix}_USER"
        username = os.getenv(username_key)
        if username:
            credentials['username'] = username
        else:
            logger.error(f"Missing credential: {username_key}")

        # Password
        password_key = f"{platform_prefix}_PASS"
        password = os.getenv(password_key)
        if password:
            credentials['password'] = password
        else:
            logger.error(f"Missing credential: {password_key}")

        # Additional platform-specific credentials
        if self.current_platform in [PlatformType.FD_RO, PlatformType.FD_BG]:
            credentials['platform'] = 'fashion_days'
        else:
            credentials['platform'] = 'emag'

        credentials['api_base_url'] = platform_config.api_base_url
        credentials['marketplace_url'] = platform_config.marketplace_url

        return credentials

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration"""
        validation_results = {
            'platform': self.current_platform.value,
            'account': self.active_account.value,
            'valid': True,
            'issues': []
        }

        # Check platform configuration
        platform_config = self.get_current_platform_config()
        if not platform_config:
            validation_results['valid'] = False
            validation_results['issues'].append(f"Invalid platform: {self.current_platform}")
            return validation_results

        # Check credentials
        credentials = self.get_api_credentials()
        if 'username' not in credentials or 'password' not in credentials:
            validation_results['valid'] = False
            validation_results['issues'].append("Missing API credentials")
            return validation_results

        # Platform-specific validations
        if self.current_platform in [PlatformType.FD_RO, PlatformType.FD_BG]:
            if self.active_account != AccountType.FBE:
                validation_results['issues'].append("Fashion Days requires FBE account type")

        validation_results['rate_limits'] = platform_config.rate_limits
        validation_results['features'] = platform_config.features
        validation_results['currency'] = platform_config.currency

        return validation_results

    def get_platform_specific_settings(self) -> Dict[str, Any]:
        """Get platform-specific settings and rules"""
        platform_config = self.get_current_platform_config()

        settings = {
            'api_base_url': platform_config.api_base_url,
            'currency': platform_config.currency,
            'language': platform_config.language,
            'country_code': platform_config.country_code,
            'max_input_vars': platform_config.special_rules.get('max_input_vars', 4000),
            'bulk_save_limit': platform_config.special_rules.get('bulk_save_limit', 50),
            'start_date_min_days': platform_config.special_rules.get('start_date_min_days', 1),
            'start_date_max_days': platform_config.special_rules.get('start_date_max_days', 60),
        }

        # Add platform-specific features
        if 'green_tax' in platform_config.features:
            settings['green_tax_enabled'] = True
        else:
            settings['green_tax_enabled'] = False

        if 'smart_deals' in platform_config.features:
            settings['smart_deals_enabled'] = True
        else:
            settings['smart_deals_enabled'] = False

        return settings

    def switch_platform(self, platform: PlatformType, account: AccountType = None):
        """Switch to different platform"""
        if platform not in self.PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        self.current_platform = platform

        if account:
            self.active_account = account

        logger.info(f"Switched to platform: {self.current_platform.value} ({self.active_account.value})")

    def get_available_platforms(self) -> List[Dict[str, Any]]:
        """Get list of available platforms with their configurations"""
        return [
            {
                'platform': platform.value,
                'name': platform_config.api_base_url.split('.')[0].replace('https://marketplace-api.', '').upper(),
                'currency': platform_config.currency,
                'language': platform_config.language,
                'features': platform_config.features
            }
            for platform, platform_config in self.PLATFORM_CONFIGS.items()
        ]

    def get_rate_limits(self) -> Dict[str, int]:
        """Get rate limits for current platform"""
        return self.get_current_platform_config().rate_limits

    def supports_feature(self, feature: str) -> bool:
        """Check if current platform supports a specific feature"""
        platform_config = self.get_current_platform_config()
        return feature in platform_config.features

    def get_platform_info(self) -> Dict[str, Any]:
        """Get comprehensive platform information"""
        platform_config = self.get_current_platform_config()

        return {
            'platform': self.current_platform.value,
            'account': self.active_account.value,
            'api_url': platform_config.api_base_url,
            'marketplace_url': platform_config.marketplace_url,
            'currency': platform_config.currency,
            'language': platform_config.language,
            'country_code': platform_config.country_code,
            'rate_limits': platform_config.rate_limits,
            'features': platform_config.features,
            'special_rules': platform_config.special_rules
        }

# Global configuration manager instance
_config_manager = None

def get_platform_config_manager() -> MultiPlatformConfigManager:
    """Get or create platform configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MultiPlatformConfigManager()
    return _config_manager

def initialize_platform_config():
    """Initialize and validate platform configuration"""
    config_manager = get_platform_config_manager()
    validation = config_manager.validate_configuration()

    if not validation['valid']:
        logger.error("Platform configuration validation failed:")
        for issue in validation['issues']:
            logger.error(f"  - {issue}")
        raise ValueError("Invalid platform configuration")

    logger.info(f"Platform configuration initialized: {validation['platform']} ({validation['account']})")
    return validation

# Export functions for easy usage
__all__ = [
    'PlatformType',
    'AccountType',
    'PlatformConfig',
    'MultiPlatformConfigManager',
    'get_platform_config_manager',
    'initialize_platform_config'
]
