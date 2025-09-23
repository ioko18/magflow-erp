#!/usr/bin/env python3
"""
eMAG Sync Monitor and Recovery System
Monitors sync processes for stuck states and implements automatic recovery
Enhanced version with database monitoring and recovery capabilities
"""

import asyncio
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging
from prometheus_client import Gauge, Counter, start_http_server
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.warning("python-dotenv not installed.")

# Prometheus metrics
MONITOR_STATUS = Gauge("emag_sync_monitor_status", "Monitor status (0=idle,1=running,2=error)")
STUCK_SYNCS_COUNT = Gauge("emag_sync_stuck_syncs_total", "Number of stuck sync processes")
RECOVERED_SYNCS_COUNT = Counter("emag_sync_recovered_syncs_total", "Number of recovered sync processes")
ACTIVE_SYNCS_COUNT = Gauge("emag_sync_active_syncs_total", "Number of currently active sync processes")
FAILED_SYNCS_LAST_HOUR = Counter("emag_sync_failed_syncs_last_hour_total", "Number of failed syncs in the last hour")

# Global variables
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.warning(f"Received signal {signum}, requesting graceful shutdown...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def _build_db_url_from_env() -> str:
    """Resolve DB URL with proper fallback hierarchy"""
    url = os.getenv("DATABASE_SYNC_URL") or os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url

    user = os.getenv("DB_USER", "app")
    password = os.getenv("DB_PASS", "app_password_change_me")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "6432"))
    name = os.getenv("DB_NAME", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"

def get_db_engine():
    """Get database engine"""
    db_url = _build_db_url_from_env()
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

    engine = create_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=4,
        pool_timeout=10
    )
    return engine

def get_db_session():
    """Create database session"""
    try:
        engine = get_db_engine()
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        raise

@contextmanager
def get_db():
    """Database context manager"""
    session = None
    try:
        session = get_db_session()
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
                logger.debug("Database session closed")
            except Exception as close_error:
                logger.error(f"Error closing database session: {close_error}")

def find_stuck_syncs(max_age_hours: int = 1):
    """Find sync processes that are stuck in running state"""
    stuck_syncs = []
    try:
        with get_db() as session:
            result = session.execute(text("""
                SELECT sync_id, account_type, started_at,
                       EXTRACT(EPOCH FROM (NOW() - started_at))/3600 as hours_running,
                       total_offers_processed
                FROM app.emag_offer_syncs
                WHERE status = 'running'
                AND started_at < NOW() - INTERVAL :max_age
                ORDER BY started_at ASC
            """), {"max_age": f"{max_age_hours} hours"})

            for row in result:
                stuck_syncs.append({
                    'sync_id': row.sync_id,
                    'account_type': row.account_type,
                    'started_at': row.started_at,
                    'hours_running': float(row.hours_running),
                    'offers_processed': int(row.total_offers_processed or 0)
                })

        logger.info(f"Found {len(stuck_syncs)} stuck sync processes (older than {max_age_hours}h)")
        return stuck_syncs

    except Exception as e:
        logger.error(f"Error finding stuck syncs: {e}")
        return []

def mark_sync_as_failed(sync_id, reason="Process stuck and terminated"):
    """Mark a sync as failed with detailed error information"""
    try:
        with get_db() as session:
            session.execute(text("""
                UPDATE app.emag_offer_syncs
                SET status = 'failed',
                    error_count = error_count + 1,
                    errors = array_append(COALESCE(errors, ARRAY[]::text[]), :reason),
                    updated_at = NOW()
                WHERE sync_id = :sync_id
            """), {
                "sync_id": sync_id,
                "reason": reason
            })
        logger.info(f"Marked sync {sync_id} as failed: {reason}")
        return True
    except Exception as e:
        logger.error(f"Error marking sync {sync_id} as failed: {e}")
        return False

def get_sync_health_status():
    """Get comprehensive sync health status"""
    try:
        with get_db() as session:
            # Get sync summary for different time periods
            periods = {
                'last_hour': '1 hour',
                'last_24h': '24 hours',
                'last_7d': '7 days'
            }

            health_data = {}

            for period_name, interval in periods.items():
                result = session.execute(text("""
                    SELECT
                        status,
                        COUNT(*) as count,
                        AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - started_at))/60) as avg_duration_min,
                        MAX(started_at) as latest_sync
                    FROM app.emag_offer_syncs
                    WHERE started_at >= NOW() - INTERVAL :interval
                    GROUP BY status
                    ORDER BY status
                """), {"interval": interval})

                period_data = {}
                latest_sync = None

                for row in result:
                    period_data[row.status] = {
                        'count': int(row.count),
                        'avg_duration_min': float(row.avg_duration_min or 0)
                    }
                    if row.latest_sync:
                        latest_sync = row.latest_sync

                health_data[period_name] = {
                    'status_counts': period_data,
                    'latest_sync': latest_sync
                }

            # Get currently running syncs
            running_result = session.execute(text("""
                SELECT sync_id, account_type, started_at,
                       EXTRACT(EPOCH FROM (NOW() - started_at))/60 as minutes_running,
                       total_offers_processed
                FROM app.emag_offer_syncs
                WHERE status = 'running'
                ORDER BY started_at ASC
            """))

            running_syncs = []
            for row in running_result:
                running_syncs.append({
                    'sync_id': row.sync_id,
                    'account_type': row.account_type,
                    'started_at': row.started_at,
                    'minutes_running': float(row.minutes_running),
                    'offers_processed': int(row.total_offers_processed or 0)
                })

            return {
                'running_syncs': running_syncs,
                'health_data': health_data,
                'total_running': len(running_syncs)
            }

    except Exception as e:
        logger.error(f"Error getting sync health status: {e}")
        return None

def cleanup_stuck_syncs(max_age_hours: int = 1):
    """Clean up stuck sync processes"""
    stuck_syncs = find_stuck_syncs(max_age_hours)
    recovered_count = 0

    for sync in stuck_syncs:
        reason = f"Auto-terminated: stuck for {sync['hours_running']:.1f} hours, processed {sync['offers_processed']} offers"
        logger.warning(f"Recovering stuck sync: {sync['sync_id']} - {reason}")

        if mark_sync_as_failed(sync['sync_id'], reason):
            recovered_count += 1
            logger.info(f"Successfully recovered stuck sync: {sync['sync_id']}")

    STUCK_SYNCS_COUNT.set(len(stuck_syncs))
    RECOVERED_SYNCS_COUNT.inc(recovered_count)

    if recovered_count > 0:
        logger.info(f"✅ Recovered {recovered_count} stuck sync processes")
    else:
        logger.info("ℹ️ No stuck syncs required recovery")

    return recovered_count

def log_sync_health():
    """Log current sync health status"""
    health = get_sync_health_status()

    if health:
        logger.info("=== eMAG Sync Health Status ===")
        logger.info(f"Currently running syncs: {health['total_running']}")

        # Log details of long-running syncs
        for sync in health['running_syncs']:
            if sync['minutes_running'] > 30:  # Warn about syncs running > 30 minutes
                logger.warning(f"Long-running sync: {sync['sync_id']} ({sync['account_type']}) - running for {sync['minutes_running']:.1f} minutes, processed {sync['offers_processed']} offers")

        # Log summary statistics
        last_24h = health['health_data']['last_24h']['status_counts']

        total_24h = sum(count['count'] for count in last_24h.values())
        completed_24h = last_24h.get('completed', {}).get('count', 0)
        failed_24h = last_24h.get('failed', {}).get('count', 0)

        if total_24h > 0:
            success_rate = (completed_24h / total_24h) * 100
            logger.info(f"24h Success Rate: {success_rate:.1f}% ({completed_24h}/{total_24h})")
            FAILED_SYNCS_LAST_HOUR.set(failed_24h)

        logger.info("================================")

        # Update Prometheus metrics
        MONITOR_STATUS.set(1)  # Running
        ACTIVE_SYNCS_COUNT.set(health['total_running'])
    else:
        logger.error("❌ Could not retrieve sync health status")
        MONITOR_STATUS.set(2)  # Error
        ACTIVE_SYNCS_COUNT.set(0)

async def monitor_syncs():
    """Main monitoring loop"""
    logger.info("🚀 Starting Enhanced eMAG Sync Monitor and Recovery System...")

    # Start Prometheus metrics server
    try:
        metrics_port = int(os.getenv("EMAG_SYNC_METRICS_PORT", "9108"))
        start_http_server(metrics_port)
        logger.info(f"📈 Prometheus metrics server started on :{metrics_port}")
    except OSError:
        # Already started in this process
        pass

    check_interval = int(os.getenv("EMAG_SYNC_MONITOR_INTERVAL", "300"))  # 5 minutes default
    stuck_threshold_hours = int(os.getenv("EMAG_SYNC_STUCK_THRESHOLD_HOURS", "1"))  # 1 hour default

    while not shutdown_requested:
        try:
            logger.info("🔍 Monitoring cycle started...")

            # Clean up stuck syncs with configurable threshold
            recovered = cleanup_stuck_syncs(stuck_threshold_hours)

            # Log health status
            log_sync_health()

            logger.info(f"✅ Monitor cycle completed. Recovered: {recovered}")

        except Exception as e:
            logger.error(f"❌ Error in monitor cycle: {e}")
            MONITOR_STATUS.set(2)  # Error

        # Wait for next cycle
        logger.info(f"⏰ Next check in {check_interval} seconds...")
        await asyncio.sleep(check_interval)

    logger.info("🛑 Enhanced Sync Monitor shutting down...")

def main():
    """Main entry point"""
    try:
        logger.info("🚀 Starting eMAG Sync Monitor and Recovery System...")
        MONITOR_STATUS.set(1)  # Running

        asyncio.run(monitor_syncs())

    except KeyboardInterrupt:
        logger.info("👋 Monitor interrupted by user")
    except Exception as e:
        logger.error(f"💥 Monitor failed with exception: {e}")
        MONITOR_STATUS.set(2)  # Error
        sys.exit(1)
    finally:
        MONITOR_STATUS.set(0)  # Idle

if __name__ == "__main__":
    main()
