"""Mapping configuration utilities for eMAG integration.

This module defines Pydantic models that represent the structure of a mapping
configuration YAML file and provides helper functions to load and validate the
configuration. The tests in ``tests/unit/emag/test_mapping_config.py`` exercise
the public API:

* ``load_mapping_config`` – reads a YAML file and returns a ``ProductMappingConfig``
  instance.
* ``validate_mapping_config`` – runs additional domain‑specific validation such
  as duplicate detection and hierarchy checks.
* ``MappingConfigError`` – a custom exception type used by the validation
  functions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class MappingConfigError(Exception):
    """Raised when a mapping configuration is invalid.

    The tests expect the string representation of the exception to contain a
    helpful error message, e.g. ``"Missing required field 'emag_field'"``.
    """


# ---------------------------------------------------------------------------
# Pydantic models representing the configuration sections
# ---------------------------------------------------------------------------


class FieldMappingConfig(BaseModel):
    """Configuration for a single field mapping.
    
    Attributes:
        name: Internal field name (e.g., 'product_name')
        emag_field: Corresponding eMAG field name (e.g., 'name')
        required: Whether the field is required in eMAG
        transform: Optional transformation to apply to the field value
        min_value: Minimum allowed value for numeric fields
        default: Default value if field is missing
    """
    name: str = Field(..., description="Internal field name", json_schema_extra={"example": "product_name"})
    emag_field: str = Field(..., description="Corresponding eMAG field name", json_schema_extra={"example": "name"})
    required: bool = Field(..., description="Whether the field is required", json_schema_extra={"example": True})
    type: str = Field(..., description="Field data type (string, number, boolean, etc.)", json_schema_extra={"example": "string"})
    transform: Optional[str] = Field(
        default=None,
        description="Transformation to apply to the field value (e.g., 'uppercase', 'lowercase')",
        json_schema_extra={"example": "uppercase"}
    )
    min_value: Optional[float] = Field(
        default=None,
        description="Minimum allowed value for numeric fields",
        json_schema_extra={"example": 0}
    )
    default: Optional[Any] = Field(
        default=None,
        description="Default value if field is missing",
        json_schema_extra={"example": None}
    )


class ProductDefaultsConfig(BaseModel):
    """Default values for product fields.
    
    These defaults are applied to all products unless overridden by specific mappings.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "active",
                "marketplace_status": "enabled",
                "warranty_months": 24
            }
        }
    )
    status: Optional[str] = Field(
        default=None,
        description="Default product status in the system",
        json_schema_extra={"example": "active"}
    )
    marketplace_status: Optional[str] = Field(
        default=None,
        description="Default status in the eMAG marketplace",
        json_schema_extra={"example": "enabled"}
    )
    warranty_months: Optional[int] = Field(
        default=None,
        description="Default warranty period in months",
        json_schema_extra={"example": 24}
    )


class BrandMappingConfig(BaseModel):
    """Configuration for brand mapping."""
    internal_id: str = Field(..., description="Internal brand identifier", json_schema_extra={"example": "apple"})
    emag_id: int = Field(..., description="eMAG brand identifier", json_schema_extra={"example": 1})
    name: str = Field(..., description="Brand name", json_schema_extra={"example": "Apple"})
    model_config = ConfigDict(json_schema_extra={"example": {"internal_id": "apple", "emag_id": 1, "name": "Apple"}})


class CharacteristicValueConfig(BaseModel):
    """Configuration for characteristic value mapping."""
    internal_value: str = Field(..., description="Internal value identifier", json_schema_extra={"example": "16gb"})
    emag_value_id: int = Field(..., description="eMAG value identifier", json_schema_extra={"example": 123})
    display_value: str = Field(..., description="Human readable label", json_schema_extra={"example": "16 GB"})
    model_config = ConfigDict(json_schema_extra={"example": {"internal_value": "16gb", "emag_value_id": 123, "display_value": "16 GB"}})


class CharacteristicMappingConfig(BaseModel):
    """Configuration for characteristic mapping.
    
    Represents a product characteristic that can be mapped between internal and eMAG systems.
    """
    name: str = Field(
        ...,
        description="Name of the characteristic (e.g., 'Memory', 'Color')",
        json_schema_extra={"example": "Memory"}
    )
    emag_id: int = Field(
        ...,
        description="eMAG's identifier for this characteristic",
        json_schema_extra={"example": 1}
    )
    type: str = Field(
        ...,
        description="Type of the characteristic (e.g., 'dropdown', 'text')",
        json_schema_extra={"example": "dropdown"}
    )
    values: List[CharacteristicValueConfig] = Field(
        ...,
        description="List of possible values for this characteristic"
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Memory",
                "emag_id": 1,
                "type": "dropdown",
                "values": [
                    {"internal_value": "8gb", "emag_value_id": 123, "display_value": "8 GB"},
                    {"internal_value": "16gb", "emag_value_id": 124, "display_value": "16 GB"}
                ]
            }
        }
    )


class CategoryMappingConfig(BaseModel):
    """Configuration for category mapping between internal and eMAG categories.
    
    Attributes:
        internal_id: Internal category identifier (slug format)
        emag_id: eMAG's category identifier
        name: Human-readable category name
        parent_id: Optional parent category ID in eMAG's hierarchy (None for root categories)
    """
    internal_id: str = Field(
        ...,
        description="Internal category identifier (slug format)",
        json_schema_extra={"example": "laptops"}
    )
    emag_id: int = Field(
        ...,
        description="eMAG category identifier",
        json_schema_extra={"example": 1234}
    )
    name: str = Field(
        ...,
        description="Human-readable category name",
        json_schema_extra={"example": "Laptops"}
    )
    parent_id: Optional[int] = Field(
        None,
        description="Parent category ID in eMAG's hierarchy (None for root categories)",
        json_schema_extra={"example": 1000}
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "internal_id": "laptops",
                "emag_id": 1234,
                "name": "Laptops",
                "parent_id": 1000
            }
        }
    )


class ProductMappingConfig(BaseModel):
    """Top-level configuration for product mapping between internal and eMAG systems.
    
    This is the root model that contains all mapping configurations.
    """
    field_mappings: List[FieldMappingConfig] = Field(
        ...,
        description="List of field mappings between internal and eMAG fields"
    )
    category_mappings: List[CategoryMappingConfig] = Field(
        ...,
        description="List of category mappings between internal and eMAG categories"
    )
    brand_mappings: List[BrandMappingConfig] = Field(
        ...,
        description="List of brand mappings between internal and eMAG brands"
    )
    characteristic_mappings: List[CharacteristicMappingConfig] = Field(
        default_factory=list,
        description="List of characteristic mappings for product specifications"
    )
    product_defaults: ProductDefaultsConfig = Field(
        default_factory=ProductDefaultsConfig,
        description="Default values for product fields"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field_mappings": [
                    {"name": "product_name", "emag_field": "name", "required": True, "type": "string"}
                ],
                "category_mappings": [
                    {"internal_id": "laptops", "emag_id": 1234, "name": "Laptops", "parent_id": 1000}
                ],
                "brand_mappings": [
                    {"internal_id": "apple", "emag_id": 1, "name": "Apple"}
                ],
                "characteristic_mappings": [],
                "product_defaults": {"status": "active"}
            }
        }
    )
    
    @property
    def defaults(self) -> ProductDefaultsConfig:
        """Get the product defaults with a safe default if not set.
        
        Returns:
            ProductDefaultsConfig: The product defaults configuration
        """
        return self.product_defaults or ProductDefaultsConfig()


# Rebuild models to resolve forward references
ProductMappingConfig.model_rebuild()
CategoryMappingConfig.model_rebuild()
FieldMappingConfig.model_rebuild()
BrandMappingConfig.model_rebuild()
CharacteristicValueConfig.model_rebuild()
CharacteristicMappingConfig.model_rebuild()
ProductDefaultsConfig.model_rebuild()


def _check_duplicates(items, key_func, error_message, key_formatter=str):
    """Check for duplicate items based on a key function.
    
    Args:
        items: Iterable of items to check for duplicates
        key_func: Function to extract key from each item
        error_message: Error message prefix to use when duplicates are found
        key_formatter: Function to format the key in the error message
        
    Raises:
        MappingConfigError: If duplicate items are found
    """
    seen = {}
    for item in items:
        key = key_func(item)
        if key in seen:
            raise MappingConfigError(f"{error_message} '{key_formatter(key)}'")
        seen[key] = item


def validate_mapping_config(config: ProductMappingConfig) -> None:
    """Validate the mapping configuration.
    
    Args:
        config: The mapping configuration to validate
        
    Raises:
        MappingConfigError: If the configuration is invalid
    """
    # 1. Check for duplicate field mappings
    _check_duplicates(
        config.field_mappings,
        lambda f: f.name,
        "Duplicate field mapping",
        lambda key: f"name '{key}'",
    )
    
    # 2. Check for duplicate category mappings
    _check_duplicates(
        config.category_mappings,
        lambda c: c.internal_id,
        "Duplicate category mapping",
        lambda key: f"internal_id '{key}'",
    )
    
    # 3. Check for duplicate brand mappings
    _check_duplicates(
        config.brand_mappings,
        lambda b: b.internal_id,
        "Duplicate brand mapping",
        lambda key: f"internal_id '{key}'",
    )
    
    # 4. Check for duplicate characteristic mappings
    _check_duplicates(
        config.characteristic_mappings,
        lambda c: c.name,
        "Duplicate characteristic mapping",
        lambda key: f"name '{key}'",
    )
    
    # 5. Validate category hierarchy - each non-null parent_id must exist
    emag_ids = {cat.emag_id for cat in config.category_mappings}
    for cat in config.category_mappings:
        if cat.parent_id is not None and cat.parent_id not in emag_ids:
            raise MappingConfigError(
                f"Parent category with ID {cat.parent_id} not found"
            )
    
    # 6. Check for duplicate characteristic values
    for ch in config.characteristic_mappings:
        _check_duplicates(
            ch.values,
            lambda v: v.internal_value,
            f"Duplicate value for characteristic '{ch.name}'",
            lambda key: f"internal_value '{key}'",
        )


# Type variable for generic functions
T = TypeVar('T')

# Exported names for ``from ... import *``
__all__ = [
    "ProductMappingConfig",
    "FieldMappingConfig",
    "CategoryMappingConfig",
    "ProductDefaultsConfig",
    "BrandMappingConfig",
    "CharacteristicValueConfig",
    "CharacteristicMappingConfig",
    "MappingConfigError",
    "load_mapping_config",
    "validate_mapping_config"
]


def load_mapping_config(file_path: str | Path) -> ProductMappingConfig:
    """Load and validate a mapping configuration from a YAML file.
    
    Args:
        file_path: Path to the YAML configuration file
        
    Returns:
        Validated mapping configuration
        
    Raises:
        MappingConfigError: If the configuration is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
        
        # Convert the raw data to a ProductMappingConfig instance
        config = ProductMappingConfig(**config_data)
        
        # Run additional validations
        validate_mapping_config(config)
        
        return config
    except (yaml.YAMLError, ValidationError) as e:
        raise MappingConfigError(f"Invalid configuration: {str(e)}") from e
