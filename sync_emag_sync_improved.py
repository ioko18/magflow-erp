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
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import signal
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
    global EMAG_API_URL, EMAG_USER, EMAG_PASS, EMAG_ACCOUNT_TYPE

    EMAG_API_URL = os.getenv('EMAG_API_BASE_URL', 'https://marketplace-api.emag.ro/api-3')
    EMAG_ACCOUNT_TYPE = os.getenv('EMAG_ACCOUNT_TYPE', 'main')

    # Load MAIN account credentials
    main_username = os.getenv('EMAG_API_USERNAME')
    main_password = os.getenv('EMAG_API_PASSWORD')

    # Load FBE account credentials
    fbe_username = os.getenv('EMAG_FBE_API_USERNAME')
    fbe_password = os.getenv('EMAG_FBE_API_PASSWORD')

    # Validate credentials
    if not main_username or not main_password:
        raise ValueError("MAIN account credentials not found. Please set EMAG_API_USERNAME and EMAG_API_PASSWORD environment variables.")

    if not fbe_username or not fbe_password:
        raise ValueError("FBE account credentials not found. Please set EMAG_FBE_API_USERNAME and EMAG_FBE_API_PASSWORD environment variables.")

    # Set credentials based on account type
    if EMAG_ACCOUNT_TYPE == 'main':
        EMAG_USER = main_username
        EMAG_PASS = main_password
        logger.info(f"Using MAIN account: {EMAG_USER}")
    elif EMAG_ACCOUNT_TYPE == 'fbe':
        EMAG_USER = fbe_username
        EMAG_PASS = fbe_password
        logger.info(f"Using FBE account: {EMAG_USER}")
    elif EMAG_ACCOUNT_TYPE == 'auto':
        # Try MAIN first, fallback to FBE
        EMAG_USER = main_username
        EMAG_PASS = main_password
        logger.info(f"Using AUTO mode - starting with MAIN account: {EMAG_USER}")
    else:
        raise ValueError(f"Invalid EMAG_ACCOUNT_TYPE: {EMAG_ACCOUNT_TYPE}. Must be 'main', 'fbe', or 'auto'")

    logger.info(f"Loaded credentials for account type: {EMAG_ACCOUNT_TYPE}")

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

def _build_db_url_from_env() -> str:
    """Resolve DB URL with proper fallback hierarchy"""
    # 1) Explicit sync URL
    url = os.getenv("DATABASE_SYNC_URL")
    if url:
        return url

    # 2) Fallback to general DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        # For async URLs (postgresql+asyncpg), convert to sync driver for SQLAlchemy engine here
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url

    # 3) Build from parts with PgBouncer defaults
    user = os.getenv("DB_USER", "app")
    password = os.getenv("DB_PASS", "app_password_change_me")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "6432"))  # PgBouncer published port
    name = os.getenv("DB_NAME", "postgres")   # PgBouncer routes to DB internally
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"

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
                        errors = array_append(errors, :error_message),
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

def check_sync_timeout():
    """Check if sync has exceeded timeout limit"""
    if sync_start_time and datetime.utcnow() - sync_start_time > timedelta(hours=SYNC_TIMEOUT_HOURS):
        logger.warning(f"Sync timeout exceeded ({SYNC_TIMEOUT_HOURS} hours)")
        return True
    return False

async def sync_emag_offers():
    """Sync eMAG offers to database with improved error handling and safety limits"""
    global current_sync_id, sync_start_time, shutdown_requested

    logger.info("🔐 Starting eMAG synchronization...")

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
    sync_start_time = datetime.utcnow()
    shutdown_requested = False

    # Create sync record
    sync_id = f"sync-{datetime.now().strftime('%H%M%S')}"
    current_sync_id = sync_id

    try:
        with get_db() as session:
            session.execute(text("""
                INSERT INTO app.emag_offer_syncs
                (sync_id, account_type, operation_type, status, started_at)
                VALUES (:sync_id, :account_type, 'full_import', 'running', :started_at)
            """), {"sync_id": sync_id, "account_type": EMAG_ACCOUNT_TYPE, "started_at": datetime.utcnow()})

            logger.info(f"Sync record created: {sync_id}")
            # Metrics: mark run as running
            SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(1)
    except Exception as e:
        logger.error(f"Error creating sync record: {e}")
        SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(3)
        raise

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
                    break

                # Check for timeout
                if check_sync_timeout():
                    logger.warning("Sync timeout exceeded, stopping gracefully...")
                    update_sync_status(sync_id, 'failed', total_processed, f"Timeout after {SYNC_TIMEOUT_HOURS} hours")
                    SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(4)
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
                    break

            # Final sync record update
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
                        "completed_at": datetime.utcnow()
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
        return 0

    processed = 0
    products_batch = []
    offers_batch = []
    batch_errors = 0

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

            # Build product data
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
                "raw_data": json.dumps(offer),
            }

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
                "metadata_": json.dumps({
                    "validation_status": offer.get("offer_validation_status", {}),
                    "availability": offer.get("availability", []),
                    "genius_eligibility": offer.get("genius_eligibility")
                }),
            }

            offers_batch.append(offer_data)

            SYNC_OFFERS_PROCESSED.labels(EMAG_ACCOUNT_TYPE).inc()
            processed += 1

        except Exception as e:
            logger.error(f"Error processing offer {offer.get('id')}: {e}")
            batch_errors += 1
            continue

    # Execute batched database operations
    if products_batch or offers_batch:
        try:
            with get_db() as db:
                # Upsert products in batches
                if products_batch:
                    logger.info(f"Upserting {len(products_batch)} products...")
                    for i in range(0, len(products_batch), SYNC_BATCH_SIZE):
                        chunk = products_batch[i:i + SYNC_BATCH_SIZE]
                        db.execute(text("""
                            INSERT INTO app.emag_products (
                                emag_id, name, description, part_number, emag_category_id,
                                emag_brand_id, emag_category_name, emag_brand_name,
                                characteristics, images, is_active, raw_data, created_at, updated_at
                            )
                            VALUES (
                                :emag_id, :name, :description, :part_number, :emag_category_id,
                                :emag_brand_id, :emag_category_name, :emag_brand_name,
                                :characteristics, :images, :is_active, :raw_data, NOW(), NOW()
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
                                raw_data = EXCLUDED.raw_data,
                                updated_at = NOW()
                        """), chunk)

                # Upsert offers in batches
                if offers_batch:
                    logger.info(f"Upserting {len(offers_batch)} offers...")
                    for i in range(0, len(offers_batch), SYNC_BATCH_SIZE):
                        chunk = offers_batch[i:i + SYNC_BATCH_SIZE]
                        db.execute(text("""
                            INSERT INTO app.emag_product_offers (
                                emag_product_id, emag_offer_id, price, sale_price, currency,
                                stock, stock_status, handling_time, status, is_available,
                                is_visible, vat_rate, vat_included, warehouse_id, warehouse_name,
                                account_type, warranty, raw_data, metadata_, created_at, updated_at
                            )
                            VALUES (
                                :emag_product_id, :emag_offer_id, :price, :sale_price, :currency,
                                :stock, :stock_status, :handling_time, :status, :is_available,
                                :is_visible, :vat_rate, :vat_included, :warehouse_id, :warehouse_name,
                                :account_type, :warranty, :raw_data, :metadata_, NOW(), NOW()
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
                                metadata_ = EXCLUDED.metadata_,
                                updated_at = NOW()
                        """), chunk)

                logger.info(f"✅ Successfully processed {processed} offers in batch")

        except Exception as batch_e:
            logger.error(f"Batch database operation failed: {batch_e}")
            raise

    return processed

if __name__ == "__main__":
    try:
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
