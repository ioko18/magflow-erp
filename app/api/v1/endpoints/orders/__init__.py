"""Order-related API endpoints."""

from .cancellations import router as cancellations_router
from .invoice_names import router as invoice_names_router
from .invoices import router as invoices_router
from .orders import router as orders_router
from .payment_gateways import router as payment_gateways_router
from .rma import router as rma_router
from .vat import router as vat_router

__all__ = [
    "orders_router",
    "cancellations_router",
    "rma_router",
    "invoices_router",
    "invoice_names_router",
    "payment_gateways_router",
    "vat_router",
]
