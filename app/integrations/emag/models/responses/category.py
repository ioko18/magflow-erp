"""Response models for eMAG category endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryCharacteristicValue(BaseModel):
    """Model for category characteristic value."""

    id: int = Field(..., description="Unique identifier for the characteristic value")
    value: str = Field(..., description="The actual value")
    is_default: bool = Field(
        False,
        alias="isDefault",
        description="Whether this is the default value",
    )


class CategoryCharacteristic(BaseModel):
    """Model for category characteristic."""

    id: int = Field(..., description="Unique identifier for the characteristic")
    code: str = Field(..., description="Characteristic code")
    name: str = Field(..., description="Characteristic name")
    type: str = Field(..., description="Characteristic type (e.g., 'TEXT', 'NUMBER')")
    is_required: bool = Field(
        False,
        alias="isRequired",
        description="Whether this characteristic is required",
    )
    is_filter: bool = Field(
        False,
        alias="isFilter",
        description="Whether this characteristic can be used as a filter",
    )
    is_variant: bool = Field(
        False,
        alias="isVariant",
        description="Whether this characteristic can be used for variants",
    )
    values: List[CategoryCharacteristicValue] = Field(
        default_factory=list,
        description="Possible values for this characteristic",
    )


class Category(BaseModel):
    """Model for eMAG category."""

    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    parent_id: Optional[int] = Field(
        None,
        alias="parentId",
        description="Parent category ID",
    )
    is_leaf: bool = Field(
        False,
        alias="isLeaf",
        description="Whether this is a leaf category",
    )
    characteristics: List[CategoryCharacteristic] = Field(
        default_factory=list,
        description="Category characteristics",
    )

    model_config = ConfigDict(populate_by_name=True)


class CategoryListResponse(BaseModel):
    """Response model for category list endpoint."""

    is_error: bool = Field(
        False,
        alias="isError",
        description="Indicates if there was an error",
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of messages",
    )
    results: List[Category] = Field(
        default_factory=list,
        description="List of categories",
    )

    model_config = ConfigDict(populate_by_name=True)


class CategoryCharacteristicsResponse(BaseModel):
    """Response model for category characteristics endpoint."""

    is_error: bool = Field(
        False,
        alias="isError",
        description="Indicates if there was an error",
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of messages",
    )
    results: List[CategoryCharacteristic] = Field(
        default_factory=list,
        description="List of category characteristics",
    )

    model_config = ConfigDict(populate_by_name=True)
