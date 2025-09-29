"""Test database connection directly using psycopg2."""

import logging
import os
import subprocess
import sys
from pathlib import Path

from app.core.config import Settings

import psycopg2
from psycopg2 import errors
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection as PGConnection

# Reuse shared test configuration defaults
from tests.config import test_config as cfg

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _prepare_alembic_env() -> dict[str, str]:
    """Prepare environment variables for Alembic matching test DB settings."""
    overrides = {
        "DB_HOST": cfg.TEST_DB_HOST,
        "DB_PORT": str(cfg.TEST_DB_PORT),
        "DB_USER": cfg.TEST_DB_USER,
        "DB_PASS": cfg.TEST_DB_PASSWORD,
        "DB_NAME": cfg.TEST_DB_NAME,
        "DB_SCHEMA": cfg.TEST_DB_SCHEMA,
        "APP_ENV": "development",
    }
    env = {**os.environ, **overrides}
    settings = Settings(**overrides)
    env["DATABASE_URL"] = settings.DB_URI
    env["DB_URI"] = settings.alembic_url
    if "ALEMBIC_CONFIG" not in env:
        env["ALEMBIC_CONFIG"] = str(Path(__file__).resolve().parents[2] / "alembic.ini")
    return env


def _run_migrations() -> None:
    """Run Alembic migrations to ensure schema exists."""
    project_root = Path(__file__).resolve().parents[2]
    logger.info("⚙️  No tables detected in target schema; running migrations...")
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            cwd=str(project_root),
            env=_prepare_alembic_env(),
        )
        logger.info("✅ Alembic migrations completed successfully.")
    except FileNotFoundError:
        logger.error(
            "❌ Unable to locate the 'alembic' command. Install it or run 'pip install alembic'.",
        )
        raise
    except subprocess.CalledProcessError as exc:
        logger.error(
            "❌ Alembic migrations failed (exit code %s). Review migration output above.",
            exc.returncode,
        )
        raise


def _list_tables(conn: PGConnection) -> list[str]:
    """Return all table names in the configured schema."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (cfg.TEST_DB_SCHEMA,),
        )
        return [row[0] for row in cur.fetchall()]


def _has_only_alembic_table(tables: list[str]) -> bool:
    """Check whether the schema is populated only with the Alembic version table."""
    return bool(tables) and all(table.lower() == "alembic_version" for table in tables)


def _create_tables_fallback() -> None:
    """Run metadata-based table creation as a fallback when migrations yield no results."""
    project_root = Path(__file__).resolve().parents[2]
    logger.warning("⚠️  Running fallback metadata creation via create_tables.py...")
    env = _prepare_alembic_env()
    try:
        subprocess.run(
            [sys.executable, "create_tables.py"],
            check=True,
            cwd=str(project_root),
            env=env,
        )
        logger.info("✅ Fallback table creation completed successfully.")
    except subprocess.CalledProcessError as exc:
        logger.error(
            "❌ Fallback table creation failed (exit code %s). Review output above.",
            exc.returncode,
        )
        raise


def test_connection():
    """Test database connection and basic queries."""
    conn = None
    try:
        # Connection parameters - connecting directly to PostgreSQL
        db_params = {
            "host": cfg.TEST_DB_HOST,
            "port": cfg.TEST_DB_PORT,
            "database": cfg.TEST_DB_NAME,
            "user": cfg.TEST_DB_USER,
            "password": cfg.TEST_DB_PASSWORD or None,
            "application_name": "magflow-db-test",
            "connect_timeout": 5,  # 5 second connection timeout
        }

        logger.info(
            "Connecting to the PostgreSQL database %s@%s:%s/%s...",
            db_params["user"],
            db_params["host"],
            db_params["port"],
            db_params["database"],
        )
        conn = psycopg2.connect(**db_params, cursor_factory=DictCursor)

        with conn.cursor() as cur:
            # Test connection
            cur.execute("SELECT 1")
            result = cur.fetchone()
            logger.info(f"✅ Database connection successful. Result: {result[0]}")

        tables = _list_tables(conn)
        if tables:
            logger.info(
                "📋 Found %s tables in '%s' schema: %s",
                len(tables),
                cfg.TEST_DB_SCHEMA,
                ", ".join(tables),
            )
        else:
            logger.warning(
                "⚠️  No tables found in schema '%s'. Attempting to run migrations...",
                cfg.TEST_DB_SCHEMA,
            )

        if not tables or _has_only_alembic_table(tables):
            logger.warning(
                "⚠️  Schema '%s' appears uninitialised (tables: %s). Running migrations...",
                cfg.TEST_DB_SCHEMA,
                ", ".join(tables) if tables else "none",
            )
            conn.close()
            _run_migrations()
            conn = psycopg2.connect(**db_params, cursor_factory=DictCursor)
            tables = _list_tables(conn)
            if not tables or _has_only_alembic_table(tables):
                logger.warning(
                    "❌ Schema '%s' is still missing required tables after migrations. Attempting fallback creation...",
                    cfg.TEST_DB_SCHEMA,
                )
                conn.close()
                _create_tables_fallback()
                conn = psycopg2.connect(**db_params, cursor_factory=DictCursor)
                tables = _list_tables(conn)

            if tables and not _has_only_alembic_table(tables):
                logger.info(
                    "📋 Found %s tables in '%s' schema after setup: %s",
                    len(tables),
                    cfg.TEST_DB_SCHEMA,
                    ", ".join(tables),
                )
            else:
                logger.error(
                    "❌ Schema '%s' is still empty after all attempts. Ensure the database has been initialised.",
                    cfg.TEST_DB_SCHEMA,
                )
                return False

        lower_table_names = {t.lower() for t in tables}
        mandatory_tables = {"users", "roles", "user_roles"}
        missing_tables = mandatory_tables - lower_table_names
        if missing_tables:
            logger.error(
                "❌ Required tables missing after migrations: %s",
                ", ".join(sorted(missing_tables)),
            )
            return False

        with conn.cursor() as cur:
            # Count users
            cur.execute("SELECT COUNT(*) FROM app.users")
            user_count = cur.fetchone()[0]
            logger.info(f"👥 Found {user_count} users in the database")

            # List roles
            cur.execute("SELECT name, description FROM app.roles ORDER BY name")
            roles = [f"{row[0]} ({row[1]})" for row in cur.fetchall()]
            logger.info(f"🎭 Found roles: {', '.join(roles)}")

            # Get admin user
            cur.execute(
                """
                SELECT u.email, u.is_superuser, r.name as role
                FROM app.users u
                LEFT JOIN app.user_roles ur ON u.id = ur.user_id
                LEFT JOIN app.roles r ON ur.role_id = r.id
                WHERE u.email = 'admin@example.com'
                """
            )
            admin_user = cur.fetchone()

            if admin_user:
                logger.info(
                    "🔑 Admin user: %s (Superuser: %s, Role: %s)",
                    admin_user["email"],
                    admin_user["is_superuser"],
                    admin_user["role"] or "None",
                )

                # Get the admin password hash
                cur.execute(
                    "SELECT hashed_password FROM app.users WHERE email = %s",
                    ("admin@example.com",),
                )
                hashed_pw = cur.fetchone()["hashed_password"]
                logger.info(f"🔒 Admin password hash: {hashed_pw[:15]}...")
            else:
                logger.warning("❌ Admin user not found")

            # Check table structures
            logger.info("\n📊 Table Structures:")
            for table in tables:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'app' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table,),
                )
                columns = [
                    f"{row['column_name']} ({row['data_type']})"
                    for row in cur.fetchall()
                ]
                logger.info(f"  {table}: {', '.join(columns) or 'No columns found'}")

        return True

    except errors.UndefinedTable:
        logger.error(
            "❌ Required tables are missing. Run 'alembic upgrade head' or 'make db-migrate' to initialise the schema before rerunning.",
        )
        return False
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False
    finally:
        if conn is not None:
            conn.close()
            logger.info("Database connection closed.")


if __name__ == "__main__":
    logger.info("🚀 Starting database connection tests...\n")
    success = test_connection()

    if success:
        logger.info("\n✅ All database tests completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Database tests failed!")
        sys.exit(1)
