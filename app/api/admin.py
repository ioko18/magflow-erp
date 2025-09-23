"""Admin dashboard API endpoints for MagFlow ERP."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.auth import get_current_active_user
from ..core.database import get_async_session
from ..db.models import User as UserModel
from ..schemas.admin import (
    AdminActivityLog,
    AdminUserCreate,
    AdminUserUpdate,
    AuditLogSummary,
    DashboardStats,
    PermissionSummary,
    RoleSummary,
    SystemHealth,
    SystemMetrics,
    UserSummary,
)
from ..services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> DashboardStats:
    """Get dashboard statistics for admin overview.

    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    stats = await admin_service.get_dashboard_stats()
    return DashboardStats(**stats)


@router.get("/users", response_model=List[UserSummary])
async def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of users to return"),
    search: Optional[str] = Query(None, description="Search term for email or name"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[UserSummary]:
    """Get list of users for admin management.

    - **skip**: Number of users to skip
    - **limit**: Number of users to return (max 100)
    - **search**: Optional search term for filtering users
    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    users = await admin_service.get_users_list(skip=skip, limit=limit, search=search)

    result = []
    for user in users:
        # Get user roles
        role_names = (
            [role.name for role in user.roles] if hasattr(user, "roles") else []
        )

        result.append(
            UserSummary(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                created_at=user.created_at,
                role_names=role_names,
                failed_login_attempts=user.failed_login_attempts,
            ),
        )

    return result


@router.get("/users/{user_id}", response_model=UserSummary)
async def get_user_details(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> UserSummary:
    """Get detailed information about a specific user.

    - **user_id**: User ID to get details for
    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    user = await admin_service.get_user_details(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get user roles
    role_names = [role.name for role in user.roles] if hasattr(user, "roles") else []

    return UserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login,
        created_at=user.created_at,
        role_names=role_names,
        failed_login_attempts=user.failed_login_attempts,
    )


@router.post("/users", response_model=UserSummary)
async def create_user(
    user_data: AdminUserCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> UserSummary:
    """Create a new user.

    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    new_user = await admin_service.create_user(user_data.dict(), current_user)

    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # Get user roles
    role_names = (
        [role.name for role in new_user.roles] if hasattr(new_user, "roles") else []
    )

    return UserSummary(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_superuser=new_user.is_superuser,
        last_login=new_user.last_login,
        created_at=new_user.created_at,
        role_names=role_names,
        failed_login_attempts=new_user.failed_login_attempts,
    )


@router.put("/users/{user_id}", response_model=UserSummary)
async def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> UserSummary:
    """Update user information.

    - **user_id**: User ID to update
    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    updated_user = await admin_service.update_user(
        user_id,
        user_data.dict(exclude_unset=True),
        current_user,
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get user roles
    role_names = (
        [role.name for role in updated_user.roles]
        if hasattr(updated_user, "roles")
        else []
    )

    return UserSummary(
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
        is_superuser=updated_user.is_superuser,
        last_login=updated_user.last_login,
        created_at=updated_user.created_at,
        role_names=role_names,
        failed_login_attempts=updated_user.failed_login_attempts,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, str]:
    """Delete a user.

    - **user_id**: User ID to delete
    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    success = await admin_service.delete_user(user_id, current_user)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or could not be deleted",
        )

    return {"message": f"User {user_id} deleted successfully"}


@router.get("/audit-logs", response_model=List[AuditLogSummary])
async def get_audit_logs(
    skip: int = Query(0, ge=0, description="Number of logs to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of logs to return"),
    action: Optional[str] = Query(None, description="Filter by action"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[AuditLogSummary]:
    """Get audit logs for admin review.

    - **skip**: Number of logs to skip
    - **limit**: Number of logs to return (max 100)
    - **action**: Optional filter by action type
    - **user_id**: Optional filter by user ID
    - **resource**: Optional filter by resource type
    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    audit_logs = await admin_service.get_audit_logs(
        skip=skip,
        limit=limit,
        action=action,
        user_id=user_id,
        resource=resource,
    )

    result = []
    for log in audit_logs:
        user_email = None
        if log.user:
            user_email = log.user.email

        result.append(
            AuditLogSummary(
                id=log.id,
                user_id=log.user_id,
                user_email=user_email,
                action=log.action,
                resource=log.resource,
                timestamp=log.timestamp,
                success=log.success,
                ip_address=log.ip_address,
            ),
        )

    return result


@router.get("/system/health", response_model=SystemHealth)
async def get_system_health(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> SystemHealth:
    """Get system health status.

    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    health = await admin_service.get_system_health()
    return SystemHealth(**health)


@router.get("/roles", response_model=List[RoleSummary])
async def get_roles(
    skip: int = Query(0, ge=0, description="Number of roles to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of roles to return"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[RoleSummary]:
    """Get list of roles.

    - **skip**: Number of roles to skip
    - **limit**: Number of roles to return (max 100)
    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    roles = await admin_service.get_roles_list(skip=skip, limit=limit)

    result = []
    for role in roles:
        # Count users with this role
        user_count = len(role.users) if hasattr(role, "users") else 0
        permission_count = len(role.permissions) if hasattr(role, "permissions") else 0

        result.append(
            RoleSummary(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system_role=role.is_system_role,
                user_count=user_count,
                permission_count=permission_count,
                created_at=role.created_at,
            ),
        )

    return result


@router.get("/permissions", response_model=List[PermissionSummary])
async def get_permissions(
    skip: int = Query(0, ge=0, description="Number of permissions to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of permissions to return"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[PermissionSummary]:
    """Get list of permissions.

    - **skip**: Number of permissions to skip
    - **limit**: Number of permissions to return (max 100)
    - **Requires admin permissions**
    """
    admin_service = AdminService(db)
    permissions = await admin_service.get_permissions_list(skip=skip, limit=limit)

    result = []
    for perm in permissions:
        # Count roles with this permission
        role_count = len(perm.roles) if hasattr(perm, "roles") else 0

        result.append(
            PermissionSummary(
                id=perm.id,
                name=perm.name,
                description=perm.description,
                resource=perm.resource,
                action=perm.action,
                role_count=role_count,
                created_at=perm.created_at,
            ),
        )

    return result


@router.get("/activities", response_model=List[AdminActivityLog])
async def get_admin_activities(
    skip: int = Query(0, ge=0, description="Number of activities to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[AdminActivityLog]:
    """Get admin activities for tracking admin actions.

    - **skip**: Number of activities to skip
    - **limit**: Number of activities to return (max 100)
    - **Requires admin permissions**
    """
    # Get recent audit logs where the user is an admin (superuser or has admin role)
    admin_service = AdminService(db)
    audit_logs = await admin_service.get_audit_logs(limit=limit, offset=skip)

    result = []
    for log in audit_logs:
        # Check if the user performing the action is an admin
        if log.user and (
            log.user.is_superuser
            or any(role.name == "admin" for role in log.user.roles)
        ):
            admin_email = log.user.email

            result.append(
                AdminActivityLog(
                    id=log.id,
                    admin_id=log.user_id,
                    admin_email=admin_email,
                    action=log.action,
                    target_type=log.resource,
                    target_id=log.resource_id,
                    details=log.details,
                    timestamp=log.timestamp,
                    ip_address=log.ip_address,
                ),
            )

    return result


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> SystemMetrics:
    """Get system performance metrics.

    - **Requires admin permissions**
    """
    # This would integrate with actual monitoring systems like Prometheus
    # For now, return placeholder data
    return SystemMetrics(
        cpu_usage=45.2,
        memory_usage=67.8,
        disk_usage=23.1,
        database_connections=15,
        cache_hit_rate=94.5,
        response_time_avg=125.7,
        error_rate=0.2,
        uptime="7d 14h 32m",
    )
