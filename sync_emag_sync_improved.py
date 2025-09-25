#!/usr/bin/env python3
"""
Improved eMAG synchronization with async support and robust error handling
Enhancements:
- Robust DB connection via environment (PgBouncer aware)
- Hardened field mappings to avoid type/constraint errors
- Prometheus metrics for observability
- Fixed infinite loops and timeout issues
- Proper error recovery and status updates
- Maximum page limits and safety checks
"""

import aiohttp
import asyncio
import os
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import signal
import socket
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.warning("python-dotenv not installed. Environment variables may not be loaded from .env file.")

# Global variables - will be loaded when needed
EMAG_API_URL = None
EMAG_USER = None
EMAG_PASS = None
EMAG_ACCOUNT_TYPE = None
ACCOUNT_CREDENTIALS = {}
semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests per second

# Prometheus metrics
METRICS_PORT = int(os.getenv("EMAG_SYNC_METRICS_PORT", "9108"))
MAX_PAGES = int(os.getenv("EMAG_SYNC_MAX_PAGES", "100"))  # Maximum pages to fetch
SYNC_TIMEOUT_HOURS = int(os.getenv("EMAG_SYNC_TIMEOUT_HOURS", "2"))  # Maximum sync duration
SYNC_BATCH_SIZE = int(os.getenv("EMAG_SYNC_BATCH_SIZE", "50"))  # Batch size for database operations
PROGRESS_UPDATE_INTERVAL = int(os.getenv("EMAG_SYNC_PROGRESS_INTERVAL", "10"))  # Update progress every N offers

# Prometheus metrics
SYNC_REQUESTS = Counter(
    "emag_sync_requests_total",
    "Total eMAG API requests",
    ["endpoint", "account_type"]
)
SYNC_REQUEST_ERRORS = Counter(
    "emag_sync_request_errors_total",
    "Total eMAG API request errors",
    ["endpoint", "account_type", "reason"]
)
SYNC_LATENCY = Histogram(
    "emag_sync_request_latency_seconds",
    "Latency of eMAG API requests",
    ["endpoint", "account_type"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10)
)
SYNC_OFFERS_PROCESSED = Counter(
    "emag_sync_offers_processed_total",
    "Total offers processed",
    ["account_type"]
)
SYNC_RUN_STATUS = Gauge(
    "emag_sync_run_status",
    "Current sync run status (0=idle,1=running,2=completed,3=failed,4=timeout)",
    ["account_type"]
)
SYNC_LAST_SUCCESS = Gauge(
    "emag_sync_last_success_timestamp",
    "Timestamp of last successful sync",
    ["account_type"]
)
DB_CONNECTIONS_ACTIVE = Gauge(
    "emag_sync_db_connections_active",
    "Number of active database connections"
)

# Global sync state
current_sync_id = None
sync_start_time = None
shutdown_requested = False
OFFERS_METADATA_COLUMN = None
PRODUCTS_PART_NUMBER_KEY_COLUMN = None
OFFERS_PART_NUMBER_KEY_COLUMN = None


def _extract_part_number_key_from_url(url):
    """Extract part_number_key from eMAG product URL.
    
    Args:
        url (str): The eMAG product URL (e.g., for .../pd/D5DD9BBBM/ the part_number_key is D5DD9BBBM)
    
    Returns:
        str: The extracted part number key or empty string if not found
    """
    if not url or not isinstance(url, str):
        return ""
        
    try:
        # Split URL by '/' and get the last non-empty segment
        parts = [part for part in url.rstrip('/').split('/') if part.strip()]
        if not parts:
            return ""
            
        # The part number key is the last non-empty part
        part_number_key = parts[-1]
        
        # Basic validation - should contain both letters and numbers
        if part_number_key and any(c.isalpha() for c in part_number_key) and any(c.isdigit() for c in part_number_key):
            return part_number_key.upper()  # Convert to uppercase for consistency
            
        return ""
    except Exception as e:
        logger.warning(f"Error extracting part number key from URL '{url}': {str(e)}")
        return ""

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.warning(f"Received signal {signum}, requesting graceful shutdown...")
    shutdown_requested = True
    if current_sync_id:
        update_sync_status(current_sync_id, 'failed', error_message="Shutdown requested by signal")


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def load_credentials():
    """Load eMAG API credentials from environment variables"""
    global EMAG_API_URL, EMAG_USER, EMAG_PASS, EMAG_ACCOUNT_TYPE, ACCOUNT_CREDENTIALS

    EMAG_API_URL = os.getenv('EMAG_API_BASE_URL', 'https://marketplace-api.emag.ro/api-3')
    requested_account_type = (os.getenv('EMAG_ACCOUNT_TYPE', 'main') or 'main').strip().lower()

    # Load MAIN account credentials
    main_username = os.getenv('EMAG_API_USERNAME')
    main_password = os.getenv('EMAG_API_PASSWORD')

    # Load FBE account credentials
    fbe_username = os.getenv('EMAG_FBE_API_USERNAME')
    fbe_password = os.getenv('EMAG_FBE_API_PASSWORD')

    available_accounts = {}
    if main_username and main_password:
        available_accounts['main'] = (main_username, main_password)
    else:
        logger.debug("MAIN account credentials not fully configured")

    if fbe_username and fbe_password:
        available_accounts['fbe'] = (fbe_username, fbe_password)
    else:
        logger.debug("FBE account credentials not fully configured")

    if requested_account_type not in {'main', 'fbe', 'auto'}:
        raise ValueError(f"Invalid EMAG_ACCOUNT_TYPE: {requested_account_type}. Must be 'main', 'fbe', or 'auto'")

    selected_account_type = requested_account_type

    if requested_account_type == 'main':
        if 'main' not in available_accounts:
            raise ValueError("MAIN account credentials not found. Please set EMAG_API_USERNAME and EMAG_API_PASSWORD environment variables.")
    elif requested_account_type == 'fbe':
        if 'fbe' not in available_accounts:
            raise ValueError("FBE account credentials not found. Please set EMAG_FBE_API_USERNAME and EMAG_FBE_API_PASSWORD environment variables.")
    else:  # auto mode
        if 'main' in available_accounts:
            selected_account_type = 'main'
            logger.info("AUTO mode selected, using MAIN account credentials")
        elif 'fbe' in available_accounts:
            selected_account_type = 'fbe'
            logger.info("AUTO mode selected, MAIN missing -> using FBE account credentials")
        else:
            raise ValueError("No eMAG credentials configured. Provide MAIN or FBE credentials for AUTO mode.")

    EMAG_ACCOUNT_TYPE = selected_account_type
    EMAG_USER, EMAG_PASS = available_accounts[selected_account_type]
    ACCOUNT_CREDENTIALS = dict(available_accounts)

    logger.info(f"Loaded credentials for account type: {EMAG_ACCOUNT_TYPE.upper()}")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_emag_products(session, page=1, items_per_page=100):
    """Fetch eMAG products with retry and rate limiting"""
    async with semaphore:
        await asyncio.sleep(0.33)  # Approximate 3 req/s by sleeping 333ms per request
        url = f"{EMAG_API_URL}/product_offer/read"
        payload = {
            "data": {
                "currentPage": page,
                "itemsPerPage": items_per_page
            }
        }

        try:
            # Ensure credentials are loaded
            if EMAG_USER is None or EMAG_PASS is None:
                load_credentials()

            logger.info(f"Making API request to {url} with user: {EMAG_USER} (page {page})")
            SYNC_REQUESTS.labels(endpoint="product_offer/read", account_type=EMAG_ACCOUNT_TYPE).inc()

            with SYNC_LATENCY.labels(endpoint="product_offer/read", account_type=EMAG_ACCOUNT_TYPE).time():
                async with session.post(
                    url,
                    json=payload,
                    auth=aiohttp.BasicAuth(EMAG_USER, EMAG_PASS),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_text = await response.text()

            logger.info(f"API Response Status: {response.status} (page {page})")

            if response.status == 200:
                try:
                    data = await response.json()
                    logger.info(f"Successfully parsed JSON response for page {page}")

                    if data.get('isError', False):
                        messages = data.get('messages', [])
                        error_msg = messages[0] if messages else 'No error message provided'
                        logger.error(f"API returned error on page {page}: {error_msg}")
                        SYNC_REQUEST_ERRORS.labels(
                            endpoint="product_offer/read",
                            account_type=EMAG_ACCOUNT_TYPE,
                            reason="api_isError"
                        ).inc()
                        raise Exception(f"API error on page {page}: {error_msg}")
                    return data
                except Exception as json_error:
                    logger.error(f"Error parsing JSON response on page {page}: {json_error}")
                    logger.error(f"Response text: {response_text[:500]}...")
                    SYNC_REQUEST_ERRORS.labels(
                        endpoint="product_offer/read",
                        account_type=EMAG_ACCOUNT_TYPE,
                        reason="json_parse"
                    ).inc()
                    raise
            elif response.status == 429:
                logger.warning(f"Rate limit exceeded on page {page}. Retrying...")
                await asyncio.sleep(5)
                SYNC_REQUEST_ERRORS.labels(
                    endpoint="product_offer/read",
                    account_type=EMAG_ACCOUNT_TYPE,
                    reason="rate_limit"
                ).inc()
                raise Exception("Rate limit exceeded")
            else:
                logger.error(f"HTTP error {response.status} on page {page}: {response_text[:200]}")
                SYNC_REQUEST_ERRORS.labels(
                    endpoint="product_offer/read",
                    account_type=EMAG_ACCOUNT_TYPE,
                    reason=f"http_{response.status}"
                ).inc()
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Error fetching products on page {page}: {e}")
            raise

def _apply_db_host_override(db_url: str) -> str:
    """Override the database host when an explicit override is provided or when default hosts are unreachable"""
    if not db_url:
        return db_url

    try:
        from urllib.parse import urlparse, urlunparse
    except ImportError:
        return db_url

    try:
        parsed = urlparse(db_url)
    except Exception:
        return db_url

    if not parsed.hostname:
        return db_url

    host_override = os.getenv("EMAG_SYNC_DB_HOST_OVERRIDE")

    if not host_override:
        disable_auto = os.getenv("EMAG_SYNC_DISABLE_HOST_AUTO_OVERRIDE", "false").lower() in {"1", "true", "yes"}
        if disable_auto:
            return db_url

        default_hosts = {"db", "postgres", "pgbouncer"}
        if parsed.hostname in default_hosts:
            try:
                socket.getaddrinfo(parsed.hostname, parsed.port or 5432)
            except socket.gaierror:
                host_override = os.getenv("EMAG_SYNC_LOCAL_DB_HOST", "127.0.0.1")

    if not host_override:
        return db_url

    netloc = parsed.netloc
    if "@" in netloc:
        auth, host_port = netloc.split("@", 1)
        if ":" in host_port:
            _, port = host_port.rsplit(":", 1)
            host_port = f"{host_override}:{port}"
        else:
            host_port = host_override
        netloc = f"{auth}@{host_port}"
    else:
        if ":" in netloc:
            _, port = netloc.rsplit(":", 1)
            netloc = f"{host_override}:{port}"
        else:
            netloc = host_override

    updated = urlunparse(parsed._replace(netloc=netloc))
    logger.info(f"DB host override applied: {parsed.hostname} -> {host_override}")
    return updated


def _build_db_url_from_env() -> str:
    """Resolve DB URL with proper fallback hierarchy"""
    # 1) Explicit sync URL
    url = os.getenv("DATABASE_SYNC_URL")
    if url:
        return _apply_db_host_override(url)

    # 2) Fallback to general DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        # For async URLs (postgresql+asyncpg), convert to sync driver for SQLAlchemy engine here
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return _apply_db_host_override(url)

    # 3) Build from parts with PgBouncer defaults
    user = os.getenv("DB_USER", "app")
    password = os.getenv("DB_PASS", "app_password_change_me")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "6432"))  # PgBouncer published port
    name = os.getenv("DB_NAME", "postgres")   # PgBouncer routes to DB internally
    return _apply_db_host_override(f"postgresql://{user}:{password}@{host}:{port}/{name}")

# Global database engine for connection pooling
_db_engine = None

def get_db_engine():
    """Get or create database engine with connection pooling"""
    global _db_engine
    if _db_engine is None:
        db_url = _build_db_url_from_env()
        # Redact password for safe logging
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(db_url)
            if parsed.password:
                netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
                redacted = urlunparse(parsed._replace(netloc=netloc))
            else:
                redacted = db_url
            logger.info(f"DB connection URL resolved: {redacted}")
        except Exception:
            pass

        # Create engine with connection pooling and pre-ping
        _db_engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600
        )
        logger.info("Database engine created with connection pooling")
    return _db_engine

def get_db_session():
    """Create database session using connection pool"""
    try:
        engine = get_db_engine()
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        raise

@contextmanager
def get_db():
    """Database context manager with better error handling"""
    session = None
    try:
        session = get_db_session()
        DB_CONNECTIONS_ACTIVE.inc()
        yield session
        session.commit()
        logger.debug("Database transaction committed successfully")
    except Exception as e:
        if session:
            try:
                session.rollback()
                logger.debug("Database transaction rolled back due to error")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        logger.error(f"Database error: {e}")
        raise
    finally:
        if session:
            try:
                session.close()
                DB_CONNECTIONS_ACTIVE.dec()
                logger.debug("Database session closed")
            except Exception as close_error:
                logger.error(f"Error closing database session: {close_error}")

def update_sync_status(sync_id, status, offers_processed=0, error_message=None):
    """Update sync status in database"""
    try:
        with get_db() as session:
            if error_message:
                session.execute(text("""
                    UPDATE app.emag_offer_syncs
                    SET status = :status,
                        total_offers_processed = :processed,
                        error_count = error_count + 1,
                        errors = COALESCE(errors, '[]'::jsonb) || jsonb_build_array(CAST(:error_message AS text)),
                        updated_at = NOW()
                    WHERE sync_id = :sync_id
                """), {
                    "sync_id": sync_id,
                    "status": status,
                    "processed": offers_processed,
                    "error_message": error_message
                })
            else:
                session.execute(text("""
                    UPDATE app.emag_offer_syncs
                    SET status = :status,
                        total_offers_processed = :processed,
                        updated_at = NOW()
                    WHERE sync_id = :sync_id
                """), {
                    "sync_id": sync_id,
                    "status": status,
                    "processed": offers_processed
                })
            logger.debug(f"Updated sync {sync_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update sync status for {sync_id}: {e}")


def check_table_columns_exist():
    """Check if required columns exist in the database tables and add them if missing"""
    global PRODUCTS_PART_NUMBER_KEY_COLUMN, OFFERS_PART_NUMBER_KEY_COLUMN

    if PRODUCTS_PART_NUMBER_KEY_COLUMN is not None and OFFERS_PART_NUMBER_KEY_COLUMN is not None:
        return PRODUCTS_PART_NUMBER_KEY_COLUMN and OFFERS_PART_NUMBER_KEY_COLUMN

    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            # Check and add part_number_key to emag_products if it doesn't exist
            result = connection.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = :table AND column_name = :column
            """), {"schema": "app", "table": "emag_products", "column": "part_number_key"})
            PRODUCTS_PART_NUMBER_KEY_COLUMN = result.fetchone() is not None
            
            if not PRODUCTS_PART_NUMBER_KEY_COLUMN:
                logger.info("Adding part_number_key column to emag_products table")
                connection.execute(text("""
                    ALTER TABLE app.emag_products 
                    ADD COLUMN IF NOT EXISTS part_number_key VARCHAR(100)
                """))
                connection.commit()
                PRODUCTS_PART_NUMBER_KEY_COLUMN = True

            # Check and add part_number_key to emag_product_offers if it doesn't exist
            result = connection.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = :table AND column_name = :column
            """), {"schema": "app", "table": "emag_product_offers", "column": "part_number_key"})
            OFFERS_PART_NUMBER_KEY_COLUMN = result.fetchone() is not None
            
            if not OFFERS_PART_NUMBER_KEY_COLUMN:
                logger.info("Adding part_number_key column to emag_product_offers table")
                connection.execute(text("""
                    ALTER TABLE app.emag_product_offers 
                    ADD COLUMN IF NOT EXISTS part_number_key VARCHAR(100)
                """))
                connection.commit()
                OFFERS_PART_NUMBER_KEY_COLUMN = True

        logger.info(f"Database schema check: products.part_number_key={PRODUCTS_PART_NUMBER_KEY_COLUMN}, offers.part_number_key={OFFERS_PART_NUMBER_KEY_COLUMN}")
        return True

    except Exception as e:
        logger.error(f"Error checking/updating table columns: {e}")
        logger.exception("Error details:")
        PRODUCTS_PART_NUMBER_KEY_COLUMN = False
        OFFERS_PART_NUMBER_KEY_COLUMN = False
        return False

def get_offers_metadata_column():
    """Determine the metadata column name for app.emag_product_offers"""
    global OFFERS_METADATA_COLUMN
    if OFFERS_METADATA_COLUMN:
        return OFFERS_METADATA_COLUMN

    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = :table
            """), {"schema": "app", "table": "emag_product_offers"})
            columns = {row[0] for row in result}
        if 'metadata_payload' in columns:
            OFFERS_METADATA_COLUMN = 'metadata_payload'
        else:
            # Add the metadata_payload column if it doesn't exist
            try:
                connection.execute(text("""
                    ALTER TABLE app.emag_product_offers ADD COLUMN IF NOT EXISTS metadata_payload JSONB
                """))
                logger.info("Added metadata_payload column to app.emag_product_offers")
                OFFERS_METADATA_COLUMN = 'metadata_payload'
            except Exception as alter_e:
                logger.warning(f"Could not add metadata_payload column: {alter_e}; skipping metadata payload")
                OFFERS_METADATA_COLUMN = None
    except Exception as e:
        OFFERS_METADATA_COLUMN = None
        logger.error(f"Could not determine metadata column for offers table: {e}")

    logger.debug(f"Using offers metadata column: {OFFERS_METADATA_COLUMN}")
    return OFFERS_METADATA_COLUMN

def check_sync_timeout():
    """Check if sync has exceeded timeout limit"""
    if sync_start_time and _now_utc() - sync_start_time > timedelta(hours=SYNC_TIMEOUT_HOURS):
        logger.warning(f"Sync timeout exceeded ({SYNC_TIMEOUT_HOURS} hours)")
        return True
    return False

async def sync_emag_offers_for_account(account_type, account_credentials):
    """Sync eMAG offers for a specific account type"""
    global current_sync_id, sync_start_time, shutdown_requested
    
    logger.info(f"🔐 Starting eMAG synchronization for {account_type.upper()} account...")
    
    # Set credentials for this account
    global EMAG_USER, EMAG_PASS, EMAG_ACCOUNT_TYPE
    EMAG_USER, EMAG_PASS = account_credentials
    EMAG_ACCOUNT_TYPE = account_type

    # Create sync record for this account
    sync_id = f"sync-{account_type}-{_now_utc().strftime('%H%M%S')}"
    
    try:
        with get_db() as session:
            session.execute(text("""
               INSERT INTO app.emag_offer_syncs
               (sync_id, account_type, operation_type, status, started_at, 
                total_offers_processed, offers_created, offers_updated, 
                offers_failed, offers_skipped, error_count, errors, filters)
               VALUES (
                   :sync_id, :account_type, 'full_import', 'running', :started_at,
                   0, 0, 0, 0, 0, 0, '[]'::jsonb, '{}'::jsonb
               )
            """), {"sync_id": sync_id, "account_type": account_type, "started_at": _now_utc()})

            logger.info(f"Sync record created for {account_type}: {sync_id}")
            SYNC_RUN_STATUS.labels(account_type).set(1)
    except Exception as e:
        logger.error(f"Error creating sync record for {account_type}: {e}")
        SYNC_RUN_STATUS.labels(account_type).set(3)
        raise

    sync_failed = False
    total_processed = 0

    try:
        async with aiohttp.ClientSession() as session:
            page = 1
            last_progress_update = 0

            while True:
                # Check for shutdown request
                if shutdown_requested:
                    logger.warning(f"Shutdown requested for {account_type}, stopping sync gracefully...")
                    update_sync_status(sync_id, 'failed', total_processed, "Shutdown requested")
                    SYNC_RUN_STATUS.labels(account_type).set(3)
                    sync_failed = True
                    break

                # Check for timeout
                if check_sync_timeout():
                    logger.warning(f"Sync timeout exceeded for {account_type}, stopping gracefully...")
                    update_sync_status(sync_id, 'failed', total_processed, f"Timeout after {SYNC_TIMEOUT_HOURS} hours")
                    SYNC_RUN_STATUS.labels(account_type).set(4)
                    sync_failed = True
                    break

                # Check maximum pages limit
                if page > MAX_PAGES:
                    logger.warning(f"Maximum pages limit reached ({MAX_PAGES}) for {account_type}, stopping sync...")
                    update_sync_status(sync_id, 'completed', total_processed, f"Maximum pages limit reached ({MAX_PAGES})")
                    SYNC_RUN_STATUS.labels(account_type).set(2)
                    break

                try:
                    logger.info(f"[{account_type.upper()}] Fetching page {page}/{MAX_PAGES}...")
                    data = await fetch_emag_products(session, page)

                    if not data or not data.get('results'):
                        logger.info(f"🔚 [{account_type.upper()}] No more results found, sync completed successfully")
                        update_sync_status(sync_id, 'completed', total_processed)
                        SYNC_RUN_STATUS.labels(account_type).set(2)
                        SYNC_LAST_SUCCESS.labels(account_type).set_to_current_time()
                        break

                    page_offers = len(data.get('results', []))
                    logger.info(f"📦 [{account_type.upper()}] Processing {page_offers} offers from page {page}")

                    # Process offers in batches with improved error handling
                    processed_in_page = await process_offers_batch(data['results'], sync_id)

                    total_processed += processed_in_page
                    last_progress_update += processed_in_page

                    # Update progress periodically
                    if last_progress_update >= PROGRESS_UPDATE_INTERVAL:
                        update_sync_status(sync_id, 'running', total_processed)
                        last_progress_update = 0
                        logger.info(f"📊 [{account_type.upper()}] Progress update: {total_processed} offers processed so far")

                    # Increment page for next iteration
                    page += 1
                    await asyncio.sleep(1)  # Rate limiting between pages

                except Exception as e:
                    logger.error(f"Error processing page {page} for {account_type}: {e}")
                    SYNC_REQUEST_ERRORS.labels(endpoint="product_offer/read", account_type=account_type, reason=str(e)[:50]).inc()
                    
                    # Continue to next page on error, but log it
                    page += 1
                    if page > MAX_PAGES:
                        break

    except Exception as e:
        logger.error(f"Critical error in {account_type} sync: {e}")
        update_sync_status(sync_id, 'failed', total_processed, str(e))
        SYNC_RUN_STATUS.labels(account_type).set(3)
        sync_failed = True

    logger.info(f"✅ [{account_type.upper()}] Sync completed. Total processed: {total_processed}")
    return {"account_type": account_type, "total_processed": total_processed, "sync_failed": sync_failed, "sync_id": sync_id}


async def sync_emag_offers():
    """Sync eMAG offers to database with improved error handling and safety limits"""
    global current_sync_id, sync_start_time, shutdown_requested

    logger.info("🔐 Starting eMAG synchronization...")

    # Check database schema (but don't fail if columns are missing)
    check_table_columns_exist()

    # Load and validate credentials
    load_credentials()

    # Start Prometheus metrics server (idempotent per process)
    try:
        start_http_server(METRICS_PORT)
        logger.info(f"📈 Prometheus metrics server started on :{METRICS_PORT}")
    except OSError:
        # Already started in this process
        pass

    # Reset sync state
    current_sync_id = None
    sync_start_time = _now_utc()
    shutdown_requested = False

    # Create sync record
    sync_id = f"sync-{_now_utc().strftime('%H%M%S')}"
    current_sync_id = sync_id

    try:
        with get_db() as session:
            session.execute(text("""
                INSERT INTO app.emag_offer_syncs
                (sync_id, account_type, operation_type, status, started_at, 
                 total_offers_processed, offers_created, offers_updated, 
                 offers_failed, offers_skipped, error_count, errors, filters)
                VALUES (
                    :sync_id, :account_type, 'full_import', 'running', :started_at,
                    0, 0, 0, 0, 0, 0, '[]'::jsonb, '{}'::jsonb
                )
            """), {"sync_id": sync_id, "account_type": EMAG_ACCOUNT_TYPE, "started_at": _now_utc()})

            logger.info(f"Sync record created: {sync_id}")
            # Metrics: mark run as running
            SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(1)
    except Exception as e:
        logger.error(f"Error creating sync record: {e}")
        SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(3)
        raise

    sync_failed = False

    try:
        async with aiohttp.ClientSession() as session:
            page = 1
            total_processed = 0
            last_progress_update = 0

            while True:
                # Check for shutdown request
                if shutdown_requested:
                    logger.warning("Shutdown requested, stopping sync gracefully...")
                    update_sync_status(sync_id, 'failed', total_processed, "Shutdown requested")
                    SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(3)
                    sync_failed = True
                    break

                # Check for timeout
                if check_sync_timeout():
                    logger.warning("Sync timeout exceeded, stopping gracefully...")
                    update_sync_status(sync_id, 'failed', total_processed, f"Timeout after {SYNC_TIMEOUT_HOURS} hours")
                    SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(4)
                    sync_failed = True
                    break

                # Check maximum pages limit
                if page > MAX_PAGES:
                    logger.warning(f"Maximum pages limit reached ({MAX_PAGES}), stopping sync...")
                    update_sync_status(sync_id, 'completed', total_processed, f"Maximum pages limit reached ({MAX_PAGES})")
                    SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(2)
                    break

                try:
                    logger.info(f"Fetching page {page}/{MAX_PAGES}...")
                    data = await fetch_emag_products(session, page)

                    if not data or not data.get('results'):
                        logger.info("🔚 No more results found, sync completed successfully")
                        update_sync_status(sync_id, 'completed', total_processed)
                        SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(2)
                        SYNC_LAST_SUCCESS.labels(EMAG_ACCOUNT_TYPE).set_to_current_time()
                        break

                    page_offers = len(data.get('results', []))
                    logger.info(f"📦 Processing {page_offers} offers from page {page}")

                    # Process offers in batches with improved error handling
                    processed_in_page = await process_offers_batch(data['results'], sync_id)

                    total_processed += processed_in_page
                    last_progress_update += processed_in_page

                    # Update progress periodically
                    if last_progress_update >= PROGRESS_UPDATE_INTERVAL:
                        update_sync_status(sync_id, 'running', total_processed)
                        last_progress_update = 0
                        logger.info(f"📊 Progress update: {total_processed} offers processed so far")

                    page += 1
                    await asyncio.sleep(1)  # Respect rate limits

                except Exception as e:
                    logger.error(f"Failed to process page {page}: {e}")
                    update_sync_status(sync_id, 'failed', total_processed, f"Error on page {page}: {str(e)}")
                    SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(3)
                    sync_failed = True
                    break

            # Final sync record update
            if not sync_failed:
                try:
                    with get_db() as final_db:
                        final_db.execute(text("""
                            UPDATE app.emag_offer_syncs
                            SET status = 'completed',
                                completed_at = :completed_at,
                                updated_at = NOW()
                            WHERE sync_id = :sync_id
                        """), {
                            "sync_id": sync_id,
                            "completed_at": _now_utc()
                        })

                    SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(2)
                    SYNC_LAST_SUCCESS.labels(EMAG_ACCOUNT_TYPE).set_to_current_time()
                    logger.info(f"✅ Successfully synced {total_processed} offers to database!")
                except Exception as final_error:
                    logger.error(f"Error updating final sync record: {final_error}")

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        try:
            update_sync_status(sync_id, 'failed', error_message=str(e))
            SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(3)
        except Exception as update_error:
            logger.error(f"Error updating sync record: {update_error}")
        raise

async def process_offers_batch(offers, sync_id):
    """Process a batch of offers with improved error handling"""
    if not offers:
        logger.info("No offers to process in this batch")
        return 0

    logger.info(f"Starting to process batch of {len(offers)} offers")
    processed = 0
    products_batch = []
    offers_batch = []
    batch_errors = 0
    metadata_column = get_offers_metadata_column()
    columns_exist = check_table_columns_exist()
    logger.info(f"Metadata column: {metadata_column}, Columns exist: {columns_exist}")

    for offer in offers:
        try:
            # Extract and validate offer data
            offer_id = str(offer.get('id', ''))
            if not offer_id:
                logger.warning(f"Skipping offer without ID: {offer}")
                continue

            # Defensive data extraction helpers
            def _safe_str(val, max_len=None):
                if val is None:
                    return ""
                s = str(val)
                return s[:max_len] if max_len else s

            def _safe_float(val):
                try:
                    if val is None or val == "":
                        return None
                    return float(val)
                except Exception:
                    return None

            def _safe_int(val):
                try:
                    if val is None or val == "":
                        return None
                    return int(val)
                except Exception:
                    return None

            def _status_text(ov):
                if isinstance(ov, dict):
                    return _safe_str(ov.get("description", ""), 100)
                return _safe_str(ov, 100)

            # Build product data with only the fields that exist in the database
            product_data = {
                "emag_id": offer_id,
                "name": _safe_str(offer.get("name", ""), 500),
                "description": _safe_str(offer.get("description", "")),
                "part_number": _safe_str(offer.get("part_number", ""), 100),
                "emag_category_id": _safe_int(offer.get("category_id")),
                "emag_brand_id": _safe_int(offer.get("brand_id")),
                "emag_category_name": _safe_str(offer.get("category_name"), 255),
                "emag_brand_name": _safe_str(offer.get("brand_name"), 255),
                "characteristics": json.dumps(offer.get("characteristics", [])),
                "images": json.dumps(offer.get("images", [])),
                "is_active": offer.get("status") == 1,
                "last_imported_at": datetime.utcnow(),
                "emag_updated_at": datetime.utcnow(),
                "raw_data": json.dumps(offer),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Add part_number_key only if column exists
            if columns_exist:
                product_data["part_number_key"] = _extract_part_number_key_from_url(offer.get("url", ""))

            products_batch.append(product_data)

            # Build offer data
            offer_details = offer.get("offer_details", {}) or {}
            offer_data = {
                "emag_product_id": offer_id,
                "emag_offer_id": _safe_int(offer.get("id")) or 0,
                "price": _safe_float(offer.get("recommended_price")),
                "sale_price": _safe_float(offer.get("sale_price")),
                "currency": _safe_str(offer.get("currency", "RON"), 8),
                "stock": _safe_int(offer.get("general_stock")) or 0,
                "stock_status": _safe_str(offer.get("stock_status"), 50),
                "handling_time": _safe_int(offer_details.get("supply_lead_time")),
                "status": _status_text(offer.get("offer_validation_status")),
                "is_available": offer.get("status") == 1,
                "is_visible": offer.get("status") == 1,
                "vat_rate": _safe_int(offer.get("vat_id")),
                "vat_included": True,
                "warehouse_id": _safe_int(offer_details.get("warehouse_id")),
                "warehouse_name": _safe_str(offer.get("warehouse_name"), 255),
                "account_type": EMAG_ACCOUNT_TYPE,
                "warranty": _safe_int(offer.get("warranty")),
                "raw_data": json.dumps(offer),
            }

            # Add part_number_key only if column exists
            if columns_exist:
                offer_data["part_number_key"] = _extract_part_number_key_from_url(offer.get("url", ""))

            if metadata_column:
                offer_data["metadata_payload"] = json.dumps({
                    "validation_status": offer.get("offer_validation_status", {}),
                    "availability": offer.get("availability", []),
                    "genius_eligibility": offer.get("genius_eligibility")
                })

            offers_batch.append(offer_data)

            SYNC_OFFERS_PROCESSED.labels(EMAG_ACCOUNT_TYPE).inc()
            processed += 1

        except Exception as e:
            logger.error(f"Error processing offer {offer.get('id')}: {e}")
            batch_errors += 1
            continue

    # Execute batched database operations
    if not products_batch and not offers_batch:
        logger.warning("No products or offers to process in this batch")
        return 0

    logger.info(f"Starting database operations with {len(products_batch)} products and {len(offers_batch)} offers")
    
    try:
        with get_db() as db:
            # Begin a transaction
            db.begin()
            logger.info("Database transaction started")
            
            # First, ensure all products exist and get their IDs
            product_id_map = {}
            if products_batch:
                logger.info(f"Ensuring {len(products_batch)} products exist...")
                for product in products_batch:
                    emag_id = product['emag_id']
                    try:
                        logger.debug(f"Processing product with emag_id: {emag_id}")
                        
                        # Try to get existing product ID
                        result = db.execute(
                            text("SELECT id, emag_id FROM app.emag_products WHERE emag_id = :emag_id"),
                            {'emag_id': emag_id}
                        ).fetchone()
                        
                        if result:
                            product_id = result[0]
                            product_id_map[emag_id] = product_id
                            logger.debug(f"Found existing product with emag_id: {emag_id}, id: {product_id}")
                            continue
                            
                        # If not exists, insert new product
                        logger.info(f"Inserting new product with emag_id: {emag_id}")
                        
                        # Log the product data being inserted
                        logger.debug(f"Product data: {json.dumps(product, default=str, ensure_ascii=False)}")
                        
                        # Prepare the SQL query based on whether part_number_key exists
                        if 'part_number_key' in product and columns_exist:
                            sql = """
                                INSERT INTO app.emag_products (
                                    emag_id, name, description, part_number, part_number_key, emag_category_id,
                                    emag_brand_id, emag_category_name, emag_brand_name,
                                    characteristics, images, is_active, last_imported_at, emag_updated_at, 
                                    raw_data, created_at, updated_at
                                )
                                VALUES (
                                    :emag_id, :name, :description, :part_number, :part_number_key, :emag_category_id,
                                    :emag_brand_id, :emag_category_name, :emag_brand_name,
                                    :characteristics, :images, :is_active, :last_imported_at, :emag_updated_at,
                                    :raw_data, NOW(), NOW()
                                )
                                ON CONFLICT (emag_id) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    description = EXCLUDED.description,
                                    part_number = EXCLUDED.part_number,
                                    part_number_key = EXCLUDED.part_number_key,
                                    emag_category_id = EXCLUDED.emag_category_id,
                                    emag_brand_id = EXCLUDED.emag_brand_id,
                                    emag_category_name = EXCLUDED.emag_category_name,
                                    emag_brand_name = EXCLUDED.emag_brand_name,
                                    characteristics = EXCLUDED.characteristics,
                                    images = EXCLUDED.images,
                                    is_active = EXCLUDED.is_active,
                                    last_imported_at = EXCLUDED.last_imported_at,
                                    emag_updated_at = EXCLUDED.emag_updated_at,
                                    raw_data = EXCLUDED.raw_data,
                                    updated_at = NOW()
                                RETURNING id
                            """
                        else:
                            sql = """
                                INSERT INTO app.emag_products (
                                    emag_id, name, description, part_number, emag_category_id,
                                    emag_brand_id, emag_category_name, emag_brand_name,
                                    characteristics, images, is_active, last_imported_at, emag_updated_at, 
                                    raw_data, created_at, updated_at
                                )
                                VALUES (
                                    :emag_id, :name, :description, :part_number, :emag_category_id,
                                    :emag_brand_id, :emag_category_name, :emag_brand_name,
                                    :characteristics, :images, :is_active, :last_imported_at, :emag_updated_at,
                                    :raw_data, NOW(), NOW()
                                )
                                ON CONFLICT (emag_id) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    description = EXCLUDED.description,
                                    part_number = EXCLUDED.part_number,
                                    emag_category_id = EXCLUDED.emag_category_id,
                                    emag_brand_id = EXCLUDED.emag_brand_id,
                                    emag_category_name = EXCLUDED.emag_category_name,
                                    emag_brand_name = EXCLUDED.emag_brand_name,
                                    characteristics = EXCLUDED.characteristics,
                                    images = EXCLUDED.images,
                                    is_active = EXCLUDED.is_active,
                                    last_imported_at = EXCLUDED.last_imported_at,
                                    emag_updated_at = EXCLUDED.emag_updated_at,
                                    raw_data = EXCLUDED.raw_data,
                                    updated_at = NOW()
                                RETURNING id
                            """
                        
                        # Execute the SQL with the product data
                        result = db.execute(text(sql), product)
                        
                        # Get the inserted/updated product ID
                        product_row = result.fetchone()
                        if product_row:
                            product_id = product_row[0]
                            product_id_map[emag_id] = product_id
                            logger.info(f"Successfully processed product with emag_id: {emag_id}, id: {product_id}")
                        else:
                            logger.warning(f"No ID returned when inserting/updating product with emag_id: {emag_id}")
                            continue
                            
                    except Exception as e:
                        logger.error(f"Error processing product with emag_id {emag_id}: {str(e)}")
                        logger.exception("Detailed error:")
                        db.rollback()
                        raise
                
                # Commit the products first
                try:
                    db.commit()
                    logger.info(f"Successfully committed {len(product_id_map)} products to the database")
                except Exception as e:
                    logger.error(f"Error committing products: {str(e)}")
                    db.rollback()
                    raise
            
            # Now process the offers with the product IDs we have
            if offers_batch:
                logger.info(f"Processing {len(offers_batch)} offers with {len(product_id_map)} available products...")
                valid_offers = []
                skipped_offers = 0
                
                for offer in offers_batch:
                    emag_id = offer.get('emag_product_id')
                    if not emag_id:
                        logger.warning("Skipping offer with missing emag_product_id")
                        skipped_offers += 1
                        continue
                        
                    # Try to find the product ID in our map or in the database
                    if emag_id in product_id_map:
                        # Set both emag_product_id and product_id
                        offer['product_id'] = product_id_map[emag_id]
                        valid_offers.append(offer)
                        logger.debug(f"Mapped offer {offer.get('emag_offer_id')} to product_id: {offer['product_id']}")
                    else:
                        # Try to get the product from the database
                        try:
                            result = db.execute(
                                text("SELECT id, emag_id FROM app.emag_products WHERE emag_id = :emag_id"),
                                {'emag_id': emag_id}
                            ).fetchone()
                            
                            if result:
                                product_id, emag_id = result
                                offer['product_id'] = product_id
                                offer['emag_product_id'] = emag_id
                                product_id_map[emag_id] = product_id
                                valid_offers.append(offer)
                                logger.info(f"Found existing product for emag_id: {emag_id}, product_id: {product_id}")
                            else:
                                logger.warning(f"No product found for emag_id: {emag_id}, skipping offer {offer.get('emag_offer_id')}")
                                skipped_offers += 1
                        except Exception as e:
                            logger.error(f"Error looking up product for emag_id {emag_id}: {str(e)}")
                            skipped_offers += 1
                
                # Update offers_batch to only include valid offers
                offers_batch = valid_offers
                logger.info(f"After validation, {len(offers_batch)} offers remain for processing, {skipped_offers} skipped")
                
                # If no valid offers left, log and return
                if not offers_batch:
                    logger.warning("No valid offers to process after validation")
                    db.rollback()
                    return 0
                
                # Process offers in chunks for database efficiency
                chunk = offers_batch
                chunk_size = 100  # Reducem dimensiunea lotului pentru a evita problemele de memorie
                logger.info("Processing {} offers in chunks of {}".format(len(chunk), chunk_size))
                for i in range(0, len(chunk), chunk_size):
                    batch = chunk[i:i + chunk_size]
                    batch_num = i // chunk_size + 1
                    total_batches = (len(chunk) + chunk_size - 1) // chunk_size
                    logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch)} offers")
                    
                    # Log first offer in batch for debugging
                    if batch:
                        first_offer = batch[0]
                        logger.debug(f"First offer in batch {batch_num}: {json.dumps(first_offer, default=str, ensure_ascii=False, indent=2)}")
                    chunk_batch = chunk[i:i+chunk_size]

                    if metadata_column:
                        sql = text("""
                            INSERT INTO app.emag_product_offers (
                                emag_product_id, emag_offer_id, price, sale_price, currency,
                                stock, stock_status, handling_time, status, is_available,
                                is_visible, vat_rate, vat_included, warehouse_id, warehouse_name,
                                account_type, warranty, raw_data, created_at, updated_at
                            )
                            VALUES (
                                :emag_product_id, :emag_offer_id, :price, :sale_price, :currency,
                                :stock, :stock_status, :handling_time, :status, :is_available,
                                :is_visible, :vat_rate, :vat_included, :warehouse_id, :warehouse_name,
                                :account_type, :warranty, :raw_data, NOW(), NOW()
                            )
                            ON CONFLICT (emag_offer_id) DO UPDATE SET
                                price = EXCLUDED.price,
                                sale_price = EXCLUDED.sale_price,
                                currency = EXCLUDED.currency,
                                stock = EXCLUDED.stock,
                                stock_status = EXCLUDED.stock_status,
                                handling_time = EXCLUDED.handling_time,
                                status = EXCLUDED.status,
                                is_available = EXCLUDED.is_available,
                                is_visible = EXCLUDED.is_visible,
                                vat_rate = EXCLUDED.vat_rate,
                                vat_included = EXCLUDED.vat_included,
                                warehouse_id = EXCLUDED.warehouse_id,
                                warehouse_name = EXCLUDED.warehouse_name,
                                account_type = EXCLUDED.account_type,
                                warranty = EXCLUDED.warranty,
                                raw_data = EXCLUDED.raw_data,
                                {metadata_column} = :metadata_payload,
                                updated_at = NOW()
                        """.format(metadata_column=metadata_column))
                    else:
                        # Use the same SQL as above but without the metadata column
                        sql = text("""
                            INSERT INTO app.emag_product_offers (
                                emag_product_id, emag_offer_id, price, sale_price, currency,
                                stock, stock_status, handling_time, status, is_available,
                                is_visible, vat_rate, vat_included, warehouse_id, warehouse_name,
                                account_type, warranty, raw_data, created_at, updated_at
                            )
                            VALUES (
                                :emag_product_id, :emag_offer_id, :price, :sale_price, :currency,
                                :stock, :stock_status, :handling_time, :status, :is_available,
                                :is_visible, :vat_rate, :vat_included, :warehouse_id, :warehouse_name,
                                :account_type, :warranty, :raw_data, NOW(), NOW()
                            )
                            ON CONFLICT (emag_offer_id) DO UPDATE SET
                                price = EXCLUDED.price,
                                sale_price = EXCLUDED.sale_price,
                                currency = EXCLUDED.currency,
                                stock = EXCLUDED.stock,
                                stock_status = EXCLUDED.stock_status,
                                handling_time = EXCLUDED.handling_time,
                                status = EXCLUDED.status,
                                is_available = EXCLUDED.is_available,
                                is_visible = EXCLUDED.is_visible,
                                vat_rate = EXCLUDED.vat_rate,
                                vat_included = EXCLUDED.vat_included,
                                warehouse_id = EXCLUDED.warehouse_id,
                                warehouse_name = EXCLUDED.warehouse_name,
                                account_type = EXCLUDED.account_type,
                                warranty = EXCLUDED.warranty,
                                raw_data = EXCLUDED.raw_data,
                                updated_at = NOW()
                            WHERE emag_product_offers.emag_offer_id = EXCLUDED.emag_offer_id
                        """)

                    # Prepare batch data with proper field handling
                    batch_data = []
                    for entry in chunk_batch:
                        entry_data = entry.copy()
                        
                        # Ensure all required fields are present
                        required_fields = ['emag_product_id', 'emag_offer_id', 'price', 'sale_price', 'currency',
                                         'stock', 'stock_status', 'handling_time', 'status', 'is_available',
                                         'is_visible', 'vat_rate', 'vat_included', 'warehouse_id', 'warehouse_name',
                                         'account_type', 'warranty', 'raw_data']
                        
                        # Add part_number_key only if the column exists
                        if columns_exist:
                            required_fields.append('part_number_key')
                        
                        for field in required_fields:
                            if field not in entry_data:
                                entry_data[field] = None
                        
                        # Remove part_number_key if columns don't exist to avoid SQL errors
                        if not columns_exist and 'part_number_key' in entry_data:
                            del entry_data['part_number_key']
                        
                        # Handle metadata if needed
                        if metadata_column and 'metadata_payload' not in entry_data:
                            entry_data['metadata_payload'] = {}
                        
                        batch_data.append(entry_data)
                    
                    # Build the UPSERT SQL based on whether part_number_key column exists
                    if columns_exist:
                        upsert_sql = text("""
                            INSERT INTO app.emag_product_offers (
                                emag_product_id, emag_offer_id, price, sale_price, currency,
                                stock, stock_status, handling_time, status, is_available,
                                is_visible, vat_rate, vat_included, warehouse_id, warehouse_name,
                                account_type, warranty, part_number_key, raw_data, created_at, updated_at
                            ) VALUES (
                                :emag_product_id, :emag_offer_id, :price, :sale_price, :currency,
                                :stock, :stock_status, :handling_time, :status, :is_available,
                                :is_visible, :vat_rate, :vat_included, :warehouse_id, :warehouse_name,
                                :account_type, :warranty, :part_number_key, :raw_data, NOW(), NOW()
                            )
                            ON CONFLICT (emag_offer_id, account_type) DO UPDATE SET
                                emag_product_id = EXCLUDED.emag_product_id,
                                price = EXCLUDED.price,
                                sale_price = EXCLUDED.sale_price,
                                currency = EXCLUDED.currency,
                                stock = EXCLUDED.stock,
                                stock_status = EXCLUDED.stock_status,
                                handling_time = EXCLUDED.handling_time,
                                status = EXCLUDED.status,
                                is_available = EXCLUDED.is_available,
                                is_visible = EXCLUDED.is_visible,
                                vat_rate = EXCLUDED.vat_rate,
                                vat_included = EXCLUDED.vat_included,
                                warehouse_id = EXCLUDED.warehouse_id,
                                warehouse_name = EXCLUDED.warehouse_name,
                                warranty = EXCLUDED.warranty,
                                part_number_key = EXCLUDED.part_number_key,
                                raw_data = EXCLUDED.raw_data,
                                updated_at = NOW()
                        """)
                    else:
                        upsert_sql = text("""
                            INSERT INTO app.emag_product_offers (
                                emag_product_id, emag_offer_id, price, sale_price, currency,
                                stock, stock_status, handling_time, status, is_available,
                                is_visible, vat_rate, vat_included, warehouse_id, warehouse_name,
                                account_type, warranty, raw_data, created_at, updated_at
                            ) VALUES (
                                :emag_product_id, :emag_offer_id, :price, :sale_price, :currency,
                                :stock, :stock_status, :handling_time, :status, :is_available,
                                :is_visible, :vat_rate, :vat_included, :warehouse_id, :warehouse_name,
                                :account_type, :warranty, :raw_data, NOW(), NOW()
                            )
                            ON CONFLICT (emag_offer_id, account_type) DO UPDATE SET
                                emag_product_id = EXCLUDED.emag_product_id,
                                price = EXCLUDED.price,
                                sale_price = EXCLUDED.sale_price,
                                currency = EXCLUDED.currency,
                                stock = EXCLUDED.stock,
                                stock_status = EXCLUDED.stock_status,
                                handling_time = EXCLUDED.handling_time,
                                status = EXCLUDED.status,
                                is_available = EXCLUDED.is_available,
                                is_visible = EXCLUDED.is_visible,
                                vat_rate = EXCLUDED.vat_rate,
                                vat_included = EXCLUDED.vat_included,
                                warehouse_id = EXCLUDED.warehouse_id,
                                warehouse_name = EXCLUDED.warehouse_name,
                                warranty = EXCLUDED.warranty,
                                raw_data = EXCLUDED.raw_data,
                                updated_at = NOW()
                        """)
                    
                    # Process in smaller chunks
                    chunk_size = 50
                    success_count = 0
                    error_count = 0
                    
                    for i in range(0, len(batch_data), chunk_size):
                        chunk = batch_data[i:i + chunk_size]
                        
                        try:
                            # Process the chunk with the new UPSERT operation
                            for item in chunk:
                                try:
                                    db.execute(upsert_sql, item)
                                    success_count += 1
                                except Exception as e:
                                    error_count += 1
                                    logger.error(f"Error processing offer_id {item.get('emag_offer_id')} (account_type: {item.get('account_type')}): {str(e)}")
                                    logger.error(f"Problematic item data: {json.dumps(item, default=str, ensure_ascii=False, indent=2)}")
                                    # Continue with the next item even if one fails
                                    continue
                            
                            db.commit()
                            logger.info(f"Successfully processed chunk {i//chunk_size + 1}/{(len(batch_data) + chunk_size - 1)//chunk_size} - Success: {success_count}, Errors: {error_count}")
                            
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error processing chunk {i//chunk_size + 1}: {str(e)}")
                            logger.exception("Chunk processing error details:")
                            
                            # Try to process each item individually to find the problematic one
                            for idx, item in enumerate(chunk):
                                try:
                                    db.execute(upsert_sql, item)
                                    db.commit()
                                    success_count += 1
                                except Exception as single_err:
                                    db.rollback()
                                    error_count += 1
                                    logger.error(f"Error processing item {i + idx + 1}: {str(single_err)}")
                                    logger.error(f"Problematic item data: {json.dumps(item, default=str, ensure_ascii=False, indent=2)}")
                                    # Skip this item and continue with the next one
                                    continue

                logger.info(f"✅ Successfully processed batch - Success: {success_count}, Errors: {error_count}, Total: {len(offers_batch)}")
                
                # Commit the transaction if we got this far
                try:
                    if success_count > 0:
                        db.commit()
                        logger.info(f"Successfully committed {success_count} offers to the database")
                    return success_count
                except Exception as e:
                    logger.error(f"Error committing offers: {str(e)}")
                    db.rollback()
                    raise
            
            # If we get here, we only processed products, no offers
            db.commit()
            return 0
            
    except Exception as e:
        logger.error(f"Error in process_offers_batch: {str(e)}")
        logger.exception("Error details:")
        try:
            db.rollback()
            logger.info("Transaction rolled back due to error")
        except Exception as e:
            logger.error(f"Could not roll back transaction: {str(e)}")
        raise

    return processed


async def sync_both_accounts():
    """Sync from both MAIN and FBE accounts simultaneously"""
    logger.info("🚀 Starting simultaneous sync from both MAIN and FBE accounts...")
    
    # Load credentials to get available accounts
    load_credentials()
    
    available_accounts = []
    if 'main' in ACCOUNT_CREDENTIALS:
        available_accounts.append(('main', ACCOUNT_CREDENTIALS['main']))
        logger.info("✅ MAIN account credentials found")
    else:
        logger.warning("⚠️ MAIN account credentials not found")
        
    if 'fbe' in ACCOUNT_CREDENTIALS:
        available_accounts.append(('fbe', ACCOUNT_CREDENTIALS['fbe']))
        logger.info("✅ FBE account credentials found")
    else:
        logger.warning("⚠️ FBE account credentials not found")
    
    if not available_accounts:
        raise ValueError("❌ No account credentials available for multi-account sync")
    
    if len(available_accounts) == 1:
        logger.warning(f"Only {available_accounts[0][0].upper()} account available, falling back to single account sync")
        # Use the existing single account sync
        global EMAG_ACCOUNT_TYPE, EMAG_USER, EMAG_PASS
        EMAG_ACCOUNT_TYPE = available_accounts[0][0]
        EMAG_USER, EMAG_PASS = available_accounts[0][1]
        return await sync_emag_offers()
    
    # Start Prometheus metrics server
    try:
        start_http_server(METRICS_PORT)
        logger.info(f"📈 Prometheus metrics server started on :{METRICS_PORT}")
    except OSError:
        pass
    
    # Reset global sync state
    global current_sync_id, sync_start_time, shutdown_requested
    current_sync_id = None
    sync_start_time = _now_utc()
    shutdown_requested = False
    
    # Run both syncs concurrently
    logger.info(f"📡 Starting concurrent sync for {len(available_accounts)} accounts...")
    tasks = []
    
    for account_type, credentials in available_accounts:
        # Create a separate task for each account
        task = asyncio.create_task(
            sync_single_account(account_type, credentials),
            name=f"sync_{account_type}"
        )
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    total_processed = 0
    successful_syncs = 0
    failed_syncs = 0
    
    for i, result in enumerate(results):
        account_type = available_accounts[i][0]
        
        if isinstance(result, Exception):
            logger.error(f"❌ [{account_type.upper()}] Sync failed with exception: {result}")
            failed_syncs += 1
        else:
            if isinstance(result, dict) and result.get('sync_failed'):
                logger.warning(f"⚠️ [{account_type.upper()}] Sync completed with errors. Processed: {result.get('total_processed', 0)}")
                failed_syncs += 1
                total_processed += result.get('total_processed', 0)
            else:
                processed_count = result if isinstance(result, int) else result.get('total_processed', 0)
                logger.info(f"✅ [{account_type.upper()}] Sync completed successfully. Processed: {processed_count}")
                successful_syncs += 1
                total_processed += processed_count
    
    # Summary
    logger.info("🏁 Multi-account sync completed!")
    logger.info("📊 Summary: {} successful, {} failed".format(successful_syncs, failed_syncs))
    logger.info("📦 Total offers processed across all accounts: {}".format(total_processed))
    
    return total_processed


async def sync_single_account(account_type, credentials):
    """Sync eMAG offers for a single account (used in multi-account mode)"""
    logger.info(f"🔐 Starting eMAG synchronization for {account_type.upper()} account...")
    
    # Set global credentials for this account
    global EMAG_USER, EMAG_PASS, EMAG_ACCOUNT_TYPE
    original_user, original_pass, original_type = EMAG_USER, EMAG_PASS, EMAG_ACCOUNT_TYPE
    
    try:
        EMAG_USER, EMAG_PASS = credentials
        EMAG_ACCOUNT_TYPE = account_type
        
        # Create sync record for this account
        sync_id = f"sync-{account_type}-{_now_utc().strftime('%H%M%S')}"
        
        try:
            with get_db() as session:
                session.execute(text("""
                    INSERT INTO app.emag_offer_syncs
                    (sync_id, account_type, operation_type, status, started_at, 
                     total_offers_processed, offers_created, offers_updated, 
                     offers_failed, offers_skipped, error_count, errors, filters)
                    VALUES (
                        :sync_id, :account_type, 'full_import', 'running', :started_at,
                        0, 0, 0, 0, 0, 0, '[]'::jsonb, '{}'::jsonb
                    )
                """), {"sync_id": sync_id, "account_type": account_type, "started_at": _now_utc()})

                logger.info(f"[{account_type.upper()}] Sync record created: {sync_id}")
                SYNC_RUN_STATUS.labels(account_type).set(1)
        except Exception as e:
            logger.error(f"[{account_type.upper()}] Error creating sync record: {e}")
            SYNC_RUN_STATUS.labels(account_type).set(3)
            return {"account_type": account_type, "total_processed": 0, "sync_failed": True}

        sync_failed = False
        total_processed = 0

        try:
            async with aiohttp.ClientSession() as session:
                page = 1
                last_progress_update = 0

                while True:
                    # Check for shutdown request
                    if shutdown_requested:
                        logger.warning(f"[{account_type.upper()}] Shutdown requested, stopping sync gracefully...")
                        update_sync_status(sync_id, 'failed', total_processed, "Shutdown requested")
                        SYNC_RUN_STATUS.labels(account_type).set(3)
                        sync_failed = True
                        break

                    # Check for timeout
                    if check_sync_timeout():
                        logger.warning(f"[{account_type.upper()}] Sync timeout exceeded, stopping gracefully...")
                        update_sync_status(sync_id, 'failed', total_processed, f"Timeout after {SYNC_TIMEOUT_HOURS} hours")
                        SYNC_RUN_STATUS.labels(account_type).set(4)
                        sync_failed = True
                        break

                    # Check maximum pages limit
                    if page > MAX_PAGES:
                        logger.warning(f"[{account_type.upper()}] Maximum pages limit reached ({MAX_PAGES}), stopping sync...")
                        update_sync_status(sync_id, 'completed', total_processed, f"Maximum pages limit reached ({MAX_PAGES})")
                        SYNC_RUN_STATUS.labels(account_type).set(2)
                        break

                    try:
                        logger.info(f"[{account_type.upper()}] Fetching page {page}/{MAX_PAGES}...")
                        data = await fetch_emag_products(session, page)

                        if not data or not data.get('results'):
                            logger.info(f"🔚 [{account_type.upper()}] No more results found, sync completed successfully")
                            update_sync_status(sync_id, 'completed', total_processed)
                            SYNC_RUN_STATUS.labels(account_type).set(2)
                            SYNC_LAST_SUCCESS.labels(account_type).set_to_current_time()
                            break

                        page_offers = len(data.get('results', []))
                        logger.info(f"📦 [{account_type.upper()}] Processing {page_offers} offers from page {page}")

                        # Process offers in batches with improved error handling
                        processed_in_page = await process_offers_batch(data['results'], sync_id)

                        total_processed += processed_in_page
                        last_progress_update += processed_in_page

                        # Update progress periodically
                        if last_progress_update >= PROGRESS_UPDATE_INTERVAL:
                            update_sync_status(sync_id, 'running', total_processed)
                            last_progress_update = 0
                            logger.info(f"📊 [{account_type.upper()}] Progress update: {total_processed} offers processed so far")

                        # Increment page for next iteration
                        page += 1
                        await asyncio.sleep(1)  # Rate limiting between pages

                    except Exception as e:
                        logger.error(f"[{account_type.upper()}] Error processing page {page}: {e}")
                        SYNC_REQUEST_ERRORS.labels(endpoint="product_offer/read", account_type=account_type, reason=str(e)[:50]).inc()
                        
                        # Continue to next page on error, but log it
                        page += 1
                        if page > MAX_PAGES:
                            break

        except Exception as e:
            logger.error(f"[{account_type.upper()}] Critical error in sync: {e}")
            update_sync_status(sync_id, 'failed', total_processed, str(e))
            SYNC_RUN_STATUS.labels(account_type).set(3)
            sync_failed = True

        logger.info(f"✅ [{account_type.upper()}] Sync completed. Total processed: {total_processed}")
        return {"account_type": account_type, "total_processed": total_processed, "sync_failed": sync_failed, "sync_id": sync_id}
        
    finally:
        # Restore original credentials
        EMAG_USER, EMAG_PASS, EMAG_ACCOUNT_TYPE = original_user, original_pass, original_type


if __name__ == "__main__":
    try:
        # Check sync mode from environment variable
        sync_mode = os.getenv('EMAG_SYNC_MODE', 'single').lower()
        
        if sync_mode == 'both':
            logger.info("🔄 Multi-account sync mode enabled")
            asyncio.run(sync_both_accounts())
        else:
            logger.info("🔄 Single account sync mode (default)")
            asyncio.run(sync_emag_offers())
            
    except KeyboardInterrupt:
        logger.info("Sync interrupted by user")
        if current_sync_id:
            update_sync_status(current_sync_id, 'failed', error_message="Interrupted by user")
    except Exception as e:
        logger.error(f"Sync failed with exception: {e}")
        if current_sync_id:
            update_sync_status(current_sync_id, 'failed', error_message=str(e))
        sys.exit(1)
