"""Compatibility schemas for legacy tests expecting simple catalog DTOs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None
    is_active: bool = True


class ProductCreate(BaseModel):
    name: str
    sku: str
    price: float
    currency: str = "RON"
    description: Optional[str] = None
    stock_quantity: int = 0
    status: str = "active"
    is_active: bool = True
    category_id: int


class Product(BaseModel):
    id: int
    name: str
    sku: str
    price: float
    currency: str
    description: Optional[str] = None
    stock_quantity: int
    status: str
    is_active: bool
    category_id: int
    created_at: datetime
    updated_at: datetime
    image_url: Optional[HttpUrl] = None


class Category(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


__all__ = [
    "ProductCreate",
    "CategoryCreate",
    "Product",
    "Category",
]
