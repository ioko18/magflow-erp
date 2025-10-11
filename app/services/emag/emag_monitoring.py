"""
eMAG Integration Monitoring and Alerting Service.

Monitors eMAG API integration health, performance, and sends alerts
conforming to Section 2.6 from eMAG API guide.
"""

import asyncio
import logging
import statistics
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.emag_constants import MonitoringThresholds
from app.core.emag_rate_limiter import get_rate_limiter
from app.models.emag_models import EmagProductV2, EmagSyncLog

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and calculates metrics for monitoring."""

    def __init__(self, window_size: int = 300):
        """
        Initialize metrics collector.

        Args:
            window_size: Time window in seconds for metrics (default: 5 minutes)
        """
        self.window_size = window_size
        self.response_times = deque(maxlen=1000)
        self.errors = deque(maxlen=1000)
        self.requests = deque(maxlen=1000)
        self._lock = asyncio.Lock()

    async def record_request(self, response_time: float, success: bool):
        """
        Record an API request.

        Args:
            response_time: Response time in milliseconds
            success: Whether the request was successful
        """
        async with self._lock:
            now = datetime.now(UTC)
            self.requests.append(
                {"time": now, "response_time": response_time, "success": success}
            )
            self.response_times.append(response_time)
            if not success:
                self.errors.append(now)

    async def get_metrics(self) -> dict[str, Any]:
        """
        Get current metrics.

        Returns:
            Dictionary with calculated metrics
        """
        async with self._lock:
            now = datetime.now(UTC)
            cutoff = now - timedelta(seconds=self.window_size)

            # Filter recent requests
            recent_requests = [r for r in self.requests if r["time"] > cutoff]
            recent_errors = [e for e in self.errors if e > cutoff]

            total_requests = len(recent_requests)
            total_errors = len(recent_errors)

            # Calculate metrics
            metrics = {
                "requests_per_minute": total_requests / (self.window_size / 60),
                "error_rate": total_errors / total_requests
                if total_requests > 0
                else 0.0,
                "total_requests": total_requests,
                "total_errors": total_errors,
            }

            # Response time metrics
            if self.response_times:
                metrics["average_response_time"] = statistics.mean(self.response_times)
                metrics["median_response_time"] = statistics.median(self.response_times)
                metrics["max_response_time"] = max(self.response_times)
                metrics["min_response_time"] = min(self.response_times)
            else:
                metrics["average_response_time"] = 0.0
                metrics["median_response_time"] = 0.0
                metrics["max_response_time"] = 0.0
                metrics["min_response_time"] = 0.0

            return metrics


class EmagMonitoringService:
    """
    Monitoring service for eMAG integration.

    Tracks:
    - Request rate and response times
    - Error rates and types
    - Rate limit usage
    - Sync success rates
    - System health
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize monitoring service.

        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.metrics_collector = MetricsCollector()
        self.rate_limiter = get_rate_limiter()

        self.metrics = {
            "requests_per_minute": 0.0,
            "error_rate": 0.0,
            "average_response_time": 0.0,
            "rate_limit_usage": 0.0,
            "sync_success_rate": 0.0,
        }

        self.alerts = {
            "high_error_rate": False,
            "slow_response": False,
            "rate_limit_warning": False,
            "sync_failure": False,
        }

        self.alert_callbacks: list[Callable] = []

    def register_alert_callback(self, callback: Callable):
        """
        Register a callback for alerts.

        Args:
            callback: Async function to call when alerts are triggered
        """
        self.alert_callbacks.append(callback)

    async def update_metrics(self):
        """Update all monitoring metrics."""
        try:
            # Get metrics from collector
            collector_metrics = await self.metrics_collector.get_metrics()
            self.metrics.update(collector_metrics)

            # Get rate limiter stats
            rate_stats = await self.rate_limiter.get_stats()
            self.metrics["rate_limit_usage"] = max(
                rate_stats.get("orders_rpm_usage", 0.0),
                rate_stats.get("other_rpm_usage", 0.0),
            )

            # Get sync success rate from database
            sync_success_rate = await self._calculate_sync_success_rate()
            self.metrics["sync_success_rate"] = sync_success_rate

            # Check alerts
            await self._check_alerts()

            logger.debug(f"Metrics updated: {self.metrics}")

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def _calculate_sync_success_rate(self) -> float:
        """
        Calculate sync success rate from recent sync logs.

        Returns:
            Success rate (0.0 to 1.0)
        """
        try:
            # Get sync logs from last hour
            one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

            result = await self.db_session.execute(
                select(
                    func.count(EmagSyncLog.id).label("total"),
                    func.sum(
                        func.cast(EmagSyncLog.status == "completed", type_=int)
                    ).label("successful"),
                ).where(EmagSyncLog.started_at >= one_hour_ago)
            )

            row = result.first()
            if row and row.total > 0:
                return (row.successful or 0) / row.total

            return 1.0  # No syncs = 100% success

        except Exception as e:
            logger.error(f"Error calculating sync success rate: {e}")
            return 0.0

    async def _check_alerts(self):
        """Check if any alert conditions are met."""
        previous_alerts = self.alerts.copy()

        # Check error rate
        self.alerts["high_error_rate"] = (
            self.metrics["error_rate"] > MonitoringThresholds.HIGH_ERROR_RATE
        )

        # Check response time
        self.alerts["slow_response"] = (
            self.metrics["average_response_time"]
            > MonitoringThresholds.SLOW_RESPONSE_MS
        )

        # Check rate limit usage
        self.alerts["rate_limit_warning"] = (
            self.metrics["rate_limit_usage"] > MonitoringThresholds.RATE_LIMIT_WARNING
        )

        # Check sync success rate
        self.alerts["sync_failure"] = (
            self.metrics["sync_success_rate"] < MonitoringThresholds.SYNC_SUCCESS_RATE
        )

        # Send alerts if any new alerts triggered
        new_alerts = {
            key: value
            for key, value in self.alerts.items()
            if value and not previous_alerts.get(key, False)
        }

        if new_alerts:
            await self._send_alerts(new_alerts)

    async def _send_alerts(self, alerts: dict[str, bool]):
        """
        Send alerts to registered callbacks.

        Args:
            alerts: Dictionary of triggered alerts
        """
        alert_messages = []

        if alerts.get("high_error_rate"):
            alert_messages.append(
                f"⚠️ High error rate: {self.metrics['error_rate']:.2%} "
                f"(threshold: {MonitoringThresholds.HIGH_ERROR_RATE:.2%})"
            )

        if alerts.get("slow_response"):
            alert_messages.append(
                f"⚠️ Slow response time: {self.metrics['average_response_time']:.0f}ms "
                f"(threshold: {MonitoringThresholds.SLOW_RESPONSE_MS}ms)"
            )

        if alerts.get("rate_limit_warning"):
            alert_messages.append(
                f"⚠️ High rate limit usage: {self.metrics['rate_limit_usage']:.2%} "
                f"(threshold: {MonitoringThresholds.RATE_LIMIT_WARNING:.2%})"
            )

        if alerts.get("sync_failure"):
            alert_messages.append(
                f"⚠️ Low sync success rate: {self.metrics['sync_success_rate']:.2%} "
                f"(threshold: {MonitoringThresholds.SYNC_SUCCESS_RATE:.2%})"
            )

        # Log alerts
        for message in alert_messages:
            logger.warning(message)

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alerts, alert_messages)
            except Exception as e:
                logger.error(f"Error calling alert callback: {e}")

    async def get_health_status(self) -> dict[str, Any]:
        """
        Get overall health status.

        Returns:
            Dictionary with health status and details
        """
        await self.update_metrics()

        # Calculate health score (0-100)
        health_score = 100.0

        if self.alerts["high_error_rate"]:
            health_score -= 30
        if self.alerts["slow_response"]:
            health_score -= 20
        if self.alerts["rate_limit_warning"]:
            health_score -= 20
        if self.alerts["sync_failure"]:
            health_score -= 30

        health_score = max(0, health_score)

        # Determine status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "degraded"
        elif health_score >= 50:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "health_score": health_score,
            "metrics": self.metrics,
            "alerts": self.alerts,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def get_sync_statistics(self) -> dict[str, Any]:
        """
        Get synchronization statistics.

        Returns:
            Dictionary with sync statistics
        """
        try:
            # Last 24 hours
            yesterday = datetime.now(UTC) - timedelta(days=1)

            # Total syncs
            result = await self.db_session.execute(
                select(func.count(EmagSyncLog.id)).where(
                    EmagSyncLog.started_at >= yesterday
                )
            )
            total_syncs = result.scalar() or 0

            # Successful syncs
            result = await self.db_session.execute(
                select(func.count(EmagSyncLog.id)).where(
                    and_(
                        EmagSyncLog.started_at >= yesterday,
                        EmagSyncLog.status == "completed",
                    )
                )
            )
            successful_syncs = result.scalar() or 0

            # Failed syncs
            result = await self.db_session.execute(
                select(func.count(EmagSyncLog.id)).where(
                    and_(
                        EmagSyncLog.started_at >= yesterday,
                        EmagSyncLog.status == "failed",
                    )
                )
            )
            failed_syncs = result.scalar() or 0

            # Average duration
            result = await self.db_session.execute(
                select(func.avg(EmagSyncLog.duration_seconds)).where(
                    and_(
                        EmagSyncLog.started_at >= yesterday,
                        EmagSyncLog.status == "completed",
                    )
                )
            )
            avg_duration = result.scalar() or 0.0

            # Total items processed
            result = await self.db_session.execute(
                select(func.sum(EmagSyncLog.processed_items)).where(
                    EmagSyncLog.started_at >= yesterday
                )
            )
            total_items = result.scalar() or 0

            return {
                "total_syncs": total_syncs,
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs,
                "success_rate": successful_syncs / total_syncs
                if total_syncs > 0
                else 0.0,
                "average_duration_seconds": float(avg_duration),
                "total_items_processed": total_items,
                "period": "24h",
            }

        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return {}

    async def get_product_statistics(self) -> dict[str, Any]:
        """
        Get product statistics.

        Returns:
            Dictionary with product statistics
        """
        try:
            # Total products
            result = await self.db_session.execute(select(func.count(EmagProductV2.id)))
            total_products = result.scalar() or 0

            # Active products
            result = await self.db_session.execute(
                select(func.count(EmagProductV2.id)).where(EmagProductV2.is_active)
            )
            active_products = result.scalar() or 0

            # Products by account
            result = await self.db_session.execute(
                select(
                    EmagProductV2.account_type, func.count(EmagProductV2.id)
                ).group_by(EmagProductV2.account_type)
            )
            by_account = {row[0]: row[1] for row in result}

            # Products synced in last 24h
            yesterday = datetime.now(UTC) - timedelta(days=1)
            result = await self.db_session.execute(
                select(func.count(EmagProductV2.id)).where(
                    EmagProductV2.last_synced_at >= yesterday
                )
            )
            recently_synced = result.scalar() or 0

            return {
                "total_products": total_products,
                "active_products": active_products,
                "inactive_products": total_products - active_products,
                "by_account": by_account,
                "recently_synced_24h": recently_synced,
            }

        except Exception as e:
            logger.error(f"Error getting product statistics: {e}")
            return {}

    async def record_api_request(self, response_time: float, success: bool):
        """
        Record an API request for metrics.

        Args:
            response_time: Response time in milliseconds
            success: Whether the request was successful
        """
        await self.metrics_collector.record_request(response_time, success)
