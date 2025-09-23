"""Mapping models for product synchronization between internal system and eMAG."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MappingStatus(str, Enum):
    """Status of a mapping entry."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    DEPRECATED = "deprecated"


class MappingType(str, Enum):
    """Types of mappings supported."""

    PRODUCT_ID = "product_id"
    CATEGORY_ID = "category_id"
    BRAND_ID = "brand_id"
    CHARACTERISTIC_ID = "characteristic_id"


class ProductMapping(BaseModel):
    """Mapping between internal product ID and eMAG product ID."""

    internal_id: str = Field(..., description="Internal product ID")
    emag_id: str = Field(..., description="eMAG product ID")
    emag_offer_id: Optional[int] = Field(None, description="eMAG offer ID")
    status: MappingStatus = Field(
        default=MappingStatus.ACTIVE,
        description="Mapping status",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
    )
    last_synced_at: Optional[datetime] = Field(
        None,
        description="Last successful sync timestamp",
    )
    sync_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of sync errors",
    )

    class Config:
        """Pydantic config."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            MappingStatus: lambda v: v.value,
        }


class CategoryIdMapping(BaseModel):
    """Mapping between internal category ID and eMAG category ID."""

    internal_id: str = Field(..., description="Internal category ID")
    emag_id: int = Field(..., description="eMAG category ID")
    internal_name: str = Field(..., description="Internal category name")
    emag_name: str = Field(..., description="eMAG category name")
    status: MappingStatus = Field(
        default=MappingStatus.ACTIVE,
        description="Mapping status",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
    )
    parent_mapping: Optional[str] = Field(
        None,
        description="Parent category mapping ID",
    )

    class Config:
        """Pydantic config."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            MappingStatus: lambda v: v.value,
        }


class BrandIdMapping(BaseModel):
    """Mapping between internal brand ID and eMAG brand ID."""

    internal_id: str = Field(..., description="Internal brand ID")
    emag_id: int = Field(..., description="eMAG brand ID")
    internal_name: str = Field(..., description="Internal brand name")
    emag_name: str = Field(..., description="eMAG brand name")
    status: MappingStatus = Field(
        default=MappingStatus.ACTIVE,
        description="Mapping status",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
    )

    class Config:
        """Pydantic config."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            MappingStatus: lambda v: v.value,
        }


class CharacteristicIdMapping(BaseModel):
    """Mapping between internal characteristic and eMAG characteristic."""

    internal_id: str = Field(..., description="Internal characteristic ID")
    emag_id: int = Field(..., description="eMAG characteristic ID")
    internal_name: str = Field(..., description="Internal characteristic name")
    emag_name: str = Field(..., description="eMAG characteristic name")
    category_id: int = Field(
        ...,
        description="eMAG category ID this characteristic belongs to",
    )
    status: MappingStatus = Field(
        default=MappingStatus.ACTIVE,
        description="Mapping status",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
    )

    class Config:
        """Pydantic config."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            MappingStatus: lambda v: v.value,
        }


class FieldMappingRule(BaseModel):
    """Rule for mapping a field from internal format to eMAG format."""

    internal_field: str = Field(..., description="Internal field name")
    emag_field: str = Field(..., description="eMAG field name")
    transform_function: Optional[str] = Field(
        None,
        description="Name of transform function to apply",
    )
    default_value: Optional[Any] = Field(
        None,
        description="Default value if field is missing",
    )
    required: bool = Field(default=True, description="Whether this field is required")
    validation_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="Validation rules",
    )


class ProductFieldMapping(BaseModel):
    """Mapping configuration for product fields."""

    name_mapping: FieldMappingRule = Field(..., description="Product name mapping")
    description_mapping: FieldMappingRule = Field(
        ...,
        description="Product description mapping",
    )
    price_mapping: FieldMappingRule = Field(..., description="Price mapping")
    stock_mapping: FieldMappingRule = Field(..., description="Stock mapping")
    category_mapping: FieldMappingRule = Field(..., description="Category mapping")
    brand_mapping: FieldMappingRule = Field(..., description="Brand mapping")
    images_mapping: FieldMappingRule = Field(..., description="Images mapping")
    characteristics_mapping: FieldMappingRule = Field(
        ...,
        description="Characteristics mapping",
    )
    part_number_mapping: Optional[FieldMappingRule] = Field(
        None,
        description="Part number mapping",
    )
    warranty_mapping: Optional[FieldMappingRule] = Field(
        None,
        description="Warranty mapping",
    )
    handling_time_mapping: Optional[FieldMappingRule] = Field(
        None,
        description="Handling time mapping",
    )


class MappingConfiguration(BaseModel):
    """Configuration for all mapping operations."""

    product_field_mapping: ProductFieldMapping = Field(
        ...,
        description="Product field mapping rules",
    )
    auto_create_mappings: bool = Field(
        default=True,
        description="Auto-create mappings when not found",
    )
    update_existing_mappings: bool = Field(
        default=True,
        description="Update existing mappings on sync",
    )
    case_sensitive_matching: bool = Field(
        default=False,
        description="Case-sensitive name matching",
    )
    fuzzy_matching_threshold: float = Field(
        default=0.8,
        description="Threshold for fuzzy name matching (0-1)",
    )
    max_sync_batch_size: int = Field(
        default=50,
        description="Maximum batch size for sync operations",
    )


class MappingResult(BaseModel):
    """Result of a mapping operation."""

    mapping_type: MappingType = Field(..., description="Type of mapping")
    internal_id: str = Field(..., description="Internal ID")
    emag_id: Optional[Union[str, int]] = Field(None, description="eMAG ID")
    success: bool = Field(..., description="Whether mapping was successful")
    created: bool = Field(
        default=False,
        description="Whether a new mapping was created",
    )
    updated: bool = Field(
        default=False,
        description="Whether existing mapping was updated",
    )
    errors: List[str] = Field(default_factory=list, description="List of errors if any")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class BulkMappingResult(BaseModel):
    """Result of bulk mapping operations."""

    total_processed: int = Field(..., description="Total items processed")
    successful_mappings: int = Field(..., description="Number of successful mappings")
    failed_mappings: int = Field(..., description="Number of failed mappings")
    new_mappings_created: int = Field(..., description="Number of new mappings created")
    existing_mappings_updated: int = Field(
        ...,
        description="Number of existing mappings updated",
    )
    results: List[MappingResult] = Field(
        default_factory=list,
        description="Individual mapping results",
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Bulk operation errors",
    )


class ProductTransformationResult(BaseModel):
    """Result of transforming a product for eMAG."""

    internal_product: Dict[str, Any] = Field(
        ...,
        description="Original internal product data",
    )
    emag_product: Dict[str, Any] = Field(
        ...,
        description="Transformed eMAG product data",
    )
    mappings_applied: List[str] = Field(
        default_factory=list,
        description="List of mappings applied",
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    success: bool = Field(..., description="Whether transformation was successful")
