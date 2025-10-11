"""Periodic cleanup tasks for the application."""

import asyncio
import logging
import os
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def idem_cleanup_loop(
    engine: AsyncEngine,
    interval: int = 300,
    batch_size: int = 1000,
) -> None:
    """Background task to clean up expired idempotency keys.

    Args:
        engine: SQLAlchemy async engine
        interval: How often to run the cleanup in seconds
        batch_size: Maximum number of rows to delete in one batch

    """
    if os.getenv("IDEMPOTENCY_CLEANUP", "0") != "1":
        logger.info("Idempotency cleanup is disabled (IDEMPOTENCY_CLEANUP != 1)")
        return

    logger.info("Starting idempotency key cleanup task")

    while True:
        try:
            start_time = datetime.now(UTC)

            async with engine.begin() as conn:
                # Log before deletion
                logger.info("Starting cleanup of expired idempotency keys...")

                # First, check how many keys would be deleted
                count_result = await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM app.idempotency_keys WHERE ttl_at < now()",
                    ),
                )
                count = count_result.scalar()
                logger.info(f"Found {count} expired idempotency keys to clean up")

                if count > 0:
                    # Perform the actual deletion
                    result = await conn.execute(
                        text(
                            """
                        DELETE FROM app.idempotency_keys
                        WHERE ttl_at < now()
                        AND key IN (
                            SELECT key FROM app.idempotency_keys
                            WHERE ttl_at < now()
                            LIMIT :batch_size
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING key, ttl_at
                        """,
                        ),
                        {"batch_size": batch_size},
                    )
                    deleted = result.rowcount
                    logger.info(
                        f"Successfully deleted {deleted} expired idempotency keys",
                    )

                    # Verify deletion
                    verify_result = await conn.execute(
                        text(
                            "SELECT COUNT(*) FROM app.idempotency_keys WHERE ttl_at < now()",
                        ),
                    )
                    remaining = verify_result.scalar()
                    if remaining > 0:
                        logger.warning(
                            f"Still found {remaining} expired keys after cleanup",
                        )

            duration = (datetime.now(UTC) - start_time).total_seconds()

            if count > 0:
                logger.info(
                    f"Cleaned up {deleted} expired idempotency keys "
                    f"in {duration:.3f} seconds",
                )
            else:
                logger.debug("No expired idempotency keys to clean up")

            # Sleep until next interval
            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info("Idempotency key cleanup task cancelled")
            break

        except Exception as e:
            logger.error(f"Error in idempotency key cleanup: {e}", exc_info=True)
            # Sleep before retrying on error
            await asyncio.sleep(min(60, interval))  # Max 1 minute delay on error
