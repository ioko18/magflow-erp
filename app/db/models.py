"""Compatibility layer re-exporting models from `app.models`.

Legacy code and tests historically imported SQLAlchemy models from
`app.db.models`. After the large refactor these definitions live under
`app.models`. To avoid touching all historical imports we re-export the
relevant symbols here.
"""

from app.db.base_class import Base
from app.models.associations import product_categories
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.order import Order, OrderLine
from app.models.permission import Permission
from app.models.product import Product
from app.models.role import Role
from app.models.user import RefreshToken, User
from app.models.user_session import UserSession

__all__ = [
    "User",
    "RefreshToken",
    "Role",
    "Permission",
    "AuditLog",
    "UserSession",
    "Category",
    "Product",
    "Order",
    "OrderLine",
    "product_categories",
    "Base",
]
