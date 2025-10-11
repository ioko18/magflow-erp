"""Configuration system for product mapping field transformations."""

import json
from pathlib import Path
from typing import Any

from ..models.mapping import (
    FieldMappingRule,
    MappingConfiguration,
    ProductFieldMapping,
)


class MappingConfigLoader:
    """Loader for mapping configuration from various sources."""

    @staticmethod
    def from_dict(config_dict: dict[str, Any]) -> MappingConfiguration:
        """Load configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            MappingConfiguration instance

        """
        return MappingConfiguration(**config_dict)

    @staticmethod
    def from_json_file(file_path: str | Path) -> MappingConfiguration:
        """Load configuration from a JSON file.

        Args:
            file_path: Path to the JSON configuration file

        Returns:
            MappingConfiguration instance

        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(path, encoding="utf-8") as f:
            config_dict = json.load(f)

        return MappingConfigLoader.from_dict(config_dict)

    @staticmethod
    def from_env_vars(prefix: str = "EMAG_MAPPING_") -> MappingConfiguration:
        """Load configuration from environment variables.

        Args:
            prefix: Environment variable prefix

        Returns:
            MappingConfiguration instance

        """
        import os

        config_dict = {}

        # Load simple configuration values
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix) :].lower()

                # Handle boolean values
                if value.lower() in ("true", "false"):
                    config_dict[config_key] = value.lower() == "true"
                # Handle numeric values
                elif value.isdigit():
                    config_dict[config_key] = int(value)
                elif value.replace(".", "").isdigit():
                    config_dict[config_key] = float(value)
                else:
                    config_dict[config_key] = value

        return MappingConfiguration(**config_dict)

    @staticmethod
    def create_default_config() -> MappingConfiguration:
        """Create a default mapping configuration.

        Returns:
            Default MappingConfiguration instance

        """
        return MappingConfiguration(
            product_field_mapping=ProductFieldMapping(
                name_mapping=FieldMappingRule(
                    internal_field="name",
                    emag_field="product_name",
                    required=True,
                ),
                description_mapping=FieldMappingRule(
                    internal_field="description",
                    emag_field="description",
                    transform_function="strip_whitespace",
                    required=False,
                ),
                price_mapping=FieldMappingRule(
                    internal_field="price",
                    emag_field="price",
                    transform_function="to_float",
                    required=True,
                ),
                stock_mapping=FieldMappingRule(
                    internal_field="stock_quantity",
                    emag_field="stock",
                    transform_function="to_int",
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
                    internal_field="specifications",
                    emag_field="characteristics",
                    required=False,
                ),
                part_number_mapping=FieldMappingRule(
                    internal_field="sku",
                    emag_field="part_number",
                    required=False,
                ),
                warranty_mapping=FieldMappingRule(
                    internal_field="warranty_months",
                    emag_field="warranty",
                    transform_function="to_int",
                    required=False,
                ),
                handling_time_mapping=FieldMappingRule(
                    internal_field="handling_days",
                    emag_field="handling_time",
                    transform_function="to_int",
                    required=False,
                ),
            ),
            auto_create_mappings=True,
            update_existing_mappings=True,
            case_sensitive_matching=False,
            fuzzy_matching_threshold=0.8,
            max_sync_batch_size=50,
        )


class MappingPreset:
    """Predefined mapping configurations for common scenarios."""

    @staticmethod
    def magento_to_emag() -> MappingConfiguration:
        """Configuration for mapping from Magento to eMAG.

        Returns:
            MappingConfiguration for Magento integration

        """
        return MappingConfiguration(
            product_field_mapping=ProductFieldMapping(
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
                    internal_field="qty",
                    emag_field="stock",
                    required=True,
                ),
                category_mapping=FieldMappingRule(
                    internal_field="category_ids",
                    emag_field="category_id",
                    required=True,
                ),
                brand_mapping=FieldMappingRule(
                    internal_field="manufacturer",
                    emag_field="brand_id",
                    required=True,
                ),
                images_mapping=FieldMappingRule(
                    internal_field="media_gallery",
                    emag_field="images",
                    required=False,
                ),
                characteristics_mapping=FieldMappingRule(
                    internal_field="custom_attributes",
                    emag_field="characteristics",
                    required=False,
                ),
                part_number_mapping=FieldMappingRule(
                    internal_field="sku",
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
            ),
        )

    @staticmethod
    def woocommerce_to_emag() -> MappingConfiguration:
        """Configuration for mapping from WooCommerce to eMAG.

        Returns:
            MappingConfiguration for WooCommerce integration

        """
        return MappingConfiguration(
            product_field_mapping=ProductFieldMapping(
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
                    internal_field="regular_price",
                    emag_field="price",
                    required=True,
                ),
                stock_mapping=FieldMappingRule(
                    internal_field="stock_quantity",
                    emag_field="stock",
                    required=True,
                ),
                category_mapping=FieldMappingRule(
                    internal_field="categories",
                    emag_field="category_id",
                    required=True,
                ),
                brand_mapping=FieldMappingRule(
                    internal_field="brands",
                    emag_field="brand_id",
                    required=True,
                ),
                images_mapping=FieldMappingRule(
                    internal_field="images",
                    emag_field="images",
                    required=False,
                ),
                characteristics_mapping=FieldMappingRule(
                    internal_field="attributes",
                    emag_field="characteristics",
                    required=False,
                ),
                part_number_mapping=FieldMappingRule(
                    internal_field="sku",
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
            ),
        )

    @staticmethod
    def custom_erp_to_emag() -> MappingConfiguration:
        """Configuration for mapping from a custom ERP to eMAG.

        Returns:
            MappingConfiguration for custom ERP integration

        """
        return MappingConfiguration(
            product_field_mapping=ProductFieldMapping(
                name_mapping=FieldMappingRule(
                    internal_field="product_name",
                    emag_field="product_name",
                    required=True,
                ),
                description_mapping=FieldMappingRule(
                    internal_field="product_description",
                    emag_field="description",
                    required=False,
                ),
                price_mapping=FieldMappingRule(
                    internal_field="sales_price",
                    emag_field="price",
                    required=True,
                ),
                stock_mapping=FieldMappingRule(
                    internal_field="available_stock",
                    emag_field="stock",
                    required=True,
                ),
                category_mapping=FieldMappingRule(
                    internal_field="category_code",
                    emag_field="category_id",
                    required=True,
                ),
                brand_mapping=FieldMappingRule(
                    internal_field="brand_code",
                    emag_field="brand_id",
                    required=True,
                ),
                images_mapping=FieldMappingRule(
                    internal_field="image_urls",
                    emag_field="images",
                    required=False,
                ),
                characteristics_mapping=FieldMappingRule(
                    internal_field="specifications",
                    emag_field="characteristics",
                    required=False,
                ),
                part_number_mapping=FieldMappingRule(
                    internal_field="part_number",
                    emag_field="part_number",
                    required=False,
                ),
                warranty_mapping=FieldMappingRule(
                    internal_field="warranty_period",
                    emag_field="warranty",
                    required=False,
                ),
                handling_time_mapping=FieldMappingRule(
                    internal_field="processing_days",
                    emag_field="handling_time",
                    required=False,
                ),
            ),
        )


class MappingConfigManager:
    """Manager for loading and managing mapping configurations."""

    def __init__(self, config_dir: str | Path | None = None):
        """Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files

        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._current_config: MappingConfiguration | None = None

    def load_config(self, config_name: str = "default") -> MappingConfiguration:
        """Load a mapping configuration by name.

        Args:
            config_name: Name of the configuration to load

        Returns:
            MappingConfiguration instance

        """
        config_file = self.config_dir / f"mapping_{config_name}.json"

        if config_file.exists():
            self._current_config = MappingConfigLoader.from_json_file(config_file)
        else:
            # Create default configuration if file doesn't exist
            self._current_config = MappingConfigLoader.create_default_config()
            self.save_config(config_name)

        return self._current_config

    def save_config(
        self,
        config_name: str,
        config: MappingConfiguration | None = None,
    ) -> None:
        """Save a mapping configuration to file.

        Args:
            config_name: Name of the configuration
            config: Configuration to save (uses current if not provided)

        """
        if config is None:
            config = self._current_config or MappingConfigLoader.create_default_config()

        config_file = self.config_dir / f"mapping_{config_name}.json"

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config.dict(), f, indent=2, ensure_ascii=False)

    def list_configs(self) -> list[str]:
        """List available configuration files.

        Returns:
            List of configuration names

        """
        config_files = list(self.config_dir.glob("mapping_*.json"))
        return [f.stem.replace("mapping_", "") for f in config_files]

    def create_preset_config(
        self,
        preset_name: str,
        config_name: str,
    ) -> MappingConfiguration:
        """Create a configuration from a preset.

        Args:
            preset_name: Name of the preset (magento, woocommerce, custom_erp)
            config_name: Name to save the configuration as

        Returns:
            Created MappingConfiguration

        """
        presets = {
            "magento": MappingPreset.magento_to_emag,
            "woocommerce": MappingPreset.woocommerce_to_emag,
            "custom_erp": MappingPreset.custom_erp_to_emag,
        }

        if preset_name not in presets:
            available = list(presets.keys())
            raise ValueError(f"Unknown preset: {preset_name}. Available: {available}")

        config = presets[preset_name]()
        self.save_config(config_name, config)
        self._current_config = config

        return config

    @property
    def current_config(self) -> MappingConfiguration | None:
        """Get the current configuration.

        Returns:
            Current MappingConfiguration or None

        """
        return self._current_config

    def validate_config(
        self,
        config: MappingConfiguration | None = None,
    ) -> list[str]:
        """Validate a mapping configuration.

        Args:
            config: Configuration to validate (uses current if not provided)

        Returns:
            List of validation errors (empty if valid)

        """
        if config is None:
            config = self._current_config

        if config is None:
            return ["No configuration loaded"]

        errors = []

        # Validate required fields
        field_mappings = config.product_field_mapping
        required_fields = [
            "name_mapping",
            "price_mapping",
            "stock_mapping",
            "category_mapping",
            "brand_mapping",
        ]

        for field_name in required_fields:
            if hasattr(field_mappings, field_name):
                field_mapping = getattr(field_mappings, field_name)
                if field_mapping and not field_mapping.internal_field:
                    errors.append(
                        f"Required field {field_name} has no internal field mapping",
                    )

        # Validate fuzzy matching threshold
        if not 0 <= config.fuzzy_matching_threshold <= 1:
            errors.append("Fuzzy matching threshold must be between 0 and 1")

        # Validate batch size
        if config.max_sync_batch_size <= 0:
            errors.append("Max sync batch size must be positive")

        return errors
