"""Repository Pattern Implementation for MagFlow ERP.

This module provides repository classes that encapsulate data access logic,
providing a clean abstraction layer between business logic and database operations.
"""

import logging
from datetime import UTC, date, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependency_injection import DatabaseService, DatabaseServiceError
from app.db.models import AuditLog, Base, Product, User
from app.models.order import Order

# Type variables for generic repositories
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = logging.getLogger(__name__)


class RepositoryBase(Generic[ModelType]):
    """Base repository class providing common database operations."""

    def __init__(self, model_class: type[ModelType], db_service: DatabaseService):
        self.model_class = model_class
        self.db_service = db_service
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    async def get_session(self) -> AsyncSession:
        """Get database session from service."""
        return await self.db_service.get_session()

    async def get_by_id(self, id: int | str) -> ModelType | None:
        """Get entity by ID."""
        try:
            session = await self.get_session()
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(
                "Failed to get %s by ID %s: %s",
                self.model_class.__name__,
                id,
                e,
            )
            raise DatabaseServiceError(
                f"Failed to retrieve {self.model_class.__name__}",
            )

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Get all entities with pagination."""
        try:
            session = await self.get_session()
            stmt = select(self.model_class).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get all %s: %s", self.model_class.__name__, e)
            raise DatabaseServiceError(
                f"Failed to retrieve {self.model_class.__name__} list",
            )

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create new entity."""
        try:
            session = await self.get_session()
            stmt = insert(self.model_class).values(**data).returning(self.model_class)
            result = await session.execute(stmt)
            await session.commit()
            entity = result.scalar_one()
            self.logger.info(
                "Created %s with ID %s",
                self.model_class.__name__,
                entity.id,
            )
            return entity
        except Exception as e:
            await session.rollback()
            self.logger.error("Failed to create %s: %s", self.model_class.__name__, e)
            raise DatabaseServiceError(f"Failed to create {self.model_class.__name__}")

    async def update(
        self,
        id: int | str,
        data: dict[str, Any],
    ) -> ModelType | None:
        """Update existing entity."""
        try:
            session = await self.get_session()
            # Add updated_at timestamp if field exists
            if hasattr(self.model_class, "updated_at"):
                data["updated_at"] = datetime.now(UTC)

            stmt = (
                update(self.model_class)
                .where(self.model_class.id == id)
                .values(**data)
                .returning(self.model_class)
            )
            result = await session.execute(stmt)
            await session.commit()

            entity = result.scalar_one_or_none()
            if entity:
                self.logger.info("Updated %s with ID %s", self.model_class.__name__, id)
            return entity
        except Exception as e:
            await session.rollback()
            self.logger.error(
                "Failed to update %s with ID %s: %s",
                self.model_class.__name__,
                id,
                e,
            )
            raise DatabaseServiceError(f"Failed to update {self.model_class.__name__}")

    async def delete(self, id: int | str) -> bool:
        """Delete entity by ID."""
        try:
            session = await self.get_session()
            stmt = delete(self.model_class).where(self.model_class.id == id)
            result = await session.execute(stmt)
            await session.commit()

            deleted = result.rowcount > 0
            if deleted:
                self.logger.info("Deleted %s with ID %s", self.model_class.__name__, id)
            return deleted
        except Exception as e:
            await session.rollback()
            self.logger.error(
                "Failed to delete %s with ID %s: %s",
                self.model_class.__name__,
                id,
                e,
            )
            raise DatabaseServiceError(f"Failed to delete {self.model_class.__name__}")

    async def exists(self, id: int | str) -> bool:
        """Check if entity exists."""
        try:
            session = await self.get_session()
            stmt = (
                select(func.count())
                .select_from(self.model_class)
                .where(self.model_class.id == id)
            )
            result = await session.execute(stmt)
            return result.scalar() > 0
        except Exception as e:
            self.logger.error(
                "Failed to check existence of %s with ID %s: %s",
                self.model_class.__name__,
                id,
                e,
            )
            raise DatabaseServiceError(
                f"Failed to check {self.model_class.__name__} existence",
            )

    async def count(self, filters: dict[str, Any] = None) -> int:
        """Count entities with optional filters."""
        try:
            session = await self.get_session()
            stmt = select(func.count()).select_from(self.model_class)

            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        conditions.append(getattr(self.model_class, field) == value)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

            result = await session.execute(stmt)
            return result.scalar()
        except Exception as e:
            self.logger.error("Failed to count %s: %s", self.model_class.__name__, e)
            raise DatabaseServiceError(f"Failed to count {self.model_class.__name__}")


class UserRepository(RepositoryBase[User]):
    """Repository for user-related database operations."""

    def __init__(self, db_service: DatabaseService):
        super().__init__(User, db_service)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        try:
            session = await self.get_session()
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error("Failed to get user by email %s: %s", email, e)
            raise DatabaseServiceError("Failed to retrieve user by email")

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        try:
            session = await self.get_session()
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error("Failed to get user by username %s: %s", username, e)
            raise DatabaseServiceError("Failed to retrieve user by username")

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get active users with pagination."""
        try:
            session = await self.get_session()
            stmt = select(User).where(User.is_active).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get active users: %s", e)
            raise DatabaseServiceError("Failed to retrieve active users")

    async def get_users_by_role(
        self,
        role: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Get users by role."""
        try:
            session = await self.get_session()
            stmt = select(User).where(User.role == role).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get users by role %s: %s", role, e)
            raise DatabaseServiceError("Failed to retrieve users by role")

    async def search_users(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Search users by name or email."""
        try:
            session = await self.get_session()
            search_filter = f"%{search_term}%"
            stmt = (
                select(User)
                .where(
                    or_(
                        User.full_name.ilike(search_filter),
                        User.email.ilike(search_filter),
                    ),
                )
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to search users with term %s: %s", search_term, e)
            raise DatabaseServiceError("Failed to search users")


class ProductRepository(RepositoryBase[Product]):
    """Repository for product-related database operations."""

    def __init__(self, db_service: DatabaseService):
        super().__init__(Product, db_service)

    async def get_by_sku(self, sku: str) -> Product | None:
        """Get product by SKU."""
        try:
            session = await self.get_session()
            stmt = select(Product).where(Product.sku == sku)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error("Failed to get product by SKU %s: %s", sku, e)
            raise DatabaseServiceError("Failed to retrieve product by SKU")

    async def get_active_products(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Product]:
        """Get active products with pagination."""
        try:
            session = await self.get_session()
            stmt = select(Product).where(Product.is_active).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get active products: %s", e)
            raise DatabaseServiceError("Failed to retrieve active products")

    async def get_products_by_category(
        self,
        category_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Product]:
        """Get products by category."""
        try:
            session = await self.get_session()
            stmt = (
                select(Product)
                .where(Product.category_id == category_id)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(
                "Failed to get products by category %s: %s",
                category_id,
                e,
            )
            raise DatabaseServiceError("Failed to retrieve products by category")

    async def get_low_stock_products(self, threshold: int = 10) -> list[Product]:
        """Get products with low stock."""
        try:
            session = await self.get_session()
            stmt = select(Product).where(Product.stock_quantity <= threshold)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get low stock products: %s", e)
            raise DatabaseServiceError("Failed to retrieve low stock products")

    async def update_stock(
        self,
        product_id: int,
        quantity_change: int,
    ) -> Product | None:
        """Update product stock quantity."""
        try:
            # First get current product
            product = await self.get_by_id(product_id)
            if not product:
                return None

            new_quantity = max(0, product.stock_quantity + quantity_change)
            return await self.update(product_id, {"stock_quantity": new_quantity})
        except Exception as e:
            self.logger.error(
                "Failed to update stock for product %s: %s",
                product_id,
                e,
            )
            raise DatabaseServiceError("Failed to update product stock")


class OrderRepository(RepositoryBase[Order]):
    """Repository for order-related database operations."""

    def __init__(self, db_service: DatabaseService):
        super().__init__(Order, db_service)

    async def get_by_external_id(
        self,
        external_id: str,
        external_source: str,
    ) -> Order | None:
        """Get order by external identifier and source."""

        try:
            session = await self.get_session()
            stmt = select(Order).where(
                Order.external_id == external_id,
                Order.external_source == external_source,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(
                "Failed to get order by external_id=%s source=%s: %s",
                external_id,
                external_source,
                e,
            )
            raise DatabaseServiceError("Failed to retrieve order by external ID")

    async def upsert_by_external_id(
        self,
        external_id: str,
        external_source: str,
        create_data: dict[str, Any],
        update_data: dict[str, Any] | None = None,
    ) -> Order:
        """Create or update an order identified by external ID."""

        update_payload = update_data or {}
        update_payload.setdefault("external_id", external_id)
        update_payload.setdefault("external_source", external_source)

        try:
            session = await self.get_session()
            stmt = (
                select(Order)
                .where(
                    Order.external_id == external_id,
                    Order.external_source == external_source,
                )
                .with_for_update()
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                await session.execute(
                    update(Order)
                    .where(Order.id == existing.id)
                    .values(**update_payload)
                )
                await session.commit()
                await session.refresh(existing)
                return existing

            create_payload = dict(create_data)
            create_payload["external_id"] = external_id
            create_payload["external_source"] = external_source
            stmt_insert = insert(Order).values(**create_payload).returning(Order)
            inserted = await session.execute(stmt_insert)
            await session.commit()
            return inserted.scalar_one()

        except Exception as e:
            await session.rollback()
            self.logger.error(
                "Failed to upsert order external_id=%s source=%s: %s",
                external_id,
                external_source,
                e,
            )
            raise DatabaseServiceError("Failed to upsert order by external ID")

    async def get_by_customer_id(
        self,
        customer_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Order]:
        """Get orders by customer ID."""
        try:
            session = await self.get_session()
            stmt = (
                select(Order)
                .where(Order.customer_id == customer_id)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get orders by customer %s: %s", customer_id, e)
            raise DatabaseServiceError("Failed to retrieve orders by customer")

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Order]:
        """Get orders by status."""
        try:
            session = await self.get_session()
            stmt = select(Order).where(Order.status == status).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get orders by status %s: %s", status, e)
            raise DatabaseServiceError("Failed to retrieve orders by status")

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Order]:
        """Get orders within date range."""
        try:
            session = await self.get_session()
            stmt = (
                select(Order)
                .where(
                    and_(Order.order_date >= start_date, Order.order_date <= end_date),
                )
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(
                "Failed to get orders by date range %s to %s: %s",
                start_date,
                end_date,
                e,
            )
            raise DatabaseServiceError("Failed to retrieve orders by date range")

    async def get_order_total(self, order_id: int) -> float | None:
        """Calculate order total from order lines."""
        try:
            session = await self.get_session()
            # This assumes Order has a relationship with OrderLine
            # Implementation depends on your actual model structure
            stmt = select(func.sum(Order.total_amount)).where(Order.id == order_id)
            result = await session.execute(stmt)
            return result.scalar()
        except Exception as e:
            self.logger.error("Failed to get order total for order %s: %s", order_id, e)
            raise DatabaseServiceError("Failed to calculate order total")


class AuditLogRepository(RepositoryBase[AuditLog]):
    """Repository for audit log operations."""

    def __init__(self, db_service: DatabaseService):
        super().__init__(AuditLog, db_service)

    async def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs by user ID."""
        try:
            session = await self.get_session()
            stmt = (
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get audit logs by user %s: %s", user_id, e)
            raise DatabaseServiceError("Failed to retrieve audit logs by user")

    async def get_by_action(
        self,
        action: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs by action type."""
        try:
            session = await self.get_session()
            stmt = (
                select(AuditLog)
                .where(AuditLog.action == action)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get audit logs by action %s: %s", action, e)
            raise DatabaseServiceError("Failed to retrieve audit logs by action")

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs within date range."""
        try:
            session = await self.get_session()
            stmt = (
                select(AuditLog)
                .where(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.timestamp <= end_date,
                    ),
                )
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(
                "Failed to get audit logs by date range %s to %s: %s",
                start_date,
                end_date,
                e,
            )
            raise DatabaseServiceError("Failed to retrieve audit logs by date range")

    async def get_failed_logins(self, hours: int = 24) -> list[AuditLog]:
        """Get failed login attempts within specified hours."""
        try:
            session = await self.get_session()
            cutoff_time = datetime.now(UTC) - datetime.timedelta(hours=hours)
            stmt = select(AuditLog).where(
                and_(
                    AuditLog.action == "login_failed",
                    AuditLog.timestamp >= cutoff_time,
                ),
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error("Failed to get failed login attempts: %s", e)
            raise DatabaseServiceError("Failed to retrieve failed login attempts")


class RepositoryFactory:
    """Factory for creating repository instances."""

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self._repositories: dict[str, RepositoryBase] = {}

    def get_user_repository(self) -> UserRepository:
        """Get user repository instance."""
        if "user" not in self._repositories:
            self._repositories["user"] = UserRepository(self.db_service)
        return self._repositories["user"]

    def get_product_repository(self) -> ProductRepository:
        """Get product repository instance."""
        if "product" not in self._repositories:
            self._repositories["product"] = ProductRepository(self.db_service)
        return self._repositories["product"]

    def get_order_repository(self) -> OrderRepository:
        """Get order repository instance."""
        if "order" not in self._repositories:
            self._repositories["order"] = OrderRepository(self.db_service)
        return self._repositories["order"]

    def get_audit_log_repository(self) -> AuditLogRepository:
        """Get audit log repository instance."""
        if "audit_log" not in self._repositories:
            self._repositories["audit_log"] = AuditLogRepository(self.db_service)
        return self._repositories["audit_log"]
