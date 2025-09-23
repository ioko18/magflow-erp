"""Product mapping service for synchronizing products between internal system and eMAG."""

import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from ..models.mapping import (
    BrandIdMapping,
    BulkMappingResult,
    CategoryIdMapping,
    CharacteristicIdMapping,
    MappingConfiguration,
    MappingResult,
    MappingType,
    ProductFieldMapping,
    ProductIdMapping,
    ProductTransformationResult,
)

logger = logging.getLogger(__name__)


class ProductMappingService:
    """Service for managing product mappings between internal system and eMAG."""

    def __init__(self, config: Optional[MappingConfiguration] = None):
        """Initialize the product mapping service.

        Args:
            config: Optional mapping configuration. If not provided, uses defaults.

        """
        self.config = config or MappingConfiguration(
            product_field_mapping=self._get_default_field_mapping(),
        )

        # In-memory storage for mappings (in production, this would be a database)
        self._product_mappings: Dict[str, ProductIdMapping] = {}
        self._category_mappings: Dict[str, CategoryIdMapping] = {}
        self._brand_mappings: Dict[str, BrandIdMapping] = {}
        self._characteristic_mappings: Dict[str, CharacteristicIdMapping] = {}

    def _get_default_field_mapping(self) -> ProductFieldMapping:
        """Get default field mapping configuration."""
        from ..models.mapping import FieldMappingRule

        return ProductFieldMapping(
            name_mapping=FieldMappingRule(
                internal_field="name",
                emag_field="product_name",
                required=True,
            ),
            description_mapping=FieldMappingRule(
                internal_field="description",
                emag_field="description",
                required=False,
            ),
            price_mapping=FieldMappingRule(
                internal_field="price",
                emag_field="price",
                required=True,
            ),
            stock_mapping=FieldMappingRule(
                internal_field="stock",
                emag_field="stock",
                required=True,
            ),
            category_mapping=FieldMappingRule(
                internal_field="category_id",
                emag_field="category_id",
                required=True,
            ),
            brand_mapping=FieldMappingRule(
                internal_field="brand_id",
                emag_field="brand_id",
                required=True,
            ),
            images_mapping=FieldMappingRule(
                internal_field="images",
                emag_field="images",
                required=False,
            ),
            characteristics_mapping=FieldMappingRule(
                internal_field="characteristics",
                emag_field="characteristics",
                required=False,
            ),
            part_number_mapping=FieldMappingRule(
                internal_field="part_number",
                emag_field="part_number",
                required=False,
            ),
            warranty_mapping=FieldMappingRule(
                internal_field="warranty",
                emag_field="warranty",
                required=False,
            ),
            handling_time_mapping=FieldMappingRule(
                internal_field="handling_time",
                emag_field="handling_time",
                required=False,
            ),
        )

    # Product ID Mapping Methods

    def add_product_mapping(
        self,
        internal_id: str,
        emag_id: str,
        emag_offer_id: Optional[int] = None,
    ) -> ProductIdMapping:
        """Add or update a product ID mapping.

        Args:
            internal_id: Internal product ID
            emag_id: eMAG product ID
            emag_offer_id: Optional eMAG offer ID

        Returns:
            The created or updated mapping

        """
        mapping = ProductIdMapping(
            internal_id=internal_id,
            emag_id=emag_id,
            emag_offer_id=emag_offer_id,
        )

        self._product_mappings[internal_id] = mapping
        logger.info(f"Added product mapping: {internal_id} -> {emag_id}")
        return mapping

    def get_product_mapping(self, internal_id: str) -> Optional[ProductIdMapping]:
        """Get product mapping by internal ID.

        Args:
            internal_id: Internal product ID

        Returns:
            Product mapping if found, None otherwise

        """
        return self._product_mappings.get(internal_id)

    def find_product_by_emag_id(self, emag_id: str) -> Optional[ProductIdMapping]:
        """Find product mapping by eMAG ID.

        Args:
            emag_id: eMAG product ID

        Returns:
            Product mapping if found, None otherwise

        """
        for mapping in self._product_mappings.values():
            if mapping.emag_id == emag_id:
                return mapping
        return None

    # Category Mapping Methods

    def add_category_mapping(
        self,
        internal_id: str,
        emag_id: int,
        internal_name: str,
        emag_name: str,
    ) -> CategoryIdMapping:
        """Add or update a category ID mapping.

        Args:
            internal_id: Internal category ID
            emag_id: eMAG category ID
            internal_name: Internal category name
            emag_name: eMAG category name

        Returns:
            The created or updated mapping

        """
        mapping = CategoryIdMapping(
            internal_id=internal_id,
            emag_id=emag_id,
            internal_name=internal_name,
            emag_name=emag_name,
        )

        self._category_mappings[internal_id] = mapping
        logger.info(f"Added category mapping: {internal_name} -> {emag_name}")
        return mapping

    def get_category_mapping(self, internal_id: str) -> Optional[CategoryIdMapping]:
        """Get category mapping by internal ID.

        Args:
            internal_id: Internal category ID

        Returns:
            Category mapping if found, None otherwise

        """
        return self._category_mappings.get(internal_id)

    def find_category_by_emag_id(self, emag_id: int) -> Optional[CategoryIdMapping]:
        """Find category mapping by eMAG ID.

        Args:
            emag_id: eMAG category ID

        Returns:
            Category mapping if found, None otherwise

        """
        for mapping in self._category_mappings.values():
            if mapping.emag_id == emag_id:
                return mapping
        return None

    def find_category_by_name(
        self,
        name: str,
        fuzzy: bool = False,
    ) -> Optional[CategoryIdMapping]:
        """Find category mapping by name.

        Args:
            name: Category name to search for
            fuzzy: Whether to use fuzzy matching

        Returns:
            Category mapping if found, None otherwise

        """
        for mapping in self._category_mappings.values():
            if self.config.case_sensitive_matching:
                internal_match = mapping.internal_name == name
                emag_match = mapping.emag_name == name
            else:
                internal_match = mapping.internal_name.lower() == name.lower()
                emag_match = mapping.emag_name.lower() == name.lower()

            if internal_match or emag_match:
                return mapping

            if fuzzy:
                internal_similarity = SequenceMatcher(
                    None,
                    mapping.internal_name.lower(),
                    name.lower(),
                ).ratio()
                emag_similarity = SequenceMatcher(
                    None,
                    mapping.emag_name.lower(),
                    name.lower(),
                ).ratio()

                if (
                    internal_similarity >= self.config.fuzzy_matching_threshold
                    or emag_similarity >= self.config.fuzzy_matching_threshold
                ):
                    return mapping

        return None

    # Brand Mapping Methods

    def add_brand_mapping(
        self,
        internal_id: str,
        emag_id: int,
        internal_name: str,
        emag_name: str,
    ) -> BrandIdMapping:
        """Add or update a brand ID mapping.

        Args:
            internal_id: Internal brand ID
            emag_id: eMAG brand ID
            internal_name: Internal brand name
            emag_name: eMAG brand name

        Returns:
            The created or updated mapping

        """
        mapping = BrandIdMapping(
            internal_id=internal_id,
            emag_id=emag_id,
            internal_name=internal_name,
            emag_name=emag_name,
        )

        self._brand_mappings[internal_id] = mapping
        logger.info(f"Added brand mapping: {internal_name} -> {emag_name}")
        return mapping

    def get_brand_mapping(self, internal_id: str) -> Optional[BrandIdMapping]:
        """Get brand mapping by internal ID.

        Args:
            internal_id: Internal brand ID

        Returns:
            Brand mapping if found, None otherwise

        """
        return self._brand_mappings.get(internal_id)

    def find_brand_by_emag_id(self, emag_id: int) -> Optional[BrandIdMapping]:
        """Find brand mapping by eMAG ID.

        Args:
            emag_id: eMAG brand ID

        Returns:
            Brand mapping if found, None otherwise

        """
        for mapping in self._brand_mappings.values():
            if mapping.emag_id == emag_id:
                return mapping
        return None

    def find_brand_by_name(
        self,
        name: str,
        fuzzy: bool = False,
    ) -> Optional[BrandIdMapping]:
        """Find brand mapping by name.

        Args:
            name: Brand name to search for
            fuzzy: Whether to use fuzzy matching

        Returns:
            Brand mapping if found, None otherwise

        """
        for mapping in self._brand_mappings.values():
            if self.config.case_sensitive_matching:
                internal_match = mapping.internal_name == name
                emag_match = mapping.emag_name == name
            else:
                internal_match = mapping.internal_name.lower() == name.lower()
                emag_match = mapping.emag_name.lower() == name.lower()

            if internal_match or emag_match:
                return mapping

            if fuzzy:
                internal_similarity = SequenceMatcher(
                    None,
                    mapping.internal_name.lower(),
                    name.lower(),
                ).ratio()
                emag_similarity = SequenceMatcher(
                    None,
                    mapping.emag_name.lower(),
                    name.lower(),
                ).ratio()

                if (
                    internal_similarity >= self.config.fuzzy_matching_threshold
                    or emag_similarity >= self.config.fuzzy_matching_threshold
                ):
                    return mapping

        return None

    # Product Transformation Methods

    def transform_product_for_emag(
        self,
        internal_product: Dict[str, Any],
    ) -> ProductTransformationResult:
        """Transform an internal product to eMAG format.

        Args:
            internal_product: Internal product data

        Returns:
            Transformation result with both original and transformed data

        """
        emag_product = {}
        mappings_applied = []
        validation_errors = []

        field_mappings = self.config.product_field_mapping

        # Transform each field according to mapping rules
        for field_name, mapping_rule in field_mappings:
            if hasattr(field_mappings, field_name):
                rule = getattr(field_mappings, field_name)
                if rule is None:
                    continue

                try:
                    internal_value = internal_product.get(rule.internal_field)

                    if internal_value is None:
                        if rule.default_value is not None:
                            emag_product[rule.emag_field] = rule.default_value
                            mappings_applied.append(
                                f"Applied default value for {rule.emag_field}",
                            )
                        elif rule.required:
                            validation_errors.append(
                                f"Required field {rule.internal_field} is missing",
                            )
                        continue

                    # Apply transformation if specified
                    transformed_value = self._apply_field_transformation(
                        internal_value,
                        rule.transform_function,
                    )

                    emag_product[rule.emag_field] = transformed_value
                    mappings_applied.append(
                        f"Mapped {rule.internal_field} -> {rule.emag_field}",
                    )

                except Exception as e:
                    validation_errors.append(
                        f"Error transforming {rule.internal_field}: {e!s}",
                    )

        # Handle special mappings that require lookups
        if "category_id" in emag_product:
            category_mapping = self.get_category_mapping(
                str(internal_product.get("category_id", "")),
            )
            if category_mapping:
                emag_product["category_id"] = category_mapping.emag_id
                mappings_applied.append("Applied category ID mapping")
            elif self.config.auto_create_mappings:
                validation_errors.append(
                    "Category mapping not found and auto-create is disabled",
                )

        if "brand_id" in emag_product:
            brand_mapping = self.get_brand_mapping(
                str(internal_product.get("brand_id", "")),
            )
            if brand_mapping:
                emag_product["brand_id"] = brand_mapping.emag_id
                mappings_applied.append("Applied brand ID mapping")
            elif self.config.auto_create_mappings:
                validation_errors.append(
                    "Brand mapping not found and auto-create is disabled",
                )

        success = len(validation_errors) == 0

        return ProductTransformationResult(
            internal_product=internal_product,
            emag_product=emag_product,
            mappings_applied=mappings_applied,
            validation_errors=validation_errors,
            success=success,
        )

    def _apply_field_transformation(
        self,
        value: Any,
        transform_function: Optional[str],
    ) -> Any:
        """Apply a transformation function to a field value.

        Args:
            value: The value to transform
            transform_function: Name of the transformation function

        Returns:
            Transformed value

        """
        if transform_function is None:
            return value

        # Define available transformation functions
        transformations = {
            "to_string": lambda x: str(x),
            "to_int": lambda x: int(x) if x is not None else None,
            "to_float": lambda x: float(x) if x is not None else None,
            "strip_whitespace": lambda x: x.strip() if isinstance(x, str) else x,
            "uppercase": lambda x: x.upper() if isinstance(x, str) else x,
            "lowercase": lambda x: x.lower() if isinstance(x, str) else x,
            "title_case": lambda x: x.title() if isinstance(x, str) else x,
        }

        if transform_function in transformations:
            return transformations[transform_function](value)

        logger.warning(f"Unknown transformation function: {transform_function}")
        return value

    # Bulk Operations

    def bulk_create_product_mappings(
        self,
        mappings: List[Dict[str, Any]],
    ) -> BulkMappingResult:
        """Bulk create product mappings.

        Args:
            mappings: List of mapping data dictionaries

        Returns:
            Bulk operation result

        """
        results = []
        successful = 0
        failed = 0
        created = 0
        updated = 0

        for mapping_data in mappings:
            try:
                mapping = self.add_product_mapping(
                    internal_id=mapping_data["internal_id"],
                    emag_id=mapping_data["emag_id"],
                    emag_offer_id=mapping_data.get("emag_offer_id"),
                )

                results.append(
                    MappingResult(
                        mapping_type=MappingType.PRODUCT_ID,
                        internal_id=mapping.internal_id,
                        emag_id=mapping.emag_id,
                        success=True,
                        created=True,
                    ),
                )

                successful += 1
                created += 1

            except Exception as e:
                results.append(
                    MappingResult(
                        mapping_type=MappingType.PRODUCT_ID,
                        internal_id=mapping_data.get("internal_id", "unknown"),
                        success=False,
                        errors=[str(e)],
                    ),
                )
                failed += 1

        return BulkMappingResult(
            total_processed=len(mappings),
            successful_mappings=successful,
            failed_mappings=failed,
            new_mappings_created=created,
            existing_mappings_updated=updated,
            results=results,
        )

    # Utility Methods

    def get_mapping_statistics(self) -> Dict[str, int]:
        """Get statistics about current mappings.

        Returns:
            Dictionary with mapping counts

        """
        return {
            "product_mappings": len(self._product_mappings),
            "category_mappings": len(self._category_mappings),
            "brand_mappings": len(self._brand_mappings),
            "characteristic_mappings": len(self._characteristic_mappings),
        }

    def clear_mappings(self, mapping_type: Optional[MappingType] = None) -> None:
        """Clear mappings of specified type or all mappings.

        Args:
            mapping_type: Type of mappings to clear, or None to clear all

        """
        if mapping_type is None:
            self._product_mappings.clear()
            self._category_mappings.clear()
            self._brand_mappings.clear()
            self._characteristic_mappings.clear()
            logger.info("Cleared all mappings")
        elif mapping_type == MappingType.PRODUCT_ID:
            self._product_mappings.clear()
            logger.info("Cleared product mappings")
        elif mapping_type == MappingType.CATEGORY_ID:
            self._category_mappings.clear()
            logger.info("Cleared category mappings")
        elif mapping_type == MappingType.BRAND_ID:
            self._brand_mappings.clear()
            logger.info("Cleared brand mappings")
        elif mapping_type == MappingType.CHARACTERISTIC_ID:
            self._characteristic_mappings.clear()
            logger.info("Cleared characteristic mappings")
