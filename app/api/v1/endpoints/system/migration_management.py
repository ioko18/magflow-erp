"""
Migration Management API Endpoints

Endpoints pentru managementul și monitorizarea migrărilor.
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session, require_admin_user
from app.core.logging_config import get_logger
from app.models.user import User
from app.services.system.migration_manager import MigrationManager

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=dict)
async def check_migration_health(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Verifică starea de sănătate a migrărilor.

    **Necesită:** Admin role

    **Returns:**
    - status: healthy/warning/error/critical
    - current_version: Versiunea curentă a migrării
    - pending_migrations: Listă de migrări pending
    - conflicts: Conflicte detectate
    - duplicates: Migrări duplicate
    - schema_issues: Probleme de integritate schema
    """
    try:
        manager = MigrationManager(db)
        health_info = await manager.check_migration_health()

        return health_info

    except Exception as e:
        logger.error(f"Error checking migration health: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check migration health: {str(e)}",
        ) from e


@router.get("/statistics", response_model=dict)
async def get_migration_statistics(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Obține statistici despre migrări.

    **Necesită:** Admin role

    **Returns:**
    - total_migrations: Număr total de fișiere de migrare
    - merge_migrations: Număr de migrări de merge
    - total_size_mb: Dimensiune totală în MB
    - oldest_migration: Cea mai veche migrare
    - newest_migration: Cea mai nouă migrare
    """
    try:
        manager = MigrationManager(db)
        stats = await manager.get_migration_statistics()

        return stats

    except Exception as e:
        logger.error(f"Error getting migration statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration statistics: {str(e)}",
        ) from e


@router.get("/suggestions", response_model=list[dict])
async def get_consolidation_suggestions(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Obține sugestii pentru consolidarea migrărilor.

    **Necesită:** Admin role

    **Returns:**
    Lista de sugestii de consolidare, fiecare conținând:
    - category: Categoria de migrări
    - file_count: Număr de fișiere în categorie
    - files: Lista fișierelor
    - suggestion: Sugestia de consolidare
    """
    try:
        manager = MigrationManager(db)
        suggestions = await manager.suggest_consolidation()

        return suggestions

    except Exception as e:
        logger.error(f"Error getting consolidation suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get consolidation suggestions: {str(e)}",
        ) from e


@router.post("/backup", response_model=dict)
async def create_migration_backup(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Creează un backup al bazei de date înainte de migrare.

    **Necesită:** Admin role

    **Returns:**
    - success: True/False
    - backup_path: Calea către fișierul de backup (dacă success=True)
    - message: Mesaj descriptiv
    """
    try:
        manager = MigrationManager(db)
        success, backup_path = await manager.backup_before_migration()

        if success:
            return {
                "success": True,
                "backup_path": backup_path,
                "message": "Backup created successfully",
            }
        else:
            return {
                "success": False,
                "backup_path": None,
                "message": "Failed to create backup",
            }

    except Exception as e:
        logger.error(f"Error creating migration backup: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}",
        ) from e


@router.get("/validate", response_model=dict)
async def validate_all_migrations(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Validează toate fișierele de migrare pentru probleme comune.

    **Necesită:** Admin role

    **Returns:**
    - total_files: Număr total de fișiere validate
    - files_with_issues: Număr de fișiere cu probleme
    - issues: Lista tuturor problemelor detectate
    """
    try:
        manager = MigrationManager(db)

        all_issues = []
        files_checked = 0
        files_with_issues = 0

        # Validează fiecare fișier de migrare
        for migration_file in manager.versions_dir.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            files_checked += 1
            issues = await manager.validate_migration_file(migration_file)

            if issues:
                files_with_issues += 1
                all_issues.extend(issues)

        return {
            "total_files": files_checked,
            "files_with_issues": files_with_issues,
            "issues": all_issues,
            "validation_passed": files_with_issues == 0,
        }

    except Exception as e:
        logger.error(f"Error validating migrations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate migrations: {str(e)}",
        ) from e


@router.get("/dashboard", response_model=dict)
async def get_migration_dashboard(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(require_admin_user),
):
    """
    Obține toate informațiile pentru dashboard-ul de migrări.

    **Necesită:** Admin role

    **Returns:**
    Combinație de health, statistics și suggestions pentru afișare în dashboard.
    """
    try:
        manager = MigrationManager(db)

        # Obține toate informațiile în paralel
        health = await manager.check_migration_health()
        stats = await manager.get_migration_statistics()
        suggestions = await manager.suggest_consolidation()

        return {
            "health": health,
            "statistics": stats,
            "suggestions": suggestions,
            "timestamp": health.get("checked_at"),
        }

    except Exception as e:
        logger.error(f"Error getting migration dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration dashboard: {str(e)}",
        ) from e
