"""
eMAG Advanced Validation Service - v4.4.9

Provides comprehensive pre-publication validation for products according to
eMAG API Section 8 specifications. Validates images, characteristics, EAN codes,
and other required fields before sending to eMAG API.
"""

import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class EmagValidationService:
    """
    Advanced validation service for eMAG products.

    Validates all product data according to eMAG API v4.4.9 specifications
    before publication to prevent API errors and rejections.
    """

    # EAN validation patterns
    EAN_PATTERN = re.compile(r"^\d{6,14}$")

    # Image validation constants
    MAX_IMAGE_SIZE_MB = 8
    MAX_IMAGE_DIMENSION = 6000
    ALLOWED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png"]

    # Field length constraints
    MAX_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 16777215
    MAX_BRAND_LENGTH = 255
    MAX_PART_NUMBER_LENGTH = 25
    MAX_URL_LENGTH = 1024

    # Price constraints
    MIN_PRICE = 0.01
    MAX_PRICE = 999999.99

    def __init__(self):
        """Initialize validation service."""
        logger.info("Initialized EmagValidationService")
        self._validation_cache = {}

    def validate_product_complete(
        self,
        product_data: dict[str, Any],
        category_template: dict[str, Any] | None = None,
    ) -> tuple[bool, list[str], list[str]]:
        """
        Complete product validation before publication.

        Args:
            product_data: Product data dictionary
            category_template: Optional category template with requirements

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Validate required fields
        required_errors = self._validate_required_fields(product_data)
        errors.extend(required_errors)

        # Validate images
        image_valid, image_errors, image_warnings = self.validate_images(
            product_data.get("images", [])
        )
        errors.extend(image_errors)
        warnings.extend(image_warnings)

        # Validate EAN codes
        ean_valid, ean_errors = self.validate_ean_codes(product_data.get("ean", []))
        errors.extend(ean_errors)

        # Validate characteristics
        if category_template:
            char_valid, char_errors, char_warnings = self.validate_characteristics(
                product_data.get("characteristics", []), category_template
            )
            errors.extend(char_errors)
            warnings.extend(char_warnings)

        # Validate pricing
        price_valid, price_errors = self.validate_pricing(product_data)
        errors.extend(price_errors)

        # Validate measurements if present
        if any(k in product_data for k in ["length", "width", "height", "weight"]):
            meas_valid, meas_errors = self.validate_measurements(product_data)
            errors.extend(meas_errors)

        # Validate field lengths
        length_errors = self._validate_field_lengths(product_data)
        errors.extend(length_errors)

        is_valid = len(errors) == 0

        logger.info(
            "Product validation complete: valid=%s, errors=%d, warnings=%d",
            is_valid,
            len(errors),
            len(warnings),
        )

        return is_valid, errors, warnings

    def validate_images(
        self, images: list[dict[str, Any]]
    ) -> tuple[bool, list[str], list[str]]:
        """
        Validate product images according to eMAG specifications.

        Rules:
        - Exactly one image with display_type=1 (main)
        - Valid URLs
        - Supported formats (JPG, JPEG, PNG)
        - Max dimensions: 6000x6000 px
        - Max size: 8 MB

        Args:
            images: List of image dictionaries

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        if not images or len(images) == 0:
            errors.append("No images provided. At least one main image is required.")
            return False, errors, warnings

        # Check for main image
        main_images = [img for img in images if img.get("display_type") == 1]

        if len(main_images) == 0:
            errors.append(
                "No main image (display_type=1) found. Exactly one main image is required."
            )
        elif len(main_images) > 1:
            errors.append(
                f"Multiple main images found ({len(main_images)}). Only one main image is allowed."
            )

        # Validate each image
        for idx, img in enumerate(images):
            url = img.get("url", "")
            display_type = img.get("display_type")

            # Validate URL
            if not url:
                errors.append(f"Image {idx + 1}: Missing URL")
                continue

            if not url.startswith(("http://", "https://")):
                errors.append(
                    f"Image {idx + 1}: Invalid URL format. Must start with http:// or https://"
                )

            # Validate format
            url_lower = url.lower()
            if not any(url_lower.endswith(fmt) for fmt in self.ALLOWED_IMAGE_FORMATS):
                errors.append(
                    f"Image {idx + 1}: Unsupported format. "
                    f"Allowed formats: {', '.join(self.ALLOWED_IMAGE_FORMATS)}"
                )

            # Validate display_type
            if display_type not in [0, 1, 2]:
                warnings.append(
                    f"Image {idx + 1}: Invalid display_type={display_type}. "
                    f"Should be 0 (other), 1 (main), or 2 (secondary)"
                )

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def validate_ean_codes(self, ean_codes: list[str]) -> tuple[bool, list[str]]:
        """
        Validate EAN codes format and checksum.

        Supported formats:
        - EAN-8 (8 digits)
        - EAN-13 (13 digits)
        - UPC-A (12 digits)
        - GTIN-14 (14 digits)
        - ISBN-10, ISBN-13, ISSN, ISMN

        Args:
            ean_codes: List of EAN code strings

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        if not ean_codes or len(ean_codes) == 0:
            # EAN is optional for some categories
            return True, []

        for ean in ean_codes:
            ean_clean = str(ean).strip().replace(" ", "").replace("-", "")

            # Check format
            if not self.EAN_PATTERN.match(ean_clean):
                errors.append(
                    f"Invalid EAN format: '{ean}'. Must be 6-14 numeric characters."
                )
                continue

            # Validate EAN-13 checksum
            if len(ean_clean) == 13:
                if not self._validate_ean13_checksum(ean_clean):
                    errors.append(
                        f"Invalid EAN-13 checksum: '{ean}'. "
                        f"Please verify the code is correct."
                    )

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_characteristics(
        self, characteristics: list[dict[str, Any]], category_template: dict[str, Any]
    ) -> tuple[bool, list[str], list[str]]:
        """
        Validate product characteristics against category template.

        Args:
            characteristics: List of characteristic dictionaries
            category_template: Category template with requirements

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        template_chars = category_template.get("characteristics", [])

        # Build lookup for template characteristics
        template_lookup = {char["id"]: char for char in template_chars}

        # Check mandatory characteristics
        provided_ids = {char.get("id") for char in characteristics if char.get("id")}

        for template_char in template_chars:
            char_id = template_char.get("id")
            is_mandatory = template_char.get("is_mandatory", 0) == 1

            if is_mandatory and char_id not in provided_ids:
                errors.append(
                    f"Missing mandatory characteristic: "
                    f"{template_char.get('name', f'ID {char_id}')}"
                )

        # Validate each provided characteristic
        for char in characteristics:
            char_id = char.get("id")
            char_value = char.get("value")
            char_tag = char.get("tag")

            if not char_id:
                errors.append("Characteristic missing 'id' field")
                continue

            if not char_value:
                errors.append(f"Characteristic {char_id} missing 'value' field")
                continue

            # Check if characteristic exists in template
            template_char = template_lookup.get(char_id)
            if not template_char:
                warnings.append(
                    f"Characteristic {char_id} not found in category template. "
                    f"May be rejected by eMAG."
                )
                continue

            # Validate tags if required
            tags = template_char.get("tags", [])
            if tags and not char_tag:
                warnings.append(
                    f"Characteristic '{template_char.get('name')}' requires a tag. "
                    f"Available tags: {', '.join(tags)}"
                )

            # Validate value format based on type_id
            type_id = template_char.get("type_id")
            if type_id:
                format_valid, format_error = self._validate_characteristic_format(
                    char_value, type_id, template_char.get("name", f"ID {char_id}")
                )
                if not format_valid:
                    errors.append(format_error)

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def validate_pricing(self, product_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate product pricing.

        Args:
            product_data: Product data dictionary

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        sale_price = product_data.get("sale_price")
        min_sale_price = product_data.get("min_sale_price")
        max_sale_price = product_data.get("max_sale_price")
        recommended_price = product_data.get("recommended_price")

        # Validate sale_price
        if sale_price is None:
            errors.append("Missing required field: sale_price")
        else:
            try:
                price = float(sale_price)
                if price < self.MIN_PRICE or price > self.MAX_PRICE:
                    errors.append(
                        f"sale_price must be between {self.MIN_PRICE} and {self.MAX_PRICE}, "
                        f"got {price}"
                    )
            except (ValueError, TypeError):
                errors.append(f"Invalid sale_price format: {sale_price}")

        # Validate price ranges
        if sale_price and min_sale_price and max_sale_price:
            try:
                sp = float(sale_price)
                min_p = float(min_sale_price)
                max_p = float(max_sale_price)

                if min_p > max_p:
                    errors.append(
                        f"min_sale_price ({min_p}) cannot be greater than "
                        f"max_sale_price ({max_p})"
                    )

                if sp < min_p or sp > max_p:
                    errors.append(
                        f"sale_price ({sp}) must be between min_sale_price ({min_p}) "
                        f"and max_sale_price ({max_p})"
                    )
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid price format: {str(e)}")

        # Validate recommended_price
        if recommended_price and sale_price:
            try:
                rec_p = float(recommended_price)
                sp = float(sale_price)

                if rec_p <= sp:
                    errors.append(
                        f"recommended_price ({rec_p}) must be greater than "
                        f"sale_price ({sp}) to display as promotion"
                    )
            except (ValueError, TypeError):
                pass

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_measurements(
        self, product_data: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate product measurements (volumetry).

        Args:
            product_data: Product data dictionary

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        measurements = {
            "length": product_data.get("length"),
            "width": product_data.get("width"),
            "height": product_data.get("height"),
            "weight": product_data.get("weight"),
        }

        for field, value in measurements.items():
            if value is None:
                continue

            try:
                val = float(value)

                # Check range
                if val < 0 or val > 999999:
                    errors.append(f"{field} must be between 0 and 999,999, got {val}")

                # Check decimal places
                decimal_str = str(value)
                if "." in decimal_str:
                    decimal_places = len(decimal_str.split(".")[1])
                    if decimal_places > 2:
                        errors.append(
                            f"{field} can have maximum 2 decimal places, "
                            f"got {decimal_places}"
                        )
            except (ValueError, TypeError):
                errors.append(f"Invalid {field} format: {value}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def _validate_required_fields(self, product_data: dict[str, Any]) -> list[str]:
        """Validate required fields are present."""
        errors = []

        required_fields = {
            "name": "Product name",
            "brand": "Brand",
            "part_number": "Part number (SKU)",
            "category_id": "Category ID",
        }

        for field, label in required_fields.items():
            if not product_data.get(field):
                errors.append(f"Missing required field: {label}")

        return errors

    def _validate_field_lengths(self, product_data: dict[str, Any]) -> list[str]:
        """Validate field length constraints."""
        errors = []

        length_checks = {
            "name": (self.MAX_NAME_LENGTH, "Product name"),
            "brand": (self.MAX_BRAND_LENGTH, "Brand"),
            "part_number": (self.MAX_PART_NUMBER_LENGTH, "Part number"),
            "description": (self.MAX_DESCRIPTION_LENGTH, "Description"),
            "url": (self.MAX_URL_LENGTH, "URL"),
        }

        for field, (max_length, label) in length_checks.items():
            value = product_data.get(field)
            if value and len(str(value)) > max_length:
                errors.append(
                    f"{label} exceeds maximum length of {max_length} characters "
                    f"(current: {len(str(value))})"
                )

        return errors

    def _validate_ean13_checksum(self, ean: str) -> bool:
        """Validate EAN-13 checksum digit."""
        if len(ean) != 13:
            return True  # Only validate EAN-13

        try:
            # Calculate checksum
            odd_sum = sum(int(ean[i]) for i in range(0, 12, 2))
            even_sum = sum(int(ean[i]) for i in range(1, 12, 2))
            total = odd_sum + (even_sum * 3)
            checksum = (10 - (total % 10)) % 10

            return checksum == int(ean[12])
        except (ValueError, IndexError):
            return False

    def _validate_characteristic_format(
        self, value: str, type_id: int, char_name: str
    ) -> tuple[bool, str | None]:
        """
        Validate characteristic value format based on type_id.

        Type IDs:
        - 1: Numeric (e.g., 20, 1, 30)
        - 2: Numeric + unit (e.g., 30 cm, 20 GB)
        - 11: Text Fixed (≤255 chars)
        - 20: Boolean (Yes/No/N/A)
        - 30: Resolution (Width x Height)
        - 40: Volume (W x H x D - D2)
        - 60: Size (e.g., 36 EU, XL INTL)
        """
        value_str = str(value).strip()

        if type_id == 1:  # Numeric
            try:
                float(value_str)
                return True, None
            except ValueError:
                return False, f"{char_name}: Must be numeric, got '{value}'"

        elif type_id == 2:  # Numeric + unit
            # Pattern: number + space + unit
            if not re.match(r"^\d+(\.\d+)?\s+\w+$", value_str):
                return (
                    False,
                    f"{char_name}: Must be 'number unit' format (e.g., '30 cm'), "
                    f"got '{value}'",
                )

        elif type_id == 11:  # Text Fixed
            if len(value_str) > 255:
                return False, f"{char_name}: Text exceeds 255 characters"

        elif type_id == 20:  # Boolean
            valid_values = ["yes", "no", "n/a", "da", "nu"]
            if value_str.lower() not in valid_values:
                return False, f"{char_name}: Must be Yes/No/N/A, got '{value}'"

        elif type_id == 30:  # Resolution
            if not re.match(r"^\d+\s*x\s*\d+$", value_str, re.IGNORECASE):
                return (
                    False,
                    f"{char_name}: Must be 'Width x Height' format (e.g., '1920 x 1080'), "
                    f"got '{value}'",
                )

        elif type_id == 40:  # Volume
            if not re.match(
                r"^\d+\s*x\s*\d+\s*x\s*\d+(\s*-\s*\d+)?$", value_str, re.IGNORECASE
            ):
                return (
                    False,
                    f"{char_name}: Must be 'W x H x D' or 'W x H x D - D2' format, "
                    f"got '{value}'",
                )

        elif type_id == 60:  # Size
            # Size can be various formats (36 EU, XL INTL, etc.)
            if len(value_str) > 50:
                return False, f"{char_name}: Size value too long"

        return True, None

    def get_validation_summary(
        self, errors: list[str], warnings: list[str]
    ) -> dict[str, Any]:
        """
        Get formatted validation summary.

        Args:
            errors: List of error messages
            warnings: List of warning messages

        Returns:
            Dictionary with validation summary
        """
        return {
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "severity": "error" if errors else ("warning" if warnings else "success"),
        }
