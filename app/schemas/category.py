from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Category name")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Category name"
    )


class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    categories: List[CategoryResponse]
    total: int
    limit: int
    offset: int
