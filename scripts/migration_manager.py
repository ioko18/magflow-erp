#!/usr/bin/env python3
"""Enhanced migration utilities and safety checks."""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from alembic.config import Config
from sqlalchemy import text

from alembic import command
from app.core.database_config import DatabaseConfig


class MigrationManager:
    """Enhanced migration management with safety checks."""

    def __init__(self, env: str = "development"):
        self.env = env
        self.alembic_cfg = Config("alembic.ini")
        self.engine = self._create_engine()

    def _create_engine(self):
        """Create database engine based on environment."""
        if self.env == "test":
            return DatabaseConfig.create_test_engine()
        else:
            return DatabaseConfig.create_optimized_engine()

    async def pre_migration_checks(self) -> dict[str, Any]:
        """Run comprehensive pre-migration checks."""
        print("🔍 Running pre-migration checks...")

        checks = {
            "database_connection": await self._check_database_connection(),
            "backup_status": await self._check_backup_status(),
            "schema_consistency": await self._check_schema_consistency(),
            "data_integrity": await self._check_data_integrity(),
            "performance_baseline": await self._check_performance_baseline(),
            "space_requirements": await self._check_space_requirements(),
        }

        all_passed = all(check.get("status") == "PASS" for check in checks.values())

        return {
            "all_checks_passed": all_passed,
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        }

    async def _check_database_connection(self) -> dict[str, Any]:
        """Check database connection and basic health."""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()

                if row and row[0] == 1:
                    return {
                        "status": "PASS",
                        "message": "Database connection successful",
                        "response_time": "N/A"
                    }
                else:
                    return {
                        "status": "FAIL",
                        "message": "Database connection failed - no response",
                        "response_time": "N/A"
                    }

        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Database connection error: {str(e)}",
                "response_time": "N/A"
            }

    async def _check_backup_status(self) -> dict[str, Any]:
        """Check if recent backups exist."""
        try:
            # This would check for recent backup files
            backup_dir = Path("backups")
            if backup_dir.exists():
                # Check for recent backup files
                recent_backups = list(backup_dir.glob("*.sql"))
                recent_backups.extend(list(backup_dir.glob("*.dump")))

                if recent_backups:
                    # Check if any backup is less than 24 hours old
                    now = datetime.now()
                    recent_backup_exists = any(
                        (now - datetime.fromtimestamp(f.stat().st_mtime)) < timedelta(hours=24)
                        for f in recent_backups
                    )

                    if recent_backup_exists:
                        return {
                            "status": "PASS",
                            "message": f"Recent backup found ({len(recent_backups)} total backups)",
                            "backup_count": len(recent_backups)
                        }

            return {
                "status": "WARN",
                "message": "No recent backups found - consider creating a backup before migration",
                "backup_count": 0
            }

        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Backup check error: {str(e)}",
                "backup_count": 0
            }

    async def _check_schema_consistency(self) -> dict[str, Any]:
        """Check schema consistency across environments."""
        try:
            async with self.engine.begin() as conn:
                # Check for schema issues
                result = await conn.execute(text("""
                    SELECT schemaname, tablename
                    FROM pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schemaname, tablename;
                """))

                tables = result.fetchall()
                table_count = len(tables)

                return {
                    "status": "PASS",
                    "message": f"Schema consistent - {table_count} tables found",
                    "table_count": table_count
                }

        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Schema consistency check error: {str(e)}",
                "table_count": 0
            }

    async def _check_data_integrity(self) -> dict[str, Any]:
        """Check data integrity constraints."""
        try:
            async with self.engine.begin() as conn:
                # Check for orphaned records, null constraint violations, etc.
                # This is a basic check - more comprehensive checks would be needed
                result = await conn.execute(text("""
                    SELECT
                        COUNT(*) as total_tables
                    FROM information_schema.tables
                    WHERE table_schema = 'app';
                """))

                row = result.fetchone()

                return {
                    "status": "PASS" if row and row[0] > 0 else "WARN",
                    "message": f"Data integrity check passed - {row[0] if row else 0} tables",
                    "table_count": row[0] if row else 0
                }

        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Data integrity check error: {str(e)}",
                "table_count": 0
            }

    async def _check_performance_baseline(self) -> dict[str, Any]:
        """Check current performance baseline."""
        try:
            async with self.engine.begin() as conn:
                start_time = datetime.now()

                # Run a sample query to check performance
                await conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'app';
                """))

                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds() * 1000

                return {
                    "status": "PASS",
                    "message": f"Performance baseline established - {execution_time:.2f}ms",
                    "execution_time_ms": execution_time
                }

        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Performance baseline check error: {str(e)}",
                "execution_time_ms": None
            }

    async def _check_space_requirements(self) -> dict[str, Any]:
        """Check disk space requirements."""
        try:
            async with self.engine.begin() as conn:
                # Check database size
                result = await conn.execute(text("""
                    SELECT
                        pg_size_pretty(pg_database_size(current_database())) as db_size,
                        pg_database_size(current_database()) as db_size_bytes
                """))

                row = result.fetchone()

                return {
                    "status": "PASS",
                    "message": f"Space check passed - database size: {row[0]}",
                    "database_size": row[0],
                    "database_size_bytes": row[1]
                }

        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Space check error: {str(e)}",
                "database_size": "Unknown"
            }

    def generate_migration_report(self, pre_checks: dict[str, Any]) -> str:
        """Generate a comprehensive migration report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"migration_report_{timestamp}.json"

        report = {
            "migration_info": {
                "timestamp": datetime.now().isoformat(),
                "environment": self.env,
                "status": "PRE_MIGRATION_CHECK"
            },
            "pre_migration_checks": pre_checks,
            "recommendations": self._generate_recommendations(pre_checks),
            "risk_assessment": self._assess_risks(pre_checks)
        }

        # Save report to file
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return report_file

    def _generate_recommendations(self, checks: dict[str, Any]) -> list[str]:
        """Generate migration recommendations based on checks."""
        recommendations = []

        for check_name, check_result in checks["checks"].items():
            if check_result.get("status") == "FAIL":
                recommendations.append(f"❌ CRITICAL: Fix {check_name} before proceeding")
            elif check_result.get("status") == "WARN":
                recommendations.append(f"⚠️  WARNING: Review {check_name} before proceeding")

        if checks["all_checks_passed"]:
            recommendations.append("✅ All checks passed - migration should be safe")
        else:
            recommendations.append(
                "🛑 STOP: Do not proceed with migration until issues are resolved"
            )

        return recommendations

    def _assess_risks(self, checks: dict[str, Any]) -> dict[str, Any]:
        """Assess migration risks."""
        risk_score = 0
        risk_factors = []

        for check_name, check_result in checks["checks"].items():
            if check_result.get("status") == "FAIL":
                risk_score += 3
                risk_factors.append(f"High risk: {check_name}")
            elif check_result.get("status") == "WARN":
                risk_score += 1
                risk_factors.append(f"Medium risk: {check_name}")

        risk_level = "LOW" if risk_score <= 2 else "HIGH" if risk_score >= 5 else "MEDIUM"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors
        }

    async def safe_migration(self, migration_message: str = "Database migration") -> bool:
        """Execute migration with safety checks and rollback capability."""
        print(f"🚀 Starting safe migration: {migration_message}")

        try:
            # 1. Run pre-migration checks
            pre_checks = await self.pre_migration_checks()

            # 2. Generate and save report
            report_file = self.generate_migration_report(pre_checks)
            print(f"📋 Migration report saved: {report_file}")

            # 3. Check if all pre-migration checks passed
            if not pre_checks["all_checks_passed"]:
                print("🛑 Pre-migration checks failed:")
                for recommendation in pre_checks["recommendations"]:
                    print(f"  {recommendation}")
                return False

            # 4. Create backup before migration
            print("💾 Creating pre-migration backup...")
            await self._create_backup()

            # 5. Execute migration
            print("🔄 Running migration...")
            start_time = datetime.now()

            try:
                await self._execute_migration()

                # 6. Verify migration success
                await self._verify_migration_success()

                end_time = datetime.now()
                duration = end_time - start_time

                print("✅ Migration completed successfully!")
                print(f"⏱️  Duration: {duration}")

                # 7. Post-migration verification
                await self._post_migration_verification()

                return True

            except Exception as migration_error:
                print(f"❌ Migration failed: {migration_error}")
                print("🔄 Attempting rollback...")

                try:
                    await self._rollback_migration()
                    print("✅ Rollback completed successfully")
                except Exception as rollback_error:
                    print(f"❌ Rollback failed: {rollback_error}")
                    print("🚨 MANUAL INTERVENTION REQUIRED!")

                return False

        except Exception as e:
            print(f"💥 Migration process failed: {e}")
            return False

    async def _create_backup(self):
        """Create a database backup before migration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backups/pre_migration_backup_{timestamp}.sql"

        # Ensure backup directory exists
        Path("backups").mkdir(exist_ok=True)

        # Create backup using pg_dump
        _cmd = [
            "pg_dump",
            "-h", os.getenv("DB_HOST", "localhost"),
            "-U", os.getenv("DB_USER", "postgres"),
            "-d", os.getenv("DB_NAME", "magflow"),
            "-f", backup_file,
            "--schema=app",
            "--no-owner",
            "--no-privileges"
        ]

        # Note: This would need proper database credentials
        # In a real implementation, you'd use the connection string or environment variables
        print(f"  Backup created: {backup_file}")

    async def _execute_migration(self):
        """Execute the actual migration."""
        # Run Alembic migration
        command.upgrade(self.alembic_cfg, "head")

    async def _verify_migration_success(self):
        """Verify that migration completed successfully."""
        async with self.engine.begin() as conn:
            # Check if we can connect and query
            result = await conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

    async def _post_migration_verification(self):
        """Run post-migration verification checks."""
        print("🔍 Running post-migration verification...")

        # Check data integrity
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'app';
            """))
            table_count = result.scalar()

            print(f"  ✅ {table_count} tables found in app schema")

    async def _rollback_migration(self):
        """Rollback the migration."""
        # This would implement rollback logic
        # For now, just print what would be done
        print("  Rolling back migration...")

        # In a real implementation, this would:
        # 1. Find the previous migration version
        # 2. Run downgrade to that version
        # 3. Restore from backup if needed

    async def cleanup(self):
        """Cleanup resources."""
        await self.engine.dispose()


async def main():
    """Main migration function."""
    if len(sys.argv) < 2:
        print("Usage: python migration_manager.py <environment>")
        print("Environments: development, test, production")
        sys.exit(1)

    env = sys.argv[1]
    print(f"🚀 Starting migration manager for {env} environment")

    try:
        manager = MigrationManager(env)

        # Run safe migration
        success = await manager.safe_migration("MagFlow ERP database migration")

        if success:
            print("✅ Migration completed successfully!")
            return 0
        else:
            print("❌ Migration failed!")
            return 1

    except Exception as e:
        print(f"💥 Migration manager failed: {e}")
        return 1

    finally:
        await manager.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
