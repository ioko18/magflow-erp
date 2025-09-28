"""Unit tests for mapping configuration."""

from unittest.mock import mock_open, patch

import pytest
import yaml
from pydantic import ValidationError

from app.integrations.emag.config.mapping import (
    MappingConfigError,
    ProductMappingConfig,
    load_mapping_config,
    validate_mapping_config,
)

# Sample valid mapping configuration
SAMPLE_MAPPING_CONFIG = """
field_mappings:
  - name: "name"
    emag_field: "name"
    required: true
    type: "string"
    transform: "trim"

  - name: "price"
    emag_field: "sale_price"
    required: true
    type: "number"
    min_value: 0

  - name: "stock"
    emag_field: "stock"
    required: true
    type: "integer"
    default: 0
    min_value: 0

category_mappings:
  - internal_id: "electronics"
    emag_id: 1000
    name: "Electronics"
    parent_id: null

  - internal_id: "laptops"
    emag_id: 1001
    name: "Laptops"
    parent_id: 1000

brand_mappings:
  - internal_id: "apple"
    emag_id: 2000
    name: "Apple"

  - internal_id: "samsung"
    emag_id: 2001
    name: "Samsung"

characteristic_mappings:
  - name: "color"
    emag_id: 3000
    type: "dropdown"
    values:
      - internal_value: "red"
        emag_value_id: 3001
        display_value: "Red"

      - internal_value: "blue"
        emag_value_id: 3002
        display_value: "Blue"

product_defaults:
  warranty_months: 24
  status: "active"
  marketplace_status: "enabled"
"""


def test_load_mapping_config():
    """Test loading mapping configuration from a YAML file."""
    with patch(
        "builtins.open", mock_open(read_data=SAMPLE_MAPPING_CONFIG)
    ) as mock_file:
        config = load_mapping_config("dummy_path.yaml")

        # Verify the file was opened
        mock_file.assert_called_once_with("dummy_path.yaml", "r", encoding="utf-8")

        # Verify the config was loaded correctly
        assert len(config.field_mappings) == 3
        assert len(config.category_mappings) == 2
        assert len(config.brand_mappings) == 2
        assert len(config.characteristic_mappings) == 1
        assert config.product_defaults.warranty_months == 24


def test_validate_mapping_config_valid():
    """Test validating a valid mapping configuration."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)
    config = ProductMappingConfig(**config_dict)

    # Should not raise an exception
    validate_mapping_config(config)


def test_validate_mapping_config_missing_required_field():
    """Test validating a mapping configuration with a missing required field."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)

    # Remove a required field
    config_dict["field_mappings"][0].pop("emag_field")
    
    # Should raise a validation error when creating the config
    with pytest.raises(ValidationError) as excinfo:
        ProductMappingConfig(**config_dict)
    
    # Check that the error message contains the expected field
    error_messages = [str(e) for e in excinfo.value.errors()]
    assert any("emag_field" in msg for msg in error_messages)


def test_validate_mapping_config_duplicate_field_mapping():
    """Test validating a mapping configuration with duplicate field mappings."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)

    # Add a duplicate field mapping
    duplicate_field = dict(config_dict["field_mappings"][0])
    config_dict["field_mappings"].append(duplicate_field)
    config = ProductMappingConfig(**config_dict)

    # Should raise an exception
    with pytest.raises(MappingConfigError) as excinfo:
        validate_mapping_config(config)

    assert "Duplicate field mapping 'name 'name''" in str(excinfo.value)


def test_validate_mapping_config_duplicate_category():
    """Test validating a mapping configuration with duplicate category mappings."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)

    # Add a duplicate category mapping
    duplicate_category = dict(config_dict["category_mappings"][0])
    config_dict["category_mappings"].append(duplicate_category)
    config = ProductMappingConfig(**config_dict)

    # Should raise an exception
    with pytest.raises(MappingConfigError) as excinfo:
        validate_mapping_config(config)

    assert "Duplicate category mapping 'internal_id 'electronics''" in str(excinfo.value)


def test_validate_mapping_config_duplicate_brand():
    """Test validating a mapping configuration with duplicate brand mappings."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)

    # Add a duplicate brand mapping
    duplicate_brand = dict(config_dict["brand_mappings"][0])
    config_dict["brand_mappings"].append(duplicate_brand)
    config = ProductMappingConfig(**config_dict)

    # Should raise an exception
    with pytest.raises(MappingConfigError) as excinfo:
        validate_mapping_config(config)

    assert "Duplicate brand mapping 'internal_id 'apple''" in str(excinfo.value)


def test_validate_mapping_config_duplicate_characteristic():
    """Test validating a mapping configuration with duplicate characteristic mappings."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)

    # Add a duplicate characteristic mapping
    duplicate_char = dict(config_dict["characteristic_mappings"][0])
    config_dict["characteristic_mappings"].append(duplicate_char)
    config = ProductMappingConfig(**config_dict)

    # Should raise an exception
    with pytest.raises(MappingConfigError) as excinfo:
        validate_mapping_config(config)

    assert "Duplicate characteristic mapping 'name 'color''" in str(excinfo.value)


def test_validate_mapping_config_invalid_category_hierarchy():
    """Test validating a mapping configuration with an invalid category hierarchy."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)

    # Add a category with a non-existent parent
    invalid_category = {
        "internal_id": "invalid",
        "emag_id": 9999,
        "name": "Invalid Category",
        "parent_id": 9998,  # Non-existent parent
    }
    config_dict["category_mappings"].append(invalid_category)
    config = ProductMappingConfig(**config_dict)

    # Should raise an exception
    with pytest.raises(MappingConfigError) as excinfo:
        validate_mapping_config(config)

    assert "Parent category with ID 9998 not found" in str(excinfo.value)


def test_validate_mapping_config_duplicate_characteristic_value():
    """Test validating a mapping configuration with duplicate characteristic values."""
    config_dict = yaml.safe_load(SAMPLE_MAPPING_CONFIG)

    # Add a duplicate characteristic value
    duplicate_value = dict(config_dict["characteristic_mappings"][0]["values"][0])
    config_dict["characteristic_mappings"][0]["values"].append(duplicate_value)
    config = ProductMappingConfig(**config_dict)

    # Should raise an exception
    with pytest.raises(MappingConfigError) as excinfo:
        validate_mapping_config(config)

    assert "Duplicate value for characteristic 'color'" in str(excinfo.value)
    assert "internal_value 'red'" in str(excinfo.value)
