"""Data transformation service for converting between eMAG and internal data formats."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.integrations.emag.models.responses.offer import ProductOfferResponse

logger = logging.getLogger(__name__)


class DataTransformationService:
    """Service for transforming data between eMAG and internal formats."""

    def __init__(self):
        """Initialize the data transformation service."""
        # Field mapping configuration
        self.field_mappings = {
            # Product fields
            "name": "name",
            "description": "description",
            "part_number": "part_number",
            "category_id": "emag_category_id",
            "brand_id": "emag_brand_id",
            "category_name": "emag_category_name",
            "brand_name": "emag_brand_name",
            # Offer fields
            "price": "price",
            "sale_price": "sale_price",
            "stock": "stock",
            "stock_status": "stock_status",
            "handling_time": "handling_time",
            "status": "status",
            "is_available": "is_available",
            "is_visible": "is_visible",
            "vat_rate": "vat_rate",
            "vat_included": "vat_included",
            "warehouse_id": "warehouse_id",
            "warehouse_name": "warehouse_name",
            "warranty": "warranty",
        }

        # Data type conversions
        self.type_conversions = {
            "price": float,
            "sale_price": lambda x: float(x) if x else None,
            "stock": int,
            "handling_time": lambda x: int(x) if x else None,
            "vat_rate": lambda x: float(x) if x else None,
            "warranty": lambda x: int(x) if x else None,
            "is_available": bool,
            "is_visible": bool,
            "vat_included": bool,
        }

    def transform_emag_offer_to_internal(
        self,
        emag_offer: ProductOfferResponse,
        account_type: str = "main",
    ) -> dict[str, Any]:
        """Transform an eMAG offer response to internal format.

        Args:
            emag_offer: eMAG offer response
            account_type: Account type ('main' or 'fbe')

        Returns:
            Dictionary with transformed offer data

        """
        transformed = {
            "emag_product_id": emag_offer.product_id,
            "emag_offer_id": emag_offer.emag_id,
            "account_type": account_type,
            "last_imported_at": datetime.now(UTC),
            "raw_data": getattr(emag_offer, "raw_data", None),
        }

        # Apply field mappings and type conversions
        for internal_field, emag_field in self.field_mappings.items():
            if hasattr(emag_offer, emag_field):
                value = getattr(emag_offer, emag_field)

                # Apply type conversion if specified
                if internal_field in self.type_conversions:
                    try:
                        converter = self.type_conversions[internal_field]
                        value = converter(value)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Failed to convert {internal_field}: {value} - {e!s}",
                        )
                        value = None

                transformed[internal_field] = value

        # Handle special fields
        transformed["currency"] = getattr(emag_offer, "currency", "RON")

        # Handle timestamps
        if hasattr(emag_offer, "updated_at") and emag_offer.updated_at:
            transformed["emag_updated_at"] = emag_offer.updated_at
        else:
            transformed["emag_updated_at"] = datetime.now(UTC)

        return transformed

    def transform_emag_product_to_internal(
        self,
        emag_product_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Transform eMAG product data to internal format.

        Args:
            emag_product_data: eMAG product data dictionary

        Returns:
            Dictionary with transformed product data

        """
        transformed = {
            "emag_id": emag_product_data.get("id"),
            "last_imported_at": datetime.now(UTC),
            "is_active": emag_product_data.get("is_active", True),
            "raw_data": emag_product_data,
        }

        # Apply field mappings
        for internal_field, emag_field in self.field_mappings.items():
            if emag_field in emag_product_data:
                value = emag_product_data[emag_field]

                # Apply type conversion if specified
                if internal_field in self.type_conversions:
                    try:
                        converter = self.type_conversions[internal_field]
                        value = converter(value)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Failed to convert {internal_field}: {value} - {e!s}",
                        )
                        value = None

                transformed[internal_field] = value

        # Handle special product fields
        if "characteristics" in emag_product_data:
            transformed["characteristics"] = emag_product_data["characteristics"]

        if "images" in emag_product_data:
            transformed["images"] = emag_product_data["images"]

        # Handle timestamps
        if emag_product_data.get("updated_at"):
            transformed["emag_updated_at"] = emag_product_data["updated_at"]
        else:
            transformed["emag_updated_at"] = datetime.now(UTC)

        return transformed

    def create_emag_product_from_offer(
        self,
        offer_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create minimal eMAG product data from offer data.

        Args:
            offer_data: Offer data dictionary

        Returns:
            Dictionary with minimal product data

        """
        return {
            "emag_id": offer_data.get("emag_product_id"),
            "name": f"Product {offer_data.get('emag_product_id', 'Unknown')}",
            "description": None,
            "part_number": None,
            "emag_category_id": None,
            "emag_brand_id": None,
            "emag_category_name": None,
            "emag_brand_name": None,
            "characteristics": {},
            "images": [],
            "is_active": True,
            "last_imported_at": datetime.now(UTC),
            "emag_updated_at": datetime.now(UTC),
            "raw_data": None,
        }

    def merge_offer_data(
        self,
        existing_offer: dict[str, Any],
        new_offer: dict[str, Any],
        strategy: str = "update",
    ) -> dict[str, Any]:
        """Merge existing offer data with new offer data.

        Args:
            existing_offer: Existing offer data
            new_offer: New offer data from eMAG
            strategy: Merge strategy ('update', 'merge', 'keep_existing')

        Returns:
            Merged offer data

        """
        if strategy == "keep_existing":
            return existing_offer

        merged = existing_offer.copy()

        if strategy == "update":
            # Replace all fields with new data
            merged.update(new_offer)

        elif strategy == "merge":
            # Merge fields, preferring new data but keeping existing non-null values
            for key, new_value in new_offer.items():
                if key not in merged or merged[key] is None:
                    merged[key] = new_value
                elif new_value is not None:
                    # For some fields, we might want to choose based on recency
                    if key in ["price", "stock", "status"]:
                        merged[key] = new_value

        # Always update import metadata
        merged["last_imported_at"] = datetime.now(UTC)
        if "emag_updated_at" in new_offer:
            merged["emag_updated_at"] = new_offer["emag_updated_at"]
        if "raw_data" in new_offer:
            merged["raw_data"] = new_offer["raw_data"]

        return merged

    def detect_data_conflicts(
        self,
        existing_offer: dict[str, Any],
        new_offer: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Detect conflicts between existing and new offer data.

        Args:
            existing_offer: Existing offer data
            new_offer: New offer data

        Returns:
            List of detected conflicts

        """
        conflicts = []

        # Check for price discrepancies
        if (
            "price" in existing_offer
            and "price" in new_offer
            and existing_offer["price"] != new_offer["price"]
            and existing_offer["price"] is not None
            and new_offer["price"] is not None
        ):
            price_diff = abs(existing_offer["price"] - new_offer["price"])
            price_diff_percent = (
                (price_diff / existing_offer["price"]) * 100
                if existing_offer["price"] != 0
                else 0
            )

            if price_diff_percent > 10:  # More than 10% difference
                conflicts.append(
                    {
                        "type": "price_mismatch",
                        "field": "price",
                        "existing_value": existing_offer["price"],
                        "new_value": new_offer["price"],
                        "difference": price_diff,
                        "difference_percent": price_diff_percent,
                    },
                )

        # Check for stock discrepancies
        if (
            "stock" in existing_offer
            and "stock" in new_offer
            and existing_offer["stock"] != new_offer["stock"]
            and existing_offer["stock"] is not None
            and new_offer["stock"] is not None
        ):
            stock_diff = abs(existing_offer["stock"] - new_offer["stock"])

            if stock_diff > 5:  # More than 5 units difference
                conflicts.append(
                    {
                        "type": "stock_discrepancy",
                        "field": "stock",
                        "existing_value": existing_offer["stock"],
                        "new_value": new_offer["stock"],
                        "difference": stock_diff,
                    },
                )

        # Check for status changes
        if (
            "status" in existing_offer
            and "status" in new_offer
            and existing_offer["status"] != new_offer["status"]
            and existing_offer["status"]
            and new_offer["status"]
        ):
            conflicts.append(
                {
                    "type": "status_change",
                    "field": "status",
                    "existing_value": existing_offer["status"],
                    "new_value": new_offer["status"],
                },
            )

        return conflicts

    def validate_offer_data(self, offer_data: dict[str, Any]) -> list[str]:
        """Validate offer data for consistency and completeness.

        Args:
            offer_data: Offer data to validate

        Returns:
            List of validation errors

        """
        errors = []

        # Required fields
        required_fields = ["emag_product_id", "emag_offer_id"]
        for field in required_fields:
            if field not in offer_data or not offer_data[field]:
                errors.append(f"Missing required field: {field}")

        # Price validation
        if "price" in offer_data and offer_data["price"] is not None and (
            not isinstance(offer_data["price"], (int, float))
            or offer_data["price"] < 0
        ):
            errors.append("Invalid price: must be a non-negative number")

        # Stock validation
        if "stock" in offer_data and offer_data["stock"] is not None:
            if not isinstance(offer_data["stock"], int) or offer_data["stock"] < 0:
                errors.append("Invalid stock: must be a non-negative integer")

        # VAT rate validation
        if "vat_rate" in offer_data and offer_data["vat_rate"] is not None:
            if not isinstance(offer_data["vat_rate"], (int, float)) or not (
                0 <= offer_data["vat_rate"] <= 100
            ):
                errors.append("Invalid VAT rate: must be between 0 and 100")

        return errors

    def transform_bulk_offers(
        self,
        emag_offers: list[ProductOfferResponse],
        account_type: str = "main",
    ) -> list[dict[str, Any]]:
        """Transform multiple eMAG offers to internal format.

        Args:
            emag_offers: List of eMAG offer responses
            account_type: Account type

        Returns:
            List of transformed offer data

        """
        transformed_offers = []

        for offer in emag_offers:
            try:
                transformed = self.transform_emag_offer_to_internal(offer, account_type)

                # Validate the transformed data
                validation_errors = self.validate_offer_data(transformed)
                if validation_errors:
                    logger.warning(
                        f"Validation errors for offer {offer.emag_id}: {validation_errors}",
                    )
                    # Still include the offer but mark it as having errors
                    transformed["validation_errors"] = validation_errors

                transformed_offers.append(transformed)

            except Exception as e:
                logger.error(f"Error transforming offer {offer.emag_id}: {e!s}")
                # Include the offer with error information
                transformed_offers.append(
                    {
                        "emag_product_id": offer.product_id,
                        "emag_offer_id": offer.emag_id,
                        "error": str(e),
                        "raw_data": getattr(offer, "raw_data", None),
                    },
                )

        return transformed_offers

    def create_import_summary(
        self,
        transformed_offers: list[dict[str, Any]],
        conflicts: list[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a summary of the import operation.

        Args:
            transformed_offers: List of transformed offer data
            conflicts: List of detected conflicts

        Returns:
            Dictionary with import summary

        """
        summary = {
            "total_offers": len(transformed_offers),
            "offers_with_errors": 0,
            "offers_valid": 0,
            "price_range": {"min": None, "max": None},
            "total_stock": 0,
            "status_distribution": {},
            "conflicts_count": len(conflicts) if conflicts else 0,
        }

        for offer in transformed_offers:
            if "error" in offer or "validation_errors" in offer:
                summary["offers_with_errors"] += 1
            else:
                summary["offers_valid"] += 1

                # Price statistics
                if "price" in offer and offer["price"] is not None:
                    price = offer["price"]
                    if (
                        summary["price_range"]["min"] is None
                        or price < summary["price_range"]["min"]
                    ):
                        summary["price_range"]["min"] = price
                    if (
                        summary["price_range"]["max"] is None
                        or price > summary["price_range"]["max"]
                    ):
                        summary["price_range"]["max"] = price

                # Stock statistics
                if "stock" in offer and offer["stock"] is not None:
                    summary["total_stock"] += offer["stock"]

                # Status distribution
                status = offer.get("status", "unknown")
                summary["status_distribution"][status] = (
                    summary["status_distribution"].get(status, 0) + 1
                )

        return summary
