#!/usr/bin/env python3
"""
Advanced Product Validation and Ownership Management System
Based on eMAG API v4.4.8 specifications with comprehensive validation
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    """Product validation statuses from API"""
    DRAFT = 0
    MKTP_APPROVED = 1
    BRAND_APPROVED = 2
    EAN_WAITING = 3
    DOC_PENDING = 4
    BRAND_REJECTED = 5
    EAN_REJECTED = 6
    UPDATE_AWAITING = 11
    UPDATE_REJECTED = 12
    APPROVED = 9
    BLOCKED = 10

class OwnershipStatus(Enum):
    """Product ownership status"""
    ELIGIBLE_FOR_UPDATES = 1
    NOT_ELIGIBLE_FOR_UPDATES = 2
    PENDING_REVIEW = 3

class ProductCategory:
    """Product category information"""
    def __init__(self, category_data: dict[str, Any]):
        self.id = category_data.get('id')
        self.name = category_data.get('name', '')
        self.characteristics = category_data.get('characteristics', [])
        self.family_types = category_data.get('family_types', [])
        self.is_active = category_data.get('is_active', True)

@dataclass
class ProductValidationResult:
    """Result of product validation"""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    validation_details: dict[str, Any] = field(default_factory=dict)

@dataclass
class ProductOwnershipInfo:
    """Product ownership and permissions"""
    ownership_status: OwnershipStatus
    can_update_content: bool
    can_update_images: bool
    can_update_characteristics: bool
    restrictions: list[str] = field(default_factory=list)

class AdvancedProductValidator:
    """Advanced product validation system"""

    def __init__(self):
        self._category_cache: dict[int, ProductCategory] = {}
        self._vat_rates_cache: dict[int, dict] = {}
        self._handling_times_cache: list[dict] = []

        # Validation rules based on API documentation
        self._validation_rules = {
            'name': {
                'required': True,
                'min_length': 1,
                'max_length': 255,
                'pattern': r'^.{1,255}$'
            },
            'part_number': {
                'required': True,
                'min_length': 1,
                'max_length': 25,
                'cleanup_pattern': r'[,";]',
                'pattern': r'^.{1,25}$'
            },
            'description': {
                'required': False,
                'max_length': 16777215,  # ~16MB
                'allowed_html': True
            },
            'ean': {
                'required': False,  # Depends on category
                'length': [6, 8, 12, 13, 14],
                'numeric_only': True,
                'mutually_exclusive': ['part_number_key']
            },
            'part_number_key': {
                'required': False,
                'alphanumeric': True,
                'mutually_exclusive': ['ean']
            },
            'sale_price': {
                'required': True,
                'min_value': 0.01,
                'max_decimals': 4,
                'must_be_positive': True
            },
            'stock': {
                'required': True,
                'min_value': 0,
                'max_value': 999999,
                'integer_only': True
            }
        }

    def validate_product_data(self, product_data: dict[str, Any],
                            category_id: int | None = None) -> ProductValidationResult:
        """Validate complete product data"""
        result = ProductValidationResult(is_valid=True)

        try:
            # Basic field validations
            self._validate_basic_fields(product_data, result)

            # Category-specific validations
            if category_id:
                self._validate_category_requirements(product_data, category_id, result)

            # Business rule validations
            self._validate_business_rules(product_data, result)

            # Content validations
            self._validate_content_quality(product_data, result)

            # Image validations
            self._validate_images(product_data, result)

            # Characteristic validations
            self._validate_characteristics(product_data, result)

            # Price validations
            self._validate_pricing(product_data, result)

            # Stock validations
            self._validate_stock(product_data, result)

        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation error: {str(e)}")

        return result

    def _validate_basic_fields(self, product_data: dict[str, Any], result: ProductValidationResult):
        """Validate basic required fields"""
        required_fields = ['name', 'part_number', 'sale_price', 'stock']

        for field_name in required_fields:
            if field_name not in product_data or product_data[field_name] is None:
                result.errors.append(f"Required field '{field_name}' is missing")
                result.is_valid = False

        # Name validation
        name = product_data.get('name', '')
        if len(name) < 1 or len(name) > 255:
            result.errors.append(
                "Product name must be between 1 and 255 characters "
                f"(current: {len(name)})"
            )
            result.is_valid = False

        # Part number validation with cleanup
        part_number = product_data.get('part_number', '')
        if len(part_number) > 25:
            result.errors.append(
                "Part number must be 25 characters or less "
                f"(current: {len(part_number)})"
            )
            result.is_valid = False

        # Clean part number
        cleaned_part_number = re.sub(r'[,";]', '', part_number)
        if len(cleaned_part_number) != len(part_number):
            result.warnings.append(
                f"Part number cleaned: '{part_number}' → '{cleaned_part_number}'"
            )

    def _validate_category_requirements(self, product_data: dict[str, Any],
                                      category_id: int, result: ProductValidationResult):
        """Validate category-specific requirements"""
        if category_id not in self._category_cache:
            result.warnings.append(
                f"Category {category_id} not in cache - using general validation"
            )
            return

        category = self._category_cache[category_id]

        # Check if EAN is required for this category
        ean_required = self._is_ean_required_for_category(category)
        if ean_required:
            if not product_data.get('ean'):
                result.errors.append(f"EAN is required for category {category_id}")
                result.is_valid = False
        elif product_data.get('ean') and len(product_data['ean']) > 1:
            result.warnings.append(
                "Multiple EANs provided - only first will be used for category matching"
            )

    def _is_ean_required_for_category(self, category: ProductCategory) -> bool:
        """Determine if EAN is required based on category characteristics"""
        # This would be determined by category analysis
        # For now, assume EAN is required for most categories
        return True

    def _validate_business_rules(
        self,
        product_data: dict[str, Any],
        result: ProductValidationResult,
    ) -> None:
        """Validate business rules and constraints"""

        # EAN vs Part Number Key mutual exclusivity
        ean_present = bool(product_data.get('ean'))
        pnk_present = bool(product_data.get('part_number_key'))

        if ean_present and pnk_present:
            result.errors.append(
                "Cannot specify both 'ean' and 'part_number_key' - they are mutually exclusive"
            )
            result.is_valid = False
        elif not ean_present and not pnk_present:
            result.warnings.append(
                "Neither EAN nor Part Number Key provided - product cannot be attached "
                "to existing items"
            )

        # Price range validations
        sale_price = product_data.get('sale_price', 0)
        min_price = product_data.get('min_sale_price', 0)
        max_price = product_data.get('max_sale_price', 0)

        if min_price > 0 and max_price > 0:
            if sale_price < min_price or sale_price > max_price:
                result.errors.append(
                    f"Sale price {sale_price} must be between {min_price} and {max_price}"
                )
                result.is_valid = False

        # Stock validations
        stock = product_data.get('stock', 0)
        if stock < 0:
            result.errors.append("Stock cannot be negative")
            result.is_valid = False

    def _validate_content_quality(
        self,
        product_data: dict[str, Any],
        result: ProductValidationResult,
    ) -> None:
        """Validate content quality and completeness"""

        description = product_data.get('description', '')
        if description:
            # Check for HTML content
            html_tags = re.findall(r'<[^>]+>', description)
            if html_tags:
                result.warnings.append(
                    f"HTML content detected in description: {len(html_tags)} tags"
                )

            # Check description length
            if len(description) > 10000:
                result.warnings.append("Description is very long (>10,000 characters)")

        # Name quality checks
        name = product_data.get('name', '')
        if name.isupper() or name.islower():
            result.warnings.append("Product name should use mixed case")

        if len(name.split()) < 2:
            result.warnings.append("Product name should contain at least 2 words")

    def _validate_images(
        self,
        product_data: dict[str, Any],
        result: ProductValidationResult,
    ) -> None:
        """Validate product images"""

        images = product_data.get('images', [])
        if not images:
            result.warnings.append("No images provided - consider adding product images")
            return

        # Check image count
        if len(images) > 20:
            result.warnings.append(
                "Too many images "
                f"({len(images)}) - consider limiting to 20 or fewer"
            )

        # Validate image URLs
        for i, image in enumerate(images):
            if 'url' not in image:
                result.errors.append(f"Image {i+1} missing URL")
                result.is_valid = False
                continue

            url = image.get('url', '')
            if not self._is_valid_image_url(url):
                result.warnings.append(f"Image {i+1} URL may be invalid: {url}")

            # Check display type
            display_type = image.get('display_type', 0)
            if display_type not in [0, 1, 2]:
                result.warnings.append(f"Image {i+1} has invalid display_type: {display_type}")

    def _is_valid_image_url(self, url: str) -> bool:
        """Validate image URL format"""
        if not url:
            return False

        # Check URL format
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*\.(jpg|jpeg|png|gif|webp)$'
        return bool(re.match(url_pattern, url, re.IGNORECASE))

    def _validate_characteristics(
        self, product_data: dict[str, Any], result: ProductValidationResult
    ):
        """Validate product characteristics"""

        characteristics = product_data.get('characteristics', [])
        if not characteristics:
            result.warnings.append("No characteristics provided")
            return

        for i, char in enumerate(characteristics):
            if 'id' not in char or 'value' not in char:
                result.errors.append(f"Characteristic {i+1} missing id or value")
                result.is_valid = False
                continue

            char_id = char['id']
            char_value = char['value']

            if not isinstance(char_id, int):
                result.errors.append(f"Characteristic {i+1} id must be integer")
                result.is_valid = False

            if len(str(char_value)) > 255:
                result.warnings.append(f"Characteristic {i+1} value is very long (>255 characters)")

            # Check for tags
            if 'tag' in char:
                result.warnings.append(
                    f"Characteristic {i+1} uses tags - ensure multiple entries for different tags"
                )

    def _validate_pricing(self, product_data: dict[str, Any], result: ProductValidationResult):
        """Validate pricing information"""

        sale_price = product_data.get('sale_price', 0)
        recommended_price = product_data.get('recommended_price')

        if sale_price <= 0:
            result.errors.append("Sale price must be greater than 0")
            result.is_valid = False

        # Check decimal places
        sale_price_str = str(sale_price)
        if '.' in sale_price_str:
            decimal_places = len(sale_price_str.split('.')[1])
            if decimal_places > 4:
                result.errors.append(
                    f"Sale price has too many decimal places (max 4): {sale_price}"
                )
                result.is_valid = False

        # Recommended price should be higher than sale price
        if recommended_price and recommended_price <= sale_price:
            result.warnings.append(
                "Recommended price "
                f"({recommended_price}) should be higher than sale price ({sale_price})"
            )

        # Currency validation
        currency = product_data.get('currency')
        if currency and len(currency) != 3:
            result.warnings.append(f"Currency code should be 3 characters: {currency}")

    def _validate_stock(self, product_data: dict[str, Any], result: ProductValidationResult):
        """Validate stock information"""

        stock = product_data.get('stock', 0)

        if not isinstance(stock, int):
            result.errors.append("Stock must be an integer")
            result.is_valid = False

        if stock < 0:
            result.errors.append("Stock cannot be negative")
            result.is_valid = False

        if stock > 999999:
            result.warnings.append(f"Stock is very high ({stock}) - verify this is correct")

        # Validate stock per warehouse if provided
        stock_data = product_data.get('stock_data', [])
        if stock_data:
            for i, stock_item in enumerate(stock_data):
                if 'warehouse_id' not in stock_item or 'value' not in stock_item:
                    result.errors.append(f"Stock item {i+1} missing warehouse_id or value")
                    result.is_valid = False

                if stock_item.get('value', 0) < 0:
                    result.errors.append(
                        f"Stock item {i+1} has negative stock"
                    )
                    result.is_valid = False

    def validate_ownership_and_permissions(
        self,
        product_data: dict[str, Any],
        current_ownership: OwnershipStatus | None = None,
    ) -> ProductOwnershipInfo:
        """Validate product ownership and update permissions"""

        ownership_status = current_ownership or OwnershipStatus.NOT_ELIGIBLE_FOR_UPDATES
        restrictions = []

        # Check if product can be updated
        can_update_content = False
        can_update_images = False
        can_update_characteristics = False

        # Ownership = 1 means eligible for content updates
        if ownership_status == OwnershipStatus.ELIGIBLE_FOR_UPDATES:
            can_update_content = True
            can_update_images = True
            can_update_characteristics = True
        elif ownership_status == OwnershipStatus.NOT_ELIGIBLE_FOR_UPDATES:
            restrictions.append("Not eligible for content updates")
            if product_data.get('description') or product_data.get('images'):
                restrictions.append("Images and descriptions will be rejected")
        elif ownership_status == OwnershipStatus.PENDING_REVIEW:
            restrictions.append("Product is pending review - updates may be delayed")

        # Additional validations based on product status
        validation_status = product_data.get('validation_status')
        if validation_status:
            if validation_status in [5, 6, 10]:  # Brand rejected, EAN rejected, Blocked
                restrictions.append(
                    f"Product has validation status {validation_status} - updates restricted"
                )

        return ProductOwnershipInfo(
            ownership_status=ownership_status,
            can_update_content=can_update_content,
            can_update_images=can_update_images,
            can_update_characteristics=can_update_characteristics,
            restrictions=restrictions
        )

    def validate_gpsr_fields(self, product_data: dict[str, Any]) -> list[str]:
        """Validate GPSR (General Product Safety Regulation) fields"""
        errors = []

        # Manufacturer information
        manufacturer = product_data.get('manufacturer', [])
        if manufacturer:
            for i, mfg in enumerate(manufacturer):
                required_fields = ['name', 'address', 'email']
                for field in required_fields:
                    if field not in mfg or not mfg[field]:
                        errors.append(f"Manufacturer {i+1} missing required field: {field}")

        # EU Representative information
        eu_representative = product_data.get('eu_representative', [])
        if eu_representative:
            for i, rep in enumerate(eu_representative):
                required_fields = ['name', 'address', 'email']
                for field in required_fields:
                    if field not in rep or not rep[field]:
                        errors.append(f"EU Representative {i+1} missing required field: {field}")

        # Safety information
        safety_info = product_data.get('safety_information', '')
        if safety_info and len(safety_info) > 16777215:
            errors.append("Safety information exceeds maximum length")

        # Green tax (eMAG RO only)
        green_tax = product_data.get('green_tax')
        if green_tax is not None:
            if green_tax < 0:
                errors.append("Green tax cannot be negative")
            # Additional validation for green tax format

        return errors

    def generate_validation_report(self, product_data: dict[str, Any],
                                 category_id: int | None = None) -> dict[str, Any]:
        """Generate comprehensive validation report"""

        validation_result = self.validate_product_data(product_data, category_id)
        ownership_info = self.validate_ownership_and_permissions(product_data)
        gpsr_errors = self.validate_gpsr_fields(product_data)

        return {
            'validation_result': {
                'is_valid': validation_result.is_valid,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings,
                'recommendations': validation_result.recommendations
            },
            'ownership_info': {
                'status': ownership_info.ownership_status.value,
                'can_update_content': ownership_info.can_update_content,
                'can_update_images': ownership_info.can_update_images,
                'can_update_characteristics': ownership_info.can_update_characteristics,
                'restrictions': ownership_info.restrictions
            },
            'gpsr_validation': {
                'errors': gpsr_errors,
                'compliant': len(gpsr_errors) == 0
            },
            'validation_details': validation_result.validation_details,
            'timestamp': datetime.utcnow().isoformat()
        }

# Factory function for easy usage
def get_product_validator() -> AdvancedProductValidator:
    """Get or create product validator instance"""
    return AdvancedProductValidator()

# Export for easy usage
__all__ = [
    'AdvancedProductValidator',
    'ProductValidationResult',
    'ProductOwnershipInfo',
    'OwnershipStatus',
    'ValidationStatus',
    'ProductCategory',
    'get_product_validator'
]
