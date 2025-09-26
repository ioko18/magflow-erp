"""Test database connection directly using psycopg2."""
import logging
import sys

import psycopg2
from psycopg2.extras import DictCursor

# Reuse shared test configuration defaults
from tests.config import test_config as cfg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection():
    """Test database connection and basic queries."""
    conn = None
    try:
        # Connection parameters - connecting directly to PostgreSQL
        db_params = {
            'host': cfg.TEST_DB_HOST,
            'port': cfg.TEST_DB_PORT,
            'database': cfg.TEST_DB_NAME,
            'user': cfg.TEST_DB_USER,
            'password': cfg.TEST_DB_PASSWORD or None,
            'application_name': 'magflow-db-test',
            'connect_timeout': 5,  # 5 second connection timeout
        }

        logger.info(
            "Connecting to the PostgreSQL database %s@%s:%s/%s...",
            db_params['user'],
            db_params['host'],
            db_params['port'],
            db_params['database'],
        )
        conn = psycopg2.connect(**db_params, cursor_factory=DictCursor)
        
        # Create a cursor
        with conn.cursor() as cur:
            # Test connection
            cur.execute("SELECT 1")
            result = cur.fetchone()
            logger.info(f"✅ Database connection successful. Result: {result[0]}")
            
            # List tables in the app schema
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'app'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            logger.info(f"📋 Found {len(tables)} tables in 'app' schema: {', '.join(tables)}")
            
            # Count users
            cur.execute("SELECT COUNT(*) FROM app.users")
            user_count = cur.fetchone()[0]
            logger.info(f"👥 Found {user_count} users in the database")
            
            # List roles
            cur.execute("SELECT name, description FROM app.roles ORDER BY name")
            roles = [f"{row[0]} ({row[1]})" for row in cur.fetchall()]
            logger.info(f"🎭 Found roles: {', '.join(roles)}")
            
            # Get admin user
            cur.execute("""
                SELECT u.email, u.is_superuser, r.name as role 
                FROM app.users u
                LEFT JOIN app.user_roles ur ON u.id = ur.user_id
                LEFT JOIN app.roles r ON ur.role_id = r.id
                WHERE u.email = 'admin@example.com'
            """)
            admin_user = cur.fetchone()
            
            if admin_user:
                logger.info(f"🔑 Admin user: {admin_user['email']} (Superuser: {admin_user['is_superuser']}, Role: {admin_user['role'] or 'None'}")
                
                # Get the admin password hash
                cur.execute(
                    "SELECT hashed_password FROM app.users WHERE email = %s",
                    ('admin@example.com',)
                )
                hashed_pw = cur.fetchone()['hashed_password']
                logger.info(f"🔒 Admin password hash: {hashed_pw[:15]}...")
            else:
                logger.warning("❌ Admin user not found")
            
            # Check table structures
            logger.info("\n📊 Table Structures:")
            for table in tables:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'app' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                columns = [f"{row['column_name']} ({row['data_type']})" for row in cur.fetchall()]
                logger.info(f"  {table}: {', '.join(columns) or 'No columns found'}")
            
            return True
            
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
