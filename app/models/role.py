"""Compatibility shim for Role model.

This module re-exports the canonical `Role` ORM class defined in
`app.db.models` to avoid duplicate SQLAlchemy table mappings that lead to
`InvalidRequestError: Table 'roles' is already defined` during tests.
"""

from app.db.models import Role as Role

__all__ = ["Role"]
