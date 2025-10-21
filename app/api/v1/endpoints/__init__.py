"""API v1 endpoints package."""

# Import all routers from subdirectories
from .emag.emag_addresses import router as emag_addresses
from .emag.emag_advanced import router as emag_advanced
from .emag.emag_campaigns import router as emag_campaigns
from .emag.emag_customers import router as emag_customers
from .emag.emag_db_offers import router as emag_db_offers
from .emag.emag_ean_matching import router as emag_ean_matching
from .emag.emag_integration import router as emag_integration
from .emag.emag_management import router as emag_management
from .emag.emag_offers import router as emag_offers
from .emag.emag_orders import router as emag_orders
from .emag.emag_phase2 import router as emag_phase2
from .emag.emag_price_update import router as emag_price_update
from .emag.emag_pricing_intelligence import router as emag_pricing_intelligence
from .emag.emag_product_copy import router as emag_product_copy
from .emag.emag_product_publishing import router as emag_product_publishing
from .emag.emag_product_sync import router as emag_product_sync
from .emag.emag_sync import router as emag_sync
from .inventory.emag_inventory import router as emag_inventory
from .inventory.inventory_management import router as inventory_management
from .inventory.low_stock_suppliers import router as low_stock_suppliers
from .inventory.stock_sync import router as stock_sync
from .orders.cancellations import router as cancellations
from .orders.invoices import router as invoices
from .orders.orders import router as orders
from .orders.payment_gateways import router as payment_gateways
from .orders.rma import router as rma
from .orders.vat import router as vat
from .products.product_chinese_name import router as product_chinese_name
from .products.product_import import router as product_import

# from .products.invoice_names import router as invoice_names  # File does not exist
from .products.product_management import router as product_management
from .products.product_relationships import router as product_relationships
from .products.product_republish import router as product_republish
from .products.product_update import router as product_update
from .products.product_variants_local import router as product_variants_local
from .products.products_legacy import router as products_v1
from .purchase_orders import router as purchase_orders
from .reporting.reporting import router as reporting
from .suppliers.supplier_matching import router as supplier_matching
from .suppliers.supplier_migration import router as supplier_migration
from .suppliers.suppliers import router as suppliers
from .system.admin import router as admin
from .system.database import router as database
from .system.migration_management import router as migration_management
from .system.notifications import router as notifications
from .system.performance_metrics import router as performance_metrics
from .system.session_management import router as session_management
from .system.sms_notifications import router as sms_notifications
from .system.test_auth import router as test_auth
from .system.websocket_notifications import router as websocket_notifications
from .system.websocket_sync import router as websocket_sync

__all__ = [
    "admin",
    "emag_integration",
    "emag_sync",
    "emag_offers",
    "emag_orders",
    "emag_customers",
    "emag_advanced",
    "emag_management",
    "emag_phase2",
    "emag_addresses",
    "emag_price_update",
    "emag_pricing_intelligence",
    "emag_campaigns",
    "emag_product_publishing",
    "emag_product_sync",
    "emag_product_copy",
    "emag_ean_matching",
    "websocket_sync",
    "websocket_notifications",
    "test_auth",
    "orders",
    "vat",
    "emag_db_offers",
    "payment_gateways",
    "sms_notifications",
    "rma",
    "cancellations",
    "invoices",
    "reporting",
    "database",
    "products_v1",
    "supplier_matching",
    "suppliers",
    "supplier_migration",
    "product_import",
    "product_update",
    "product_relationships",
    "product_chinese_name",
    "stock_sync",
    "product_republish",
    "product_variants_local",
    # "invoice_names",
    "product_management",
    "inventory_management",
    "emag_inventory",
    "low_stock_suppliers",
    "notifications",
    "migration_management",
    "session_management",
    "performance_metrics",
    "purchase_orders",
]
