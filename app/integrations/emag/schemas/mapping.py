"""Pydantic schemas for eMAG product mappings."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class ProductMappingBase(BaseModel):
    """Base schema for product mappings."""

    internal_id: str = Field(..., description="Internal product ID")
    emag_id: str | None = Field(None, description="eMAG product ID")
    emag_offer_id: int | None = Field(None, description="eMAG offer ID")
    status: MappingStatus = Field(
        default=MappingStatus.PENDING,
        description="Mapping status",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class ProductMappingCreate(ProductMappingBase):
    """Schema for creating a new product mapping."""


class ProductMappingUpdate(BaseModel):
    """Schema for updating a product mapping."""

    emag_id: str | None = Field(None, description="eMAG product ID")
    emag_offer_id: int | None = Field(None, description="eMAG offer ID")
    status: MappingStatus | None = Field(None, description="Mapping status")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ProductMappingResponse(ProductMappingBase):
    """Schema for product mapping response."""

    id: int
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MappingResult(BaseModel):
    """Result of a mapping operation."""

    success: bool = Field(..., description="Whether the operation was successful")
    internal_id: str = Field(..., description="Internal product ID")
    emag_id: str | None = Field(None, description="eMAG product ID")
    emag_offer_id: int | None = Field(None, description="eMAG offer ID")
    message: str | None = Field(None, description="Status message")
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages if any",
    )


class BulkMappingResult(BaseModel):
    """Result of bulk mapping operations."""

    total: int = Field(0, description="Total number of items processed")
    successful: int = Field(0, description="Number of successful operations")
    failed: int = Field(0, description="Number of failed operations")
    results: list[MappingResult] = Field(
        default_factory=list,
        description="Individual operation results",
    )


class SyncHistoryBase(BaseModel):
    """Base schema for sync history."""

    operation: str = Field(..., description="Type of operation")
    status: str = Field(..., description="Status of the operation")
    items_processed: int = Field(0, description="Number of items processed")
    items_succeeded: int = Field(0, description="Number of items succeeded")
    items_failed: int = Field(0, description="Number of items failed")
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors if any",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class SyncHistoryCreate(SyncHistoryBase):
    """Schema for creating a new sync history entry."""

    product_mapping_id: int | None = Field(
        None,
        description="ID of the product mapping this sync is for",
    )


class SyncHistoryResponse(SyncHistoryBase):
    """Schema for sync history response."""

    id: int
    product_mapping_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FieldMappingRule(BaseModel):
    """Schema for field mapping rules."""

    internal_field: str = Field(..., description="Internal field name")
    emag_field: str = Field(..., description="eMAG field name")
    transform_function: str | None = Field(
        None,
        description="Name of the transform function to apply",
    )
    default_value: Any | None = Field(
        None,
        description="Default value if field is missing",
    )
    is_required: bool = Field(True, description="Whether the field is required")
    validation_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Validation rules for the field",
    )


class ProductFieldMappingSchema(BaseModel):
    """Schema for product field mappings."""

    name: FieldMappingRule = Field(..., description="Product name mapping")
    description: FieldMappingRule = Field(
        ...,
        description="Product description mapping",
    )
    price: FieldMappingRule = Field(..., description="Price mapping")
    stock: FieldMappingRule = Field(..., description="Stock mapping")
    category: FieldMappingRule = Field(..., description="Category mapping")
    brand: FieldMappingRule = Field(..., description="Brand mapping")
    images: FieldMappingRule = Field(..., description="Images mapping")
    characteristics: FieldMappingRule = Field(
        ...,
        description="Characteristics mapping",
    )
    part_number: FieldMappingRule | None = Field(
        None,
        description="Part number mapping",
    )
    warranty: FieldMappingRule | None = Field(None, description="Warranty mapping")
    handling_time: FieldMappingRule | None = Field(
        None,
        description="Handling time mapping",
    )


class MappingConfigurationBase(BaseModel):
    """Base schema for mapping configuration."""

    name: str = Field(..., description="Name of the configuration")
    is_active: bool = Field(True, description="Whether the configuration is active")
    description: str | None = Field(
        None,
        description="Description of the configuration",
    )
    product_field_mapping: ProductFieldMappingSchema = Field(
        ...,
        description="Field mapping configuration",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class MappingConfigurationCreate(MappingConfigurationBase):
    """Schema for creating a new mapping configuration."""


class MappingConfigurationUpdate(BaseModel):
    """Schema for updating a mapping configuration."""

    name: str | None = Field(None, description="Name of the configuration")
    is_active: bool | None = Field(
        None,
        description="Whether the configuration is active",
    )
    description: str | None = Field(
        None,
        description="Description of the configuration",
    )
    product_field_mapping: ProductFieldMappingSchema | None = Field(
        None,
        description="Field mapping configuration",
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class MappingConfigurationResponse(MappingConfigurationBase):
    """Schema for mapping configuration response."""

    id: int
    version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
