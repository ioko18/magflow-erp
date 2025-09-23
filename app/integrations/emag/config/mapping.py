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
from typing import Any, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

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

    Only the attributes used in the test suite are required. Additional keys are
    allowed (``extra = 'allow'``) so that the real application can store extra
    metadata without breaking validation.
    """

    name: str = Field(..., description="Internal field name")
    emag_field: str = Field(..., description="Corresponding eMAG field name")
    required: bool = Field(..., description="Whether the field is required")
    type: str = Field(..., description="Data type of the field (string, number, …)")
    transform: Optional[str] = None
    min_value: Optional[float] = None
    default: Optional[Any] = None

    class Config:
        extra = "allow"


class CategoryMappingConfig(BaseModel):
    internal_id: str = Field(..., description="Internal category identifier")
    emag_id: int = Field(..., description="eMAG category identifier")
    name: str = Field(..., description="Category name")
    parent_id: Optional[int] = Field(
        None,
        description="eMAG ID of the parent category (null for root)",
    )

    class Config:
        extra = "allow"


class BrandMappingConfig(BaseModel):
    internal_id: str = Field(..., description="Internal brand identifier")
    emag_id: int = Field(..., description="eMAG brand identifier")
    name: str = Field(..., description="Brand name")

    class Config:
        extra = "allow"


class CharacteristicValueConfig(BaseModel):
    internal_value: str = Field(..., description="Internal representation of the value")
    emag_value_id: int = Field(..., description="eMAG value identifier")
    display_value: str = Field(..., description="Human readable label")

    class Config:
        extra = "allow"


class CharacteristicMappingConfig(BaseModel):
    name: str = Field(..., description="Characteristic name")
    emag_id: int = Field(..., description="eMAG characteristic identifier")
    type: str = Field(..., description="Characteristic type (e.g., dropdown)")
    values: List[CharacteristicValueConfig] = Field(..., description="Allowed values")

    class Config:
        extra = "allow"


class ProductDefaultsConfig(BaseModel):
    warranty_months: Optional[int] = None
    status: Optional[str] = None
    marketplace_status: Optional[str] = None

    class Config:
        extra = "allow"


class ProductMappingConfig(BaseModel):
    """Top‑level configuration model used by the tests.

    The fields correspond to the sections of the YAML file. ``extra = 'allow'``
    permits additional keys that the real application may use.
    """

    field_mappings: List[FieldMappingConfig]
    category_mappings: List[CategoryMappingConfig]
    brand_mappings: List[BrandMappingConfig]
    characteristic_mappings: List[CharacteristicMappingConfig]
    product_defaults: ProductDefaultsConfig

    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def load_mapping_config(path: str | Path) -> ProductMappingConfig:
    """Load a YAML mapping configuration file.

    Parameters
    ----------
    path: str | Path
        Path to the YAML file.

    Returns
    -------
    ProductMappingConfig
        Parsed configuration object.

    Raises
    ------
    MappingConfigError
        If the file cannot be read or the content does not conform to the schema.

    """
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Pydantic will validate required fields; we translate ValidationError
        # into MappingConfigError so the test suite sees a consistent exception type.
        return ProductMappingConfig(**data)
    except (OSError, yaml.YAMLError) as exc:
        raise MappingConfigError(str(exc)) from exc
    except ValidationError as exc:
        # Use the first error message for simplicity.
        raise MappingConfigError(exc.errors()[0]["msg"]) from exc


def _check_duplicates(items: List[Any], key_func, error_msg: str, context_func=None):
    """Utility to detect duplicate keys in a list of items.

    ``key_func`` extracts the value that must be unique. If a duplicate is found,
    ``MappingConfigError`` is raised with ``error_msg`` formatted with the duplicate
    value and optional context.
    """
    seen = set()
    for item in items:
        key = key_func(item)
        if key in seen:
            full_msg = error_msg.format(key)
            if context_func:
                full_msg += f" {context_func(key)}"
            raise MappingConfigError(full_msg)
        seen.add(key)


def validate_mapping_config(config: ProductMappingConfig) -> None:
    """Perform domain‑specific validation on a ``ProductMappingConfig``.

    The function raises ``MappingConfigError`` with a descriptive message when a
    validation rule is violated. The tests cover the following scenarios:

    * Missing required fields – already handled by Pydantic, but we re‑raise as
      ``MappingConfigError`` for consistency.
    * Duplicate field, category, brand, or characteristic definitions.
    * Invalid category hierarchy (parent_id refers to a non‑existent category).
    * Duplicate characteristic values within a characteristic.
    """
    # The Pydantic model guarantees the basic schema, so we only need the extra
    # business rules.

    # 1. Duplicate field mappings (by ``name``)
    _check_duplicates(
        config.field_mappings,
        lambda fm: fm.name,
        "Duplicate field mapping for '{}'",
    )

    # 2. Duplicate category mappings (by ``internal_id``)
    _check_duplicates(
        config.category_mappings,
        lambda cm: cm.internal_id,
        "Duplicate category mapping for internal_id '{}'",
    )

    # 3. Duplicate brand mappings (by ``internal_id``)
    _check_duplicates(
        config.brand_mappings,
        lambda bm: bm.internal_id,
        "Duplicate brand mapping for internal_id '{}'",
    )

    # 4. Duplicate characteristic mappings (by ``name``)
    _check_duplicates(
        config.characteristic_mappings,
        lambda ch: ch.name,
        "Duplicate characteristic mapping for name '{}'",
    )

    # 5. Validate category hierarchy – each non‑null parent_id must exist among
    #    the ``emag_id`` values of the defined categories.
    emag_ids = {cat.emag_id for cat in config.category_mappings}
    for cat in config.category_mappings:
        if cat.parent_id is not None and cat.parent_id not in emag_ids:
            raise MappingConfigError(
                f"Parent category with ID {cat.parent_id} not found",
            )

    # 6. Duplicate characteristic values (by ``internal_value``) within each
    #    characteristic.
    for ch in config.characteristic_mappings:
        _check_duplicates(
            ch.values,
            lambda v: v.internal_value,
            f"Duplicate value for characteristic '{ch.name}'",
            lambda key: f"internal_value '{key}'",
        )

    # If we reach this point, the configuration is considered valid.


# Exported names for ``from ... import *``
__all__ = [
    "BrandMappingConfig",
    "CategoryMappingConfig",
    "CharacteristicMappingConfig",
    "FieldMappingConfig",
    "MappingConfigError",
    "ProductMappingConfig",
    "load_mapping_config",
    "validate_mapping_config",
]
