"""
Migration Manager Service

Serviciu pentru managementul inteligent al migrărilor Alembic.
Oferă funcționalități de:
- Verificare sănătate migrări
- Detectare conflicte
- Backup automat
- Validare integritate schema
"""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MigrationHealthStatus:
    """Status de sănătate al migrărilor."""

    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MigrationManager:
    """Gestionează migrările și verifică integritatea."""

    def __init__(self, db: AsyncSession):
        """
        Inițializează Migration Manager.

        Args:
            db: Sesiune de bază de date
        """
        self.db = db
        self.alembic_dir = Path(__file__).parent.parent.parent / "alembic"
        self.versions_dir = self.alembic_dir / "versions"

    async def check_migration_health(self) -> dict:
        """
        Verifică starea de sănătate a migrărilor.

        Returns:
            Dict cu informații despre starea migrărilor
        """
        logger.info("Checking migration health...")

        try:
            # 1. Verifică versiunea curentă
            current_version = await self._get_current_version()

            # 2. Verifică migrări pending
            pending_migrations = await self._get_pending_migrations()

            # 3. Detectează conflicte
            conflicts = await self._detect_conflicts()

            # 4. Verifică fișiere duplicate
            duplicates = self._find_duplicate_migrations()

            # 5. Verifică integritatea schemei
            schema_issues = await self._verify_schema_integrity()

            # 6. Calculează scor de sănătate
            health_status = self._calculate_health_status(
                conflicts=conflicts,
                duplicates=duplicates,
                schema_issues=schema_issues,
                pending_count=len(pending_migrations),
            )

            result = {
                "status": health_status,
                "current_version": current_version,
                "pending_migrations": pending_migrations,
                "conflicts": conflicts,
                "duplicates": duplicates,
                "schema_issues": schema_issues,
                "total_migration_files": len(list(self.versions_dir.glob("*.py"))),
                "checked_at": datetime.now(UTC).isoformat(),
            }

            logger.info(f"Migration health check completed: {health_status}")
            return result

        except Exception as e:
            logger.error(f"Error checking migration health: {e}", exc_info=True)
            return {
                "status": MigrationHealthStatus.ERROR,
                "error": str(e),
                "checked_at": datetime.now(UTC).isoformat(),
            }

    async def _get_current_version(self) -> str | None:
        """Obține versiunea curentă a migrării."""
        try:
            result = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True,
                cwd=self.alembic_dir.parent,
            )

            if result.returncode == 0:
                # Parse output pentru a extrage versiunea
                output = result.stdout.strip()
                if output:
                    # Format: "revision_id (head)" sau "revision_id"
                    return output.split()[0] if output else None

            return None

        except Exception as e:
            logger.error(f"Error getting current version: {e}")
            return None

    async def _get_pending_migrations(self) -> list[str]:
        """Obține lista migrărilor pending."""
        try:
            # Verifică dacă există migrări care nu au fost aplicate
            result = subprocess.run(
                ["alembic", "heads"],
                capture_output=True,
                text=True,
                cwd=self.alembic_dir.parent,
            )

            if result.returncode == 0:
                heads = result.stdout.strip().split("\n")
                current = await self._get_current_version()

                # Dacă current nu este în heads, avem migrări pending
                if current and current not in " ".join(heads):
                    return heads

            return []

        except Exception as e:
            logger.error(f"Error getting pending migrations: {e}")
            return []

    async def _detect_conflicts(self) -> list[dict]:
        """
        Detectează conflicte în migrări.

        Returns:
            Listă de conflicte detectate
        """
        conflicts = []

        try:
            # Verifică pentru multiple heads (semn de conflict)
            result = subprocess.run(
                ["alembic", "heads"],
                capture_output=True,
                text=True,
                cwd=self.alembic_dir.parent,
            )

            if result.returncode == 0:
                heads = [
                    h.strip() for h in result.stdout.strip().split("\n") if h.strip()
                ]

                if len(heads) > 1:
                    conflicts.append(
                        {
                            "type": "multiple_heads",
                            "severity": "high",
                            "message": f"Multiple migration heads detected: {len(heads)}",
                            "heads": heads,
                        }
                    )

            # Verifică pentru fișiere de merge
            merge_files = list(self.versions_dir.glob("*merge*.py"))
            if merge_files:
                conflicts.append(
                    {
                        "type": "merge_files",
                        "severity": "medium",
                        "message": f"Found {len(merge_files)} merge migration files",
                        "files": [f.name for f in merge_files],
                    }
                )

            return conflicts

        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return []

    def _find_duplicate_migrations(self) -> list[dict]:
        """
        Găsește migrări duplicate sau similare.

        Returns:
            Listă de duplicate detectate
        """
        duplicates = []

        try:
            migration_files = list(self.versions_dir.glob("*.py"))

            # Grupează după nume similar (fără revision ID)
            name_groups = {}
            for file in migration_files:
                # Extrage numele fără revision ID
                parts = file.stem.split("_", 1)
                if len(parts) > 1:
                    name = parts[1]
                    if name not in name_groups:
                        name_groups[name] = []
                    name_groups[name].append(file.name)

            # Găsește grupuri cu mai multe fișiere
            for name, files in name_groups.items():
                if len(files) > 1:
                    duplicates.append(
                        {
                            "name": name,
                            "count": len(files),
                            "files": files,
                        }
                    )

            return duplicates

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}")
            return []

    async def _verify_schema_integrity(self) -> list[dict]:
        """
        Verifică integritatea schemei bazei de date.

        Returns:
            Listă de probleme detectate
        """
        issues = []

        try:
            # Verifică dacă tabelul alembic_version există
            query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = :schema
                    AND table_name = 'alembic_version'
                )
            """)

            result = await self.db.execute(query, {"schema": settings.db_schema_safe})
            exists = result.scalar()

            if not exists:
                issues.append(
                    {
                        "type": "missing_version_table",
                        "severity": "critical",
                        "message": "Alembic version table not found",
                    }
                )

            # Verifică pentru tabele orfane (fără foreign keys valide)
            # Verifică pentru index-uri lipsă
            # etc.

            return issues

        except Exception as e:
            logger.error(f"Error verifying schema integrity: {e}")
            return [
                {
                    "type": "verification_error",
                    "severity": "error",
                    "message": str(e),
                }
            ]

    def _calculate_health_status(
        self,
        conflicts: list[dict],
        duplicates: list[dict],
        schema_issues: list[dict],
        pending_count: int,
    ) -> str:
        """
        Calculează status-ul de sănătate bazat pe probleme detectate.

        Args:
            conflicts: Listă de conflicte
            duplicates: Listă de duplicate
            schema_issues: Listă de probleme schema
            pending_count: Număr de migrări pending

        Returns:
            Status de sănătate
        """
        # Critical: probleme de schema sau multiple heads
        if schema_issues:
            for issue in schema_issues:
                if issue.get("severity") == "critical":
                    return MigrationHealthStatus.CRITICAL

        if conflicts:
            for conflict in conflicts:
                if conflict.get("type") == "multiple_heads":
                    return MigrationHealthStatus.CRITICAL

        # Error: conflicte sau multe duplicate
        if len(conflicts) > 0 or len(duplicates) > 3:
            return MigrationHealthStatus.ERROR

        # Warning: duplicate sau pending migrations
        if len(duplicates) > 0 or pending_count > 0:
            return MigrationHealthStatus.WARNING

        # Healthy
        return MigrationHealthStatus.HEALTHY

    async def suggest_consolidation(self) -> list[dict]:
        """
        Sugerează migrări care pot fi consolidate.

        Returns:
            Listă de sugestii de consolidare
        """
        suggestions = []

        try:
            migration_files = list(self.versions_dir.glob("*.py"))

            # Grupează pe categorii
            categories = {
                "emag": [],
                "product": [],
                "order": [],
                "supplier": [],
                "notification": [],
                "user": [],
                "inventory": [],
                "other": [],
            }

            for file in migration_files:
                name_lower = file.stem.lower()
                categorized = False

                for category in categories:
                    if category in name_lower:
                        categories[category].append(file.name)
                        categorized = True
                        break

                if not categorized:
                    categories["other"].append(file.name)

            # Sugerează consolidare pentru categorii cu multe fișiere
            for category, files in categories.items():
                if len(files) > 3:
                    suggestions.append(
                        {
                            "category": category,
                            "file_count": len(files),
                            "files": files,
                            "suggestion": f"Consider consolidating {len(files)} {category} migrations into a single file",
                        }
                    )

            return suggestions

        except Exception as e:
            logger.error(f"Error suggesting consolidation: {e}")
            return []

    async def backup_before_migration(self) -> tuple[bool, str | None]:
        """
        Creează backup automat înainte de migrare.

        Returns:
            Tuple (success, backup_path)
        """
        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(__file__).parent.parent.parent / "backups"
            backup_dir.mkdir(exist_ok=True)

            backup_file = backup_dir / f"pre_migration_{timestamp}.sql"

            # Creează backup folosind pg_dump
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "magflow_db",
                    "pg_dump",
                    "-U",
                    settings.DB_USER,
                    "-d",
                    settings.DB_NAME,
                    "-f",
                    f"/tmp/backup_{timestamp}.sql",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Copiază backup-ul din container
                subprocess.run(
                    [
                        "docker",
                        "cp",
                        f"magflow_db:/tmp/backup_{timestamp}.sql",
                        str(backup_file),
                    ]
                )

                logger.info(f"Backup created successfully: {backup_file}")
                return True, str(backup_file)
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return False, None

        except Exception as e:
            logger.error(f"Error creating backup: {e}", exc_info=True)
            return False, None

    async def validate_migration_file(self, filepath: Path) -> list[dict]:
        """
        Validează un fișier de migrare pentru probleme comune.

        Args:
            filepath: Calea către fișierul de migrare

        Returns:
            Listă de probleme detectate
        """
        issues = []

        try:
            content = filepath.read_text()

            # Verifică pentru operații periculoase
            dangerous_ops = [
                ("DROP TABLE", "critical", "Contains DROP TABLE operation"),
                ("DROP COLUMN", "high", "Contains DROP COLUMN operation"),
                ("TRUNCATE", "high", "Contains TRUNCATE operation"),
            ]

            for op, severity, message in dangerous_ops:
                if op in content.upper():
                    issues.append(
                        {
                            "type": "dangerous_operation",
                            "severity": severity,
                            "operation": op,
                            "message": message,
                            "file": filepath.name,
                        }
                    )

            # Verifică pentru downgrade function
            if "def downgrade()" not in content:
                issues.append(
                    {
                        "type": "missing_downgrade",
                        "severity": "medium",
                        "message": "Missing downgrade function",
                        "file": filepath.name,
                    }
                )

            # Verifică pentru comentarii/documentare
            if '"""' not in content and "'''" not in content:
                issues.append(
                    {
                        "type": "missing_documentation",
                        "severity": "low",
                        "message": "Missing docstring",
                        "file": filepath.name,
                    }
                )

            return issues

        except Exception as e:
            logger.error(f"Error validating migration file: {e}")
            return [
                {
                    "type": "validation_error",
                    "severity": "error",
                    "message": str(e),
                    "file": filepath.name,
                }
            ]

    async def get_migration_statistics(self) -> dict:
        """
        Obține statistici despre migrări.

        Returns:
            Dict cu statistici
        """
        try:
            migration_files = list(self.versions_dir.glob("*.py"))

            # Exclude __pycache__ și __init__.py
            migration_files = [
                f for f in migration_files if not f.name.startswith("__")
            ]

            # Calculează statistici
            total_files = len(migration_files)
            merge_files = len([f for f in migration_files if "merge" in f.name.lower()])

            # Dimensiune totală
            total_size = sum(f.stat().st_size for f in migration_files)

            # Cele mai vechi și mai noi
            sorted_files = sorted(migration_files, key=lambda f: f.stat().st_mtime)
            oldest = sorted_files[0] if sorted_files else None
            newest = sorted_files[-1] if sorted_files else None

            return {
                "total_migrations": total_files,
                "merge_migrations": merge_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_migration": oldest.name if oldest else None,
                "newest_migration": newest.name if newest else None,
                "oldest_date": datetime.fromtimestamp(
                    oldest.stat().st_mtime
                ).isoformat()
                if oldest
                else None,
                "newest_date": datetime.fromtimestamp(
                    newest.stat().st_mtime
                ).isoformat()
                if newest
                else None,
            }

        except Exception as e:
            logger.error(f"Error getting migration statistics: {e}")
            return {}
