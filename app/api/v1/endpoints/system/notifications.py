"""
Notifications API endpoints for MagFlow ERP.

Provides REST API endpoints for notification management including:
- Fetching user notifications
- Marking notifications as read
- Deleting notifications
- Managing notification settings
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.notification import (
    NotificationCategory,
    NotificationPriority,
    NotificationType,
)
from app.models.user import User
from app.services.system.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Pydantic schemas


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""

    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: NotificationType = NotificationType.INFO
    category: NotificationCategory = NotificationCategory.SYSTEM
    priority: NotificationPriority = NotificationPriority.MEDIUM
    data: dict | None = None
    action_url: str | None = Field(None, max_length=500)
    action_label: str | None = Field(None, max_length=100)


class NotificationResponse(BaseModel):
    """Schema for notification response."""

    id: int
    user_id: int
    type: str
    category: str
    priority: str
    title: str
    message: str
    data: dict | None
    action_url: str | None
    action_label: str | None
    read: bool
    read_at: str | None
    created_at: str
    expires_at: str | None

    class Config:
        from_attributes = True


class NotificationSettingsUpdate(BaseModel):
    """Schema for updating notification settings."""

    enabled: bool | None = None
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    sms_enabled: bool | None = None
    category_preferences: dict | None = None
    min_priority: NotificationPriority | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    auto_delete_enabled: bool | None = None
    auto_delete_days: int | None = Field(None, ge=1, le=365)
    digest_enabled: bool | None = None
    digest_frequency: str | None = Field(None, pattern=r"^(daily|weekly)$")


class NotificationSettingsResponse(BaseModel):
    """Schema for notification settings response."""

    id: int
    user_id: int
    enabled: bool
    email_enabled: bool
    push_enabled: bool
    sms_enabled: bool
    category_preferences: dict
    min_priority: str
    quiet_hours_enabled: bool
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    auto_delete_enabled: bool
    auto_delete_days: int
    digest_enabled: bool
    digest_frequency: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Endpoints


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    category: NotificationCategory | None = Query(
        None, description="Filter by category"
    ),
    priority: NotificationPriority | None = Query(
        None, description="Filter by priority"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notifications for the current user.

    - **unread_only**: Filter to show only unread notifications
    - **category**: Filter by notification category
    - **priority**: Filter by notification priority
    - **limit**: Maximum number of notifications to return
    - **offset**: Pagination offset
    """
    service = NotificationService(db)
    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        category=category,
        priority=priority,
        limit=limit,
        offset=offset,
    )

    return [NotificationResponse(**notif.to_dict()) for notif in notifications]


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications for the current user."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.get("/statistics")
async def get_notification_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification statistics for the current user."""
    service = NotificationService(db)
    stats = await service.get_statistics(current_user.id)
    return stats


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific notification by ID."""
    service = NotificationService(db)
    notification = await service.get_notification(notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this notification",
        )

    return NotificationResponse(**notification.to_dict())


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    service = NotificationService(db)
    success = await service.mark_as_read(notification_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or not authorized",
        )

    return {"message": "Notification marked as read", "success": True}


@router.post("/mark-all-read")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)

    return {
        "message": f"Marked {count} notifications as read",
        "count": count,
        "success": True,
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific notification."""
    service = NotificationService(db)
    success = await service.delete_notification(notification_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or not authorized",
        )

    return {"message": "Notification deleted", "success": True}


@router.delete("/")
async def delete_all_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all notifications for the current user."""
    service = NotificationService(db)
    count = await service.delete_all_notifications(current_user.id)

    return {
        "message": f"Deleted {count} notifications",
        "count": count,
        "success": True,
    }


# Notification Settings Endpoints


@router.get("/settings/me", response_model=NotificationSettingsResponse)
async def get_my_notification_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification settings for the current user."""
    service = NotificationService(db)
    settings = await service.get_user_settings(current_user.id)

    if not settings:
        # Create default settings if they don't exist
        settings = await service.create_default_settings(current_user.id)

    return NotificationSettingsResponse(**settings.to_dict())


@router.put("/settings/me", response_model=NotificationSettingsResponse)
async def update_my_notification_settings(
    settings_update: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification settings for the current user."""
    service = NotificationService(db)

    # Convert Pydantic model to dict, excluding None values
    update_data = settings_update.dict(exclude_none=True)

    settings = await service.update_settings(current_user.id, **update_data)

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification settings",
        )

    return NotificationSettingsResponse(**settings.to_dict())


@router.post("/settings/reset")
async def reset_notification_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset notification settings to defaults for the current user."""
    service = NotificationService(db)

    # Get existing settings
    existing_settings = await service.get_user_settings(current_user.id)

    if existing_settings:
        # Delete existing settings
        await db.delete(existing_settings)
        await db.commit()

    # Create new default settings
    settings = await service.create_default_settings(current_user.id)

    return {
        "message": "Notification settings reset to defaults",
        "settings": NotificationSettingsResponse(**settings.to_dict()),
        "success": True,
    }


# Admin endpoints (for creating notifications)


@router.post("/create", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    target_user_id: int | None = Query(
        None, description="Target user ID (admin only)"
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new notification.

    Regular users can only create notifications for themselves.
    Admins can create notifications for any user.
    """
    # Determine target user
    user_id = (
        target_user_id if target_user_id and current_user.is_admin else current_user.id
    )

    if target_user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create notifications for other users",
        )

    service = NotificationService(db)
    notification = await service.create_notification(
        user_id=user_id,
        title=notification_data.title,
        message=notification_data.message,
        type=notification_data.type,
        category=notification_data.category,
        priority=notification_data.priority,
        data=notification_data.data,
        action_url=notification_data.action_url,
        action_label=notification_data.action_label,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create notification (possibly blocked by user settings)",
        )

    return NotificationResponse(**notification.to_dict())


@router.post("/cleanup/old")
async def cleanup_old_notifications(
    days: int = Query(
        30, ge=1, le=365, description="Delete notifications older than this many days"
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Clean up old read notifications (admin only).

    - **days**: Delete notifications older than this many days
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform cleanup operations",
        )

    service = NotificationService(db)
    count = await service.cleanup_old_notifications(days)

    return {
        "message": f"Cleaned up {count} old notifications",
        "count": count,
        "success": True,
    }


@router.post("/cleanup/expired")
async def cleanup_expired_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Clean up expired notifications (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform cleanup operations",
        )

    service = NotificationService(db)
    count = await service.cleanup_expired_notifications()

    return {
        "message": f"Cleaned up {count} expired notifications",
        "count": count,
        "success": True,
    }
