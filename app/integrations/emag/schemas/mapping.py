"""Pydantic schemas for eMAG product mappings."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

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


class ProductMappingBase(BaseModel):
    """Base schema for product mappings."""

    internal_id: str = Field(..., description="Internal product ID")
    emag_id: Optional[str] = Field(None, description="eMAG product ID")
    emag_offer_id: Optional[int] = Field(None, description="eMAG offer ID")
    status: MappingStatus = Field(
        default=MappingStatus.PENDING,
        description="Mapping status",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class ProductMappingCreate(ProductMappingBase):
    """Schema for creating a new product mapping."""


class ProductMappingUpdate(BaseModel):
    """Schema for updating a product mapping."""

    emag_id: Optional[str] = Field(None, description="eMAG product ID")
    emag_offer_id: Optional[int] = Field(None, description="eMAG offer ID")
    status: Optional[MappingStatus] = Field(None, description="Mapping status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ProductMappingResponse(ProductMappingBase):
    """Schema for product mapping response."""

    id: int
    created_at: datetime
    updated_at: datetime
    last_synced_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class MappingResult(BaseModel):
    """Result of a mapping operation."""

    success: bool = Field(..., description="Whether the operation was successful")
    internal_id: str = Field(..., description="Internal product ID")
    emag_id: Optional[str] = Field(None, description="eMAG product ID")
    emag_offer_id: Optional[int] = Field(None, description="eMAG offer ID")
    message: Optional[str] = Field(None, description="Status message")
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages if any",
    )


class BulkMappingResult(BaseModel):
    """Result of bulk mapping operations."""

    total: int = Field(0, description="Total number of items processed")
    successful: int = Field(0, description="Number of successful operations")
    failed: int = Field(0, description="Number of failed operations")
    results: List[MappingResult] = Field(
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
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors if any",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class SyncHistoryCreate(SyncHistoryBase):
    """Schema for creating a new sync history entry."""

    product_mapping_id: Optional[int] = Field(
        None,
        description="ID of the product mapping this sync is for",
    )


class SyncHistoryResponse(SyncHistoryBase):
    """Schema for sync history response."""

    id: int
    product_mapping_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


class FieldMappingRule(BaseModel):
    """Schema for field mapping rules."""

    internal_field: str = Field(..., description="Internal field name")
    emag_field: str = Field(..., description="eMAG field name")
    transform_function: Optional[str] = Field(
        None,
        description="Name of the transform function to apply",
    )
    default_value: Optional[Any] = Field(
        None,
        description="Default value if field is missing",
    )
    is_required: bool = Field(True, description="Whether the field is required")
    validation_rules: Dict[str, Any] = Field(
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
    part_number: Optional[FieldMappingRule] = Field(
        None,
        description="Part number mapping",
    )
    warranty: Optional[FieldMappingRule] = Field(None, description="Warranty mapping")
    handling_time: Optional[FieldMappingRule] = Field(
        None,
        description="Handling time mapping",
    )


class MappingConfigurationBase(BaseModel):
    """Base schema for mapping configuration."""

    name: str = Field(..., description="Name of the configuration")
    is_active: bool = Field(True, description="Whether the configuration is active")
    description: Optional[str] = Field(
        None,
        description="Description of the configuration",
    )
    product_field_mapping: ProductFieldMappingSchema = Field(
        ...,
        description="Field mapping configuration",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class MappingConfigurationCreate(MappingConfigurationBase):
    """Schema for creating a new mapping configuration."""


class MappingConfigurationUpdate(BaseModel):
    """Schema for updating a mapping configuration."""

    name: Optional[str] = Field(None, description="Name of the configuration")
    is_active: Optional[bool] = Field(
        None,
        description="Whether the configuration is active",
    )
    description: Optional[str] = Field(
        None,
        description="Description of the configuration",
    )
    product_field_mapping: Optional[ProductFieldMappingSchema] = Field(
        None,
        description="Field mapping configuration",
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MappingConfigurationResponse(MappingConfigurationBase):
    """Schema for mapping configuration response."""

    id: int
    version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
