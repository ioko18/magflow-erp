"""Pydantic schemas for the application."""

# Import schemas with explicit imports to avoid F405 linting errors
from .purchase import (
    # Purchase Order schemas
    PurchaseOrder,
    PurchaseOrderCreate,
    PurchaseOrderLine,
    PurchaseOrderLineCreate,
    PurchaseOrderStatus,
    PurchaseOrderUpdate,
    # Purchase Receipt schemas
    PurchaseReceipt,
    PurchaseReceiptCreate,
    PurchaseReceiptLine,
    PurchaseReceiptLineCreate,
    PurchaseReceiptStatus,
    PurchaseReceiptUpdate,
    # Purchase Requisition schemas
    PurchaseRequisition,
    PurchaseRequisitionCreate,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineCreate,
    PurchaseRequisitionPriority,
    PurchaseRequisitionStatus,
    PurchaseRequisitionUpdate,
    # Supplier schemas
    Supplier,
    SupplierCreate,
    # Supplier Payment schemas
    SupplierPayment,
    SupplierPaymentCreate,
    SupplierPaymentMethod,
    SupplierPaymentStatus,
    SupplierPaymentUpdate,
    # Supplier Product schemas (legacy - for purchase orders)
    SupplierProduct,
    SupplierProductCreate,
    SupplierProductUpdate,
    SupplierStatus,
    SupplierUpdate,
)
from .supplier_product import (
    # Supplier Product schemas (1688.com integration)
    ChineseNameUpdate,
    LocalProductInfo,
    MatchingUpdate,
    PriceUpdate,
    SpecificationUpdate,
    SupplierChange,
    SupplierProductListResponse,
    SupplierProductResponse,
    SupplierProductStatistics,
    URLUpdate,
)

__all__ = [
    # Purchase schemas - Supplier
    "Supplier",
    "SupplierCreate",
    "SupplierUpdate",
    "SupplierStatus",
    # Purchase schemas - Supplier Product (legacy)
    "SupplierProduct",
    "SupplierProductCreate",
    "SupplierProductUpdate",
    # Supplier Product schemas (1688.com integration)
    "SupplierProductResponse",
    "SupplierProductListResponse",
    "SupplierProductStatistics",
    "LocalProductInfo",
    "ChineseNameUpdate",
    "SpecificationUpdate",
    "URLUpdate",
    "PriceUpdate",
    "SupplierChange",
    "MatchingUpdate",
    # Purchase schemas - Purchase Order
    "PurchaseOrder",
    "PurchaseOrderCreate",
    "PurchaseOrderUpdate",
    "PurchaseOrderStatus",
    "PurchaseOrderLine",
    "PurchaseOrderLineCreate",
    # Purchase schemas - Purchase Receipt
    "PurchaseReceipt",
    "PurchaseReceiptCreate",
    "PurchaseReceiptUpdate",
    "PurchaseReceiptStatus",
    "PurchaseReceiptLine",
    "PurchaseReceiptLineCreate",
    # Purchase schemas - Supplier Payment
    "SupplierPayment",
    "SupplierPaymentCreate",
    "SupplierPaymentUpdate",
    "SupplierPaymentMethod",
    "SupplierPaymentStatus",
    # Purchase schemas - Purchase Requisition
    "PurchaseRequisition",
    "PurchaseRequisitionCreate",
    "PurchaseRequisitionUpdate",
    "PurchaseRequisitionPriority",
    "PurchaseRequisitionStatus",
    "PurchaseRequisitionLine",
    "PurchaseRequisitionLineCreate",
]
