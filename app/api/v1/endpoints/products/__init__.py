"""Product-related API endpoints."""

from .categories import router as categories_router
from .product_chinese_name import router as product_chinese_name_router
from .product_import import router as product_import_router
from .product_management import router as product_management_router
from .product_relationships import router as product_relationships_router
from .product_republish import router as product_republish_router
from .product_update import router as product_update_router
from .product_variants_local import router as product_variants_router
from .products_legacy import router as products_legacy_router

__all__ = [
    "product_management_router",
    "product_import_router",
    "product_update_router",
    "product_relationships_router",
    "product_chinese_name_router",
    "product_variants_router",
    "product_republish_router",
    "products_legacy_router",
    "categories_router",
]
