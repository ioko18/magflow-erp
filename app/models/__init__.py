"""SQLAlchemy models for the application."""

from typing import Any

from sqlalchemy.orm import registry

from app.models.associations import product_categories
from app.models.audit_log import AuditLog
from app.models.cancellation import (
    CancellationItem,
    CancellationRefund,
    CancellationRequest,
    EmagCancellationIntegration,
)
from app.models.category import Category

# eMAG product models
from app.models.emag_models import EmagProductV2
from app.models.emag_offers import EmagOfferSync, EmagProductOffer
from app.models.inventory import InventoryItem, StockMovement, Warehouse
from app.models.invoice import Invoice, InvoiceItem

# Import all models here so they are properly registered with SQLAlchemy
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationSettings,
    NotificationType,
)
from app.models.order import Order, OrderLine
from app.models.permission import Permission
from app.models.product import Product

# Product mapping models (Google Sheets integration)
from app.models.product_mapping import GoogleSheetsProductMapping, ImportLog

# Product relationship models
from app.models.product_relationships import (
    ProductCompetitionLog,
    ProductGenealogy,
    ProductPNKTracking,
    ProductVariant,
)
from app.models.product_supplier_sheet import ProductSupplierSheet

# Purchase models (purchase order management)
from app.models.purchase import (
    PurchaseOrder,
    # PurchaseOrderLine,  # DISABLED - commented out to avoid mapper conflicts
    PurchaseOrderHistory,  # New - audit trail
    PurchaseOrderItem,  # New - maps to existing purchase_order_items table
    PurchaseOrderUnreceivedItem,  # New - track unreceived items
    PurchaseReceipt,
    # PurchaseReceiptLine,  # DISABLED - commented out to avoid FK conflicts
    PurchaseRequisition,
    PurchaseRequisitionLine,
    SupplierPayment,
    SupplierProductPurchase,
)
from app.models.rma import (
    EmagReturnIntegration,
    RefundTransaction,
    ReturnItem,
    ReturnRequest,
)
from app.models.role import Role, role_permissions, user_roles
from app.models.sales import Customer

# Supplier models (NEW - comprehensive supplier management)
from app.models.supplier import (
    Supplier,
    SupplierPerformance,
    SupplierProduct,
)

# Supplier matching models (NEW - 1688.com product matching)
from app.models.supplier_matching import (
    MatchingStatus,
    ProductMatchingGroup,
    ProductMatchingScore,
    SupplierPriceHistory,
    SupplierRawProduct,
)
from app.models.user import RefreshToken, User, UserRole
from app.models.user_session import UserSession

# Create a mapper registry
mapper_registry = registry()

# List of all model classes for easy iteration and metadata access
MODEL_CLASSES: list[type[Any]] = [
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
    PurchaseOrderItem,  # Using new model instead of PurchaseOrderLine
    # PurchaseOrderLine,  # DISABLED
    PurchaseReceipt,
    # PurchaseReceiptLine,  # DISABLED - commented out to avoid FK conflicts
    SupplierPayment,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    SupplierProductPurchase,
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
    Notification,
    NotificationSettings,
    # Product mapping models
    GoogleSheetsProductMapping,
    ImportLog,
    ProductSupplierSheet,
    # eMAG product models
    EmagProductV2,
    # Product relationship models
    ProductVariant,
    ProductPNKTracking,
    ProductCompetitionLog,
    ProductGenealogy,
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
    "PurchaseOrderItem",  # Fixed: using PurchaseOrderItem instead of PurchaseOrderLine
    "PurchaseOrderHistory",  # Added: audit trail for purchase orders
    "PurchaseOrderUnreceivedItem",  # Added: track unreceived items
    "PurchaseReceipt",
    # "PurchaseReceiptLine",  # DISABLED - commented out to avoid FK conflicts
    "SupplierPayment",
    "PurchaseRequisition",
    "PurchaseRequisitionLine",
    "SupplierProductPurchase",
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
    # Notification models
    "Notification",
    "NotificationSettings",
    "NotificationType",
    "NotificationCategory",
    "NotificationPriority",
    # Product mapping models
    "GoogleSheetsProductMapping",
    "ImportLog",
    "ProductSupplierSheet",
    # eMAG product models
    "EmagProductV2",
    # Product relationship models
    "ProductVariant",
    "ProductPNKTracking",
    "ProductCompetitionLog",
    "ProductGenealogy",
    # Enums
    "UserRole",
    # Association tables
    "user_roles",
    "role_permissions",
]
