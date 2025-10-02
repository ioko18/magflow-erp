"""SQLAlchemy models for the application."""

from typing import Any, List, Type

from sqlalchemy.orm import registry

# Import all models here so they are properly registered with SQLAlchemy
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.models.user import User, RefreshToken, UserRole
from app.models.user_session import UserSession
from app.models.role import Role, user_roles, role_permissions
from app.models.permission import Permission
from app.models.product import Product
from app.models.category import Category
from app.models.inventory import Warehouse, StockMovement, InventoryItem
from app.models.sales import Customer
# Supplier models (NEW - comprehensive supplier management)
from app.models.supplier import (
    Supplier,
    SupplierProduct,
    SupplierPerformance,
    PurchaseOrder,
    PurchaseOrderItem,
)
# Supplier matching models (NEW - 1688.com product matching)
from app.models.supplier_matching import (
    SupplierRawProduct,
    ProductMatchingGroup,
    ProductMatchingScore,
    SupplierPriceHistory,
    MatchingStatus,
)
from app.models.invoice import Invoice, InvoiceItem
from app.models.cancellation import (
    CancellationRequest,
    CancellationItem,
    CancellationRefund,
    EmagCancellationIntegration,
)
from app.models.rma import ReturnRequest, ReturnItem, RefundTransaction, EmagReturnIntegration
from app.models.emag_offers import EmagProductOffer, EmagOfferSync
from app.models.order import Order, OrderLine
from app.models.audit_log import AuditLog
from app.models.associations import product_categories

# Create a mapper registry
mapper_registry = registry()

# List of all model classes for easy iteration and metadata access
MODEL_CLASSES: List[Type[Any]] = [
    User,
    Role,
    Permission,
    RefreshToken,
    Product,
    Warehouse,
    StockMovement,
    InventoryItem,
    Order,
    OrderLine,
    # Purchase models (NEW supplier management)
    Supplier,
    SupplierProduct,
    SupplierPerformance,
    PurchaseOrder,
    PurchaseOrderItem,
    # Supplier matching models
    SupplierRawProduct,
    ProductMatchingGroup,
    ProductMatchingScore,
    SupplierPriceHistory,
    Invoice,
    InvoiceItem,
    CancellationRequest,
    CancellationItem,
    CancellationRefund,
    ReturnRequest,
    ReturnItem,
    RefundTransaction,
    EmagReturnIntegration,
    EmagProductOffer,
    EmagOfferSync,
    UserSession,
    AuditLog,
]

__all__ = [
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    # Core models
    "User",
    "Role",
    "Permission",
    "RefreshToken",
    "UserSession",
    "AuditLog",
    # Product models
    "Product",
    "Category",
    "product_categories",
    # Inventory models
    "Warehouse",
    "StockMovement",
    "InventoryItem",
    # Sales models
    "Order",
    "OrderLine",
    "Customer",
    # Purchase models (NEW supplier management)
    "Supplier",
    "SupplierProduct",
    "SupplierPerformance",
    "PurchaseOrder",
    "PurchaseOrderItem",
    # Supplier matching models
    "SupplierRawProduct",
    "ProductMatchingGroup",
    "ProductMatchingScore",
    "SupplierPriceHistory",
    "MatchingStatus",
    # Invoice models
    "Invoice",
    "InvoiceItem",
    # Cancellation models
    "CancellationRequest",
    "CancellationItem",
    "CancellationRefund",
    "EmagCancellationIntegration",
    # RMA models
    "ReturnRequest",
    "ReturnItem",
    "RefundTransaction",
    "EmagReturnIntegration",
    # eMAG models
    "EmagProductOffer",
    "EmagOfferSync",
    # Enums
    "UserRole",
    # Association tables
    "user_roles",
    "role_permissions",
]
