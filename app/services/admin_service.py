"""Admin dashboard service for MagFlow ERP."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AuditLog, Permission, Role, User
from ..services.cache_service import CacheManager
from ..services.rbac_service import AuditService, RBACService

logger = logging.getLogger(__name__)


class AdminService:
    """Service for admin dashboard operations."""

    def __init__(self, db: AsyncSession):
        """Initialize admin service."""
        self.db = db
        self.rbac_service = RBACService(db)
        self.audit_service = AuditService(db)

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        try:
            # Get user statistics
            user_stats = await self.db.execute(
                select(
                    func.count(User.id).label("total_users"),
                    func.count(User.id).filter(User.is_active).label("active_users"),
                ),
            )
            user_counts = user_stats.fetchone()

            # Get product statistics (assuming products table exists)
            try:
                product_stats = await self.db.execute(
                    select(func.count(text("products.id")).label("total_products")),
                )
                product_count = product_stats.scalar() or 0
            except Exception:
                product_count = 0

            # Get order statistics (assuming orders table exists)
            try:
                order_stats = await self.db.execute(
                    select(func.count(text("orders.id")).label("total_orders")),
                )
                order_count = order_stats.scalar() or 0
            except Exception:
                order_count = 0

            # Get revenue (this would need to be calculated from actual order data)
            revenue = 0.0  # Placeholder

            # Calculate monthly growth (placeholder)
            monthly_growth = 12.5  # Placeholder

            # Get recent activities from audit logs
            recent_activities = await self.audit_service.get_audit_logs(limit=10)

            # Format activities for dashboard
            activities = []
            for log in recent_activities:
                user_email = "System"
                if log.user:
                    user_email = log.user.email

                activities.append(
                    {
                        "id": log.id,
                        "user": user_email,
                        "action": log.action,
                        "resource": log.resource,
                        "timestamp": log.timestamp.isoformat(),
                        "success": log.success,
                    },
                )

            # System health (simplified)
            system_health = "healthy"

            return {
                "total_users": user_counts.total_users,
                "active_users": user_counts.active_users,
                "total_products": product_count,
                "total_orders": order_count,
                "total_revenue": revenue,
                "monthly_growth": monthly_growth,
                "system_health": system_health,
                "recent_activities": activities,
            }

        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            # Return default values on error
            return {
                "total_users": 0,
                "active_users": 0,
                "total_products": 0,
                "total_orders": 0,
                "total_revenue": 0.0,
                "monthly_growth": 0.0,
                "system_health": "unknown",
                "recent_activities": [],
            }

    async def get_users_list(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> List[User]:
        """Get list of users for admin management."""
        try:
            query = select(User)

            if search:
                query = query.where(
                    User.email.contains(search) | User.full_name.contains(search),
                )

            query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting users list: {e}")
            return []

    async def get_user_details(self, user_id: int) -> Optional[User]:
        """Get detailed user information."""
        try:
            result = await self.db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting user details for {user_id}: {e}")
            return None

    async def create_user(
        self,
        user_data: Dict[str, Any],
        current_user: User,
    ) -> Optional[User]:
        """Create a new user."""
        try:
            # Check permissions
            await self.rbac_service.require_permission(current_user, "users", "write")

            # Hash password
            from ..api.auth import get_password_hash

            hashed_password = get_password_hash(user_data["password"])

            # Create user
            new_user = User(
                email=user_data["email"],
                hashed_password=hashed_password,
                full_name=user_data.get("full_name"),
                is_active=user_data.get("is_active", True),
                is_superuser=user_data.get("is_superuser", False),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            self.db.add(new_user)
            await self.db.flush()  # Get user ID

            # Assign roles if provided
            if "role_ids" in user_data:
                for role_id in user_data["role_ids"]:
                    role = await self.db.execute(select(Role).where(Role.id == role_id))
                    role_obj = role.scalar_one_or_none()
                    if role_obj:
                        new_user.roles.append(role_obj)

            await self.db.commit()

            # Send welcome email
            try:
                from ..services.email_service import NotificationManager

                notification_manager = NotificationManager(self.db)
                await notification_manager.notify_user_created(new_user)
            except Exception as e:
                logger.warning(f"Failed to send welcome email to {new_user.email}: {e}")
                # Don't fail user creation if email fails

            # Log admin action
            await self.audit_service.log_action(
                user=current_user,
                action="user_created",
                resource="users",
                resource_id=str(new_user.id),
                details={"email": new_user.email},
                success=True,
            )

            # Invalidate user cache
            cache_manager = CacheManager(self.db)
            await cache_manager.invalidate_user_cache(new_user.id)

            return new_user

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {e}")

            # Log failed action
            await self.audit_service.log_action(
                user=current_user,
                action="user_creation_failed",
                resource="users",
                details={"email": user_data.get("email", "unknown"), "error": str(e)},
                success=False,
            )

            return None

    async def update_user(
        self,
        user_id: int,
        update_data: Dict[str, Any],
        current_user: User,
    ) -> Optional[User]:
        """Update user information."""
        try:
            # Check permissions
            await self.rbac_service.require_permission(current_user, "users", "write")

            # Get user
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                return None

            # Update fields
            if "email" in update_data:
                user.email = update_data["email"]
            if "full_name" in update_data:
                user.full_name = update_data["full_name"]
            if "is_active" in update_data:
                user.is_active = update_data["is_active"]
            if "is_superuser" in update_data:
                user.is_superuser = update_data["is_superuser"]

            # Update roles if provided
            if "role_ids" in update_data:
                user.roles.clear()
                for role_id in update_data["role_ids"]:
                    role = await self.db.execute(select(Role).where(Role.id == role_id))
                    role_obj = role.scalar_one_or_none()
                    if role_obj:
                        user.roles.append(role_obj)

            user.updated_at = datetime.utcnow()
            await self.db.commit()

            # Log admin action
            await self.audit_service.log_action(
                user=current_user,
                action="user_updated",
                resource="users",
                resource_id=str(user_id),
                details={"updated_fields": list(update_data.keys())},
                success=True,
            )

            # Invalidate user cache
            cache_manager = CacheManager(self.db)
            await cache_manager.invalidate_user_cache(user_id)

            return user

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")

            # Log failed action
            await self.audit_service.log_action(
                user=current_user,
                action="user_update_failed",
                resource="users",
                resource_id=str(user_id),
                details={"error": str(e)},
                success=False,
            )

            return None

    async def delete_user(self, user_id: int, current_user: User) -> bool:
        """Delete a user."""
        try:
            # Check permissions
            await self.rbac_service.require_permission(current_user, "users", "delete")

            # Get user
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                return False

            # Check if trying to delete self
            if user.id == current_user.id:
                raise ValueError("Cannot delete your own account")

            # Store email for logging
            user_email = user.email

            await self.db.delete(user)
            await self.db.commit()

            # Log admin action
            await self.audit_service.log_action(
                user=current_user,
                action="user_deleted",
                resource="users",
                resource_id=str(user_id),
                details={"deleted_user": user_email},
                success=True,
            )

            # Invalidate user cache
            cache_manager = CacheManager(self.db)
            await cache_manager.invalidate_user_cache(user_id)

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")

            # Log failed action
            await self.audit_service.log_action(
                user=current_user,
                action="user_deletion_failed",
                resource="users",
                resource_id=str(user_id),
                details={"error": str(e)},
                success=False,
            )

            return False

    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        action: Optional[str] = None,
        user_id: Optional[int] = None,
        resource: Optional[str] = None,
    ) -> List[AuditLog]:
        """Get audit logs for admin review."""
        try:
            return await self.audit_service.get_audit_logs(
                action=action,
                resource=resource,
                user_id=user_id,
                limit=limit,
                offset=skip,
            )

        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        try:
            # Database health
            db_health = "healthy"
            try:
                result = await self.db.execute(select(func.count(User.id)))
                result.scalar()
            except Exception:
                db_health = "unhealthy"

            # Cache health
            cache_health = "healthy"
            try:
                cache_manager = CacheManager(self.db)
                await cache_manager.cache.get_cache_stats()
            except Exception:
                cache_health = "unhealthy"

            # API health
            api_health = "healthy"

            # Overall health
            issues = []
            if db_health != "healthy":
                issues.append("Database connection issues")
            if cache_health != "healthy":
                issues.append("Cache service issues")

            overall_health = (
                "healthy"
                if not issues
                else "degraded" if len(issues) == 1 else "unhealthy"
            )

            return {
                "status": overall_health,
                "database": db_health,
                "cache": cache_health,
                "api": api_health,
                "last_check": datetime.utcnow(),
                "issues": issues,
            }

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "unknown",
                "database": "unknown",
                "cache": "unknown",
                "api": "unknown",
                "last_check": datetime.utcnow(),
                "issues": ["Health check failed"],
            }

    async def get_roles_list(self, skip: int = 0, limit: int = 50) -> List[Role]:
        """Get list of roles."""
        try:
            result = await self.db.execute(
                select(Role).order_by(Role.name).offset(skip).limit(limit),
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting roles list: {e}")
            return []

    async def get_permissions_list(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Permission]:
        """Get list of permissions."""
        try:
            result = await self.db.execute(
                select(Permission)
                .order_by(Permission.resource, Permission.action)
                .offset(skip)
                .limit(limit),
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting permissions list: {e}")
            return []
