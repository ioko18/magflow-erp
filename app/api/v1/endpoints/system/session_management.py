"""
Session Management API Endpoints

Endpoints pentru managementul și monitorizarea sesiunilor utilizatorilor.
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session, require_admin_user
from app.core.logging_config import get_logger
from app.models.user import User
from app.services.system.session_tracking_service import SessionTrackingService

logger = get_logger(__name__)

router = APIRouter()


@router.get("/statistics", response_model=dict)
async def get_session_statistics(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Obține statistici despre sesiuni.

    **Necesită:** Admin role

    **Returns:**
    - active_sessions: Număr de sesiuni active
    - sessions_today: Sesiuni create astăzi
    - active_users_30min: Utilizatori activi în ultimele 30 minute
    """
    try:
        service = SessionTrackingService(db)
        stats = await service.get_session_statistics()

        return {"status": "success", "data": stats}

    except Exception as e:
        logger.error(f"Error getting session statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session statistics: {str(e)}",
        )


@router.get("/active-users", response_model=dict)
async def get_active_users(
    minutes: int = 30,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Obține numărul de utilizatori activi.

    **Necesită:** Admin role

    **Args:**
    - minutes: Interval de timp în minute (default: 30)

    **Returns:**
    - active_users: Număr de utilizatori activi
    """
    try:
        service = SessionTrackingService(db)
        count = await service.get_active_users_count(minutes)

        return {
            "status": "success",
            "data": {"active_users": count, "time_window_minutes": minutes},
        }

    except Exception as e:
        logger.error(f"Error getting active users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active users: {str(e)}",
        )


@router.get("/user/{user_id}/sessions", response_model=dict)
async def get_user_sessions(
    user_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Obține toate sesiunile active ale unui utilizator.

    **Necesită:** Admin role

    **Args:**
    - user_id: ID-ul utilizatorului

    **Returns:**
    Lista de sesiuni active
    """
    try:
        service = SessionTrackingService(db)
        sessions = await service.get_user_sessions(user_id)

        return {
            "status": "success",
            "data": {"user_id": user_id, "sessions": sessions, "total": len(sessions)},
        }

    except Exception as e:
        logger.error(f"Error getting user sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}",
        )


@router.delete("/session/{session_id}", response_model=dict)
async def invalidate_session(
    session_id: str,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Invalidează o sesiune de utilizator.

    **Necesită:** Admin role

    **Args:**
    - session_id: ID-ul sesiunii de invalidat

    **Returns:**
    - success: True dacă sesiunea a fost invalidată
    """
    try:
        service = SessionTrackingService(db)
        success = await service.invalidate_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return {
            "status": "success",
            "message": f"Session {session_id} invalidated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate session: {str(e)}",
        )


@router.post("/cleanup", response_model=dict)
async def cleanup_expired_sessions(
    hours: int = 24,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Curăță sesiunile expirate.

    **Necesită:** Admin role

    **Args:**
    - hours: Sesiunile mai vechi de atâtea ore sunt considerate expirate (default: 24)

    **Returns:**
    - cleaned_count: Număr de sesiuni curățate
    """
    try:
        service = SessionTrackingService(db)
        count = await service.cleanup_expired_sessions(hours)

        return {
            "status": "success",
            "data": {"cleaned_sessions": count, "hours_threshold": hours},
            "message": f"Cleaned up {count} expired sessions",
        }

    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup sessions: {str(e)}",
        )
