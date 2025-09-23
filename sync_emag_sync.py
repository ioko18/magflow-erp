#!/usr/bin/env python3
"""
Improved eMAG synchronization with async support
Enhancements:
- Robust DB connection via environment (PgBouncer aware)
- Hardened field mappings to avoid type/constraint errors
- Prometheus metrics for observability
"""

import aiohttp
import asyncio
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from prometheus_client import Counter, Histogram, Gauge, start_http_server

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
SYNC_BATCH_SIZE = int(os.getenv("EMAG_SYNC_BATCH_SIZE", "0"))  # 0 or <=0 means no chunking
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
    "Current sync run status (0=idle,1=running,2=completed,3=failed)",
    ["account_type"]
)

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
            
            logger.info(f"Making API request to {url} with user: {EMAG_USER}")
            SYNC_REQUESTS.labels(endpoint="product_offer/read", account_type=EMAG_ACCOUNT_TYPE).inc()
            with SYNC_LATENCY.labels(endpoint="product_offer/read", account_type=EMAG_ACCOUNT_TYPE).time():
                async with session.post(
                    url,
                    json=payload,
                    auth=aiohttp.BasicAuth(EMAG_USER, EMAG_PASS),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_text = await response.text()
                logger.info(f"API Response Status: {response.status}")
                logger.info(f"API Response Headers: {dict(response.headers)}")
                logger.info(f"API Response Body (first 200 chars): {response_text[:200]}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info("Successfully parsed JSON response")
                        logger.info(f"Response keys: {list(data.keys())}")
                        logger.info(f"isError: {data.get('isError')}")
                        logger.info(f"Number of results: {len(data.get('results', []))}")
                        
                        if data.get('isError', False):
                            # Extract error message from messages array
                            messages = data.get('messages', [])
                            error_msg = messages[0] if messages else 'No error message provided'
                            logger.error(f"API returned error: {error_msg}")
                            SYNC_REQUEST_ERRORS.labels(
                                endpoint="product_offer/read",
                                account_type=EMAG_ACCOUNT_TYPE,
                                reason="api_isError"
                            ).inc()
                            raise Exception(f"API error: {error_msg}")
                        return data
                    except Exception as json_error:
                        logger.error(f"Error parsing JSON response: {json_error}")
                        logger.error(f"Response text: {response_text}")
                        SYNC_REQUEST_ERRORS.labels(
                            endpoint="product_offer/read",
                            account_type=EMAG_ACCOUNT_TYPE,
                            reason="json_parse"
                        ).inc()
                        raise
                elif response.status == 429:
                    logger.warning("Rate limit exceeded. Retrying...")
                    await asyncio.sleep(5)
                    SYNC_REQUEST_ERRORS.labels(
                        endpoint="product_offer/read",
                        account_type=EMAG_ACCOUNT_TYPE,
                        reason="rate_limit"
                    ).inc()
                    raise Exception("Rate limit exceeded")
                else:
                    logger.error(f"HTTP error {response.status}: {response_text}")
                    SYNC_REQUEST_ERRORS.labels(
                        endpoint="product_offer/read",
                        account_type=EMAG_ACCOUNT_TYPE,
                        reason=f"http_{response.status}"
                    ).inc()
                    response.raise_for_status()
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            raise

def _build_db_url_from_env() -> str:
    """Resolve DB URL, preferring explicit env vars and PgBouncer mapping.

    Order of precedence:
    1) DATABASE_SYNC_URL
    2) DATABASE_URL
    3) Construct from DB_* vars, defaulting to PgBouncer localhost:6432/postgres
    """
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


def get_db_session():
    """Create database session using environment-driven configuration."""
    try:
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
        engine = create_engine(db_url, echo=False, pool_pre_ping=True)
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
        yield session
        session.commit()
        logger.info("Database transaction committed successfully")
    except Exception as e:
        if session:
            try:
                session.rollback()
                logger.info("Database transaction rolled back due to error")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        logger.error(f"Database error: {e}")
        raise
    finally:
        if session:
            try:
                session.close()
                logger.info("Database session closed")
            except Exception as close_error:
                logger.error(f"Error closing database session: {close_error}")

async def sync_emag_offers():
    """Sync eMAG offers to database"""
    
    logger.info("🔐 Connecting to eMAG API...")
    
    # Load and validate credentials
    load_credentials()
    # Start Prometheus metrics server (idempotent per process)
    try:
        start_http_server(METRICS_PORT)
        logger.info(f"📈 Prometheus metrics server started on :{METRICS_PORT}")
    except OSError:
        # Already started in this process
        pass
    
    try:
        with get_db() as session:
            # Create sync record
            sync_id = f"sync-{datetime.now().strftime('%H%M%S')}"
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
        raise
    
    try:
        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                try:
                    data = await fetch_emag_products(session, page)
                    logger.info(f"🔍 API Response received for page {page}")
                    logger.info(f"📊 Response type: {type(data)}")
                    if isinstance(data, dict):
                        logger.info(f"📋 Response keys: {list(data.keys())}")
                        logger.info(f"🚨 isError: {data.get('isError', 'N/A')}")
                        logger.info(f"📝 Messages: {data.get('messages', [])}")
                        logger.info(f"📦 Results count: {len(data.get('results', []))}")
                        if 'results' in data and data['results']:
                            first_result = data['results'][0]
                            logger.info(f"🎯 First result ID: {first_result.get('id', 'N/A')}")
                            logger.info(f"📋 First result name: {first_result.get('name', 'N/A')[:50]}...")
                    else:
                        logger.error(f"❌ Unexpected response type: {type(data)}")
                        logger.error(f"📄 Raw response: {data}")
                        break

                    if not data.get('results'):
                        logger.info("🔚 No results found, stopping sync")
                        break
                    
                    # Process and save offers with improved error handling
                    try:
                        with get_db() as db:
                            logger.info("Starting database operations...")
                            if SYNC_BATCH_SIZE and SYNC_BATCH_SIZE > 0:
                                logger.info(f"Using EMAG_SYNC_BATCH_SIZE={SYNC_BATCH_SIZE} for batched upserts")
                            processed = 0
                            products_batch = []
                            offers_batch = []
                            batch_errors = 0
                            for offer in data['results']:
                                try:
                                    logger.info(f"Processing offer ID: {offer.get('id')}")
                                    offer_id = str(offer.get('id', ''))
                                    if not offer_id:
                                        logger.warning(f"Skipping offer without ID: {offer}")
                                        continue
                                    # Validate required fields
                                    if not offer.get('id'):
                                        logger.warning(f"Skipping offer without ID: {offer}")
                                        continue
                                    offer_id = str(offer.get('id', ''))

                                    # Extract data with proper field mapping
                                    # Defensive access helpers
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

                                    def _status_text(ov):
                                        # offer_validation_status can be dict or int or str
                                        if isinstance(ov, dict):
                                            return _safe_str(ov.get("description", ""), 100)
                                        return _safe_str(ov, 100)

                                    product_data = {
                                        "emag_id": offer_id,
                                        "name": _safe_str(offer.get("name", ""), 500),
                                        "description": _safe_str(offer.get("description", "")),
                                        "part_number": _safe_str(offer.get("part_number", ""), 100),
                                        "emag_category_id": offer.get("category_id"),
                                        "emag_brand_id": offer.get("brand_id"),
                                        "emag_category_name": _safe_str(offer.get("category_name"), 255),
                                        "emag_brand_name": _safe_str(offer.get("brand_name"), 255),
                                        "characteristics": json.dumps(offer.get("characteristics", [])),
                                        "images": json.dumps(offer.get("images", [])),
                                        "is_active": offer.get("status") == 1,  # status 1 = active
                                        "raw_data": json.dumps(offer),
                                    }
                                    
                                    products_batch.append(product_data)
                                    
                                    # Insert offer with correct field mapping
                                    offer_data = {
                                        "emag_product_id": offer_id,
                                        "emag_offer_id": offer.get("id", 0),
                                        "price": _safe_float(offer.get("recommended_price")),
                                        "sale_price": _safe_float(offer.get("sale_price")),
                                        "currency": _safe_str(offer.get("currency", "RON"), 8),
                                        "stock": int(offer.get("general_stock", 0) or 0),
                                        "stock_status": offer.get("stock_status"),
                                        "handling_time": (offer.get("offer_details", {}) or {}).get("supply_lead_time"),
                                        "status": _status_text(offer.get("offer_validation_status")),
                                        "is_available": offer.get("status") == 1,
                                        "is_visible": offer.get("status") == 1,
                                        "vat_rate": offer.get("vat_id") if offer.get("vat_id") else None,
                                        "vat_included": True,  # Default for Romanian market
                                        "warehouse_id": (offer.get("offer_details", {}) or {}).get("warehouse_id"),
                                        "warehouse_name": _safe_str(offer.get("warehouse_name"), 255),
                                        "account_type": EMAG_ACCOUNT_TYPE,
                                        "warranty": offer.get("warranty"),
                                        "raw_data": json.dumps(offer),
                                        "metadata_": json.dumps({
                                            "validation_status": offer.get("offer_validation_status", {}),
                                            "availability": offer.get("availability", []),
                                            "genius_eligibility": offer.get("genius_eligibility")
                                        }),
                                    }
                                    
                                    offers_batch.append(offer_data)
                                    
                                    SYNC_OFFERS_PROCESSED.labels(EMAG_ACCOUNT_TYPE).inc()
                                    logger.info(f"Successfully processed offer {processed}")
                                    processed += 1
                                except Exception as e:
                                    logger.error(f"Error processing offer {offer.get('id')}: {e}")
                                    # Roll back current transaction to clear InFailedSqlTransaction state
                                    try:
                                        db.rollback()
                                        logger.info("Rolled back transaction for failed offer; continuing with next offer")
                                    except Exception as rb_err:
                                        logger.error(f"Rollback failed: {rb_err}")
                                    batch_errors += 1
                                    # Continue processing other offers even if one fails
                                
                            # Helper to yield chunks
                            def _chunks(seq, n):
                                if not n or n <= 0:
                                    yield seq
                                else:
                                    for i in range(0, len(seq), n):
                                        yield seq[i:i+n]

                            # Execute batched upserts (products then offers)
                            try:
                                if products_batch:
                                    logger.info(f"Batched upsert products: {len(products_batch)}")
                                    for pchunk in _chunks(products_batch, SYNC_BATCH_SIZE):
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
                                        """), pchunk)
                                if offers_batch:
                                    logger.info(f"Batched upsert offers: {len(offers_batch)}")
                                    for ochunk in _chunks(offers_batch, SYNC_BATCH_SIZE):
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
                                        """), ochunk)
                            except Exception as batch_e:
                                logger.error(f"Batch upsert failure: {batch_e}")

                            # Update sync record with separate transaction to avoid conflicts
                            try:
                                with get_db() as update_db:
                                    update_db.execute(text("""
                                        UPDATE app.emag_offer_syncs
                                        SET status = 'running',
                                            total_offers_processed = :processed,
                                            updated_at = NOW()
                                        WHERE sync_id = :sync_id
                                    """), {
                                        "sync_id": sync_id,
                                        "processed": processed
                                    })
                                    logger.info(f"Updated sync record: {processed} offers processed")
                            except Exception as update_error:
                                logger.error(f"Failed to update sync record: {update_error}")
                                # Don't fail the entire sync for this
                    except Exception as e:
                        logger.error(f"Error in database operations for page {page}: {e}")
                        raise
                    
                    page += 1
                    await asyncio.sleep(1)  # Respect rate limits
                except Exception as e:
                    logger.error(f"Failed to process page {page}: {e}")
                    break
            
            # Final sync record update with separate transaction
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
                    logger.info("Successfully synced offers to database!")
            except Exception as final_error:
                logger.error(f"Error updating final sync record: {final_error}")
                # Try to mark as failed
                try:
                    with get_db() as fail_db:
                        fail_db.execute(text('''
                        UPDATE app.emag_offer_syncs
                        SET status = 'failed', updated_at = NOW()
                        WHERE sync_id = :sync_id
                    '''), {"sync_id": sync_id})
                    SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(3)
                    logger.info("Marked sync as failed")
                except Exception as fail_error:
                    logger.error(f"Failed to mark sync as failed: {fail_error}")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        try:
            with get_db() as session:
                session.execute(text('''
                    UPDATE app.emag_offer_syncs 
                    SET status = 'failed', updated_at = NOW()
                    WHERE sync_id = :sync_id
                '''), {"sync_id": sync_id})
            SYNC_RUN_STATUS.labels(EMAG_ACCOUNT_TYPE).set(3)
        except Exception as e:
            logger.error(f"Error updating sync record: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(sync_emag_offers())
