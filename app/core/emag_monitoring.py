"""
eMAG Integration Monitoring and Metrics Collection.

This module provides comprehensive monitoring capabilities for eMAG integration
according to Section 2.4 and 2.6 from the eMAG Full Sync Guide.
"""

import json
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.emag_constants import MonitoringThresholds
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RequestMetric:
    """Individual request metric."""

    timestamp: float
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    account_type: str
    success: bool
    error_message: str | None = None
    error_code: str | None = None


@dataclass
class SyncMetrics:
    """Aggregated sync metrics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_response_time_ms: float = 0.0
    products_synced: int = 0
    offers_synced: int = 0
    orders_synced: int = 0
    errors_by_code: dict[str, int] = field(default_factory=dict)
    requests_by_endpoint: dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    @property
    def average_response_time_ms(self) -> float:
        """Calculate average response time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time_ms / self.total_requests


class EmagMonitor:
    """Monitor and track eMAG integration metrics."""

    def __init__(self, window_size_seconds: int = 300):
        """Initialize the monitor.

        Args:
            window_size_seconds: Time window for metrics (default 5 minutes)
        """
        self.window_size = window_size_seconds
        self._requests: deque[RequestMetric] = deque()
        self._sync_start_time: float | None = None
        self._current_sync_type: str | None = None

    def start_sync(self, sync_type: str):
        """Mark the start of a sync operation.

        Args:
            sync_type: Type of sync (products, offers, orders)
        """
        self._sync_start_time = time.time()
        self._current_sync_type = sync_type
        logger.info(f"Started {sync_type} sync monitoring")

    def end_sync(self):
        """Mark the end of a sync operation."""
        if self._sync_start_time:
            duration = time.time() - self._sync_start_time
            logger.info(f"Completed {self._current_sync_type} sync in {duration:.2f}s")
            self._sync_start_time = None
            self._current_sync_type = None

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        account_type: str,
        success: bool,
        error_message: str | None = None,
        error_code: str | None = None,
    ):
        """Record a single API request metric.

        Args:
            endpoint: API endpoint called
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            account_type: Account type (main, fbe)
            success: Whether the request was successful
            error_message: Error message if failed
            error_code: eMAG error code if available
        """
        metric = RequestMetric(
            timestamp=time.time(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            account_type=account_type,
            success=success,
            error_message=error_message,
            error_code=error_code,
        )

        self._requests.append(metric)
        self._cleanup_old_metrics()

        # Log structured request data (Section 2.4 requirement)
        log_entry = {
            "timestamp": datetime.fromtimestamp(metric.timestamp).isoformat(),
            "level": "INFO" if success else "ERROR",
            "service": "emag_integration",
            "request": {
                "method": method,
                "endpoint": endpoint,
                "account_type": account_type,
            },
            "response": {
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "success": success,
            },
        }

        if not success:
            log_entry["error"] = {
                "message": error_message,
                "code": error_code,
            }

        logger.info(json.dumps(log_entry))

    def _cleanup_old_metrics(self):
        """Remove metrics outside the time window."""
        cutoff_time = time.time() - self.window_size
        while self._requests and self._requests[0].timestamp < cutoff_time:
            self._requests.popleft()

    def get_metrics(self) -> SyncMetrics:
        """Get aggregated metrics for the current time window.

        Returns:
            SyncMetrics object with aggregated data
        """
        self._cleanup_old_metrics()

        metrics = SyncMetrics()

        for req in self._requests:
            metrics.total_requests += 1
            metrics.total_response_time_ms += req.response_time_ms

            if req.success:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1
                if req.error_code:
                    metrics.errors_by_code[req.error_code] = (
                        metrics.errors_by_code.get(req.error_code, 0) + 1
                    )

            if req.status_code == 429:
                metrics.rate_limit_hits += 1

            # Track requests by endpoint
            metrics.requests_by_endpoint[req.endpoint] = (
                metrics.requests_by_endpoint.get(req.endpoint, 0) + 1
            )

        return metrics

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status with alerts.

        Returns:
            Dictionary with health status and alerts
        """
        metrics = self.get_metrics()
        alerts = []
        status = "healthy"

        # Check error rate (Section 2.6 threshold)
        if metrics.error_rate > MonitoringThresholds.HIGH_ERROR_RATE * 100:
            alerts.append(
                {
                    "level": "error",
                    "message": f"High error rate: {metrics.error_rate:.2f}%",
                    "threshold": f"{MonitoringThresholds.HIGH_ERROR_RATE * 100}%",
                }
            )
            status = "error"

        # Check response time
        if metrics.average_response_time_ms > MonitoringThresholds.SLOW_RESPONSE_MS:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"Slow response time: {metrics.average_response_time_ms:.0f}ms",
                    "threshold": f"{MonitoringThresholds.SLOW_RESPONSE_MS}ms",
                }
            )
            if status == "healthy":
                status = "warning"

        # Check rate limiting
        rate_limit_rate = (
            metrics.rate_limit_hits / metrics.total_requests
            if metrics.total_requests > 0
            else 0
        )
        if rate_limit_rate > MonitoringThresholds.RATE_LIMIT_WARNING:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"High rate limit hits: {rate_limit_rate * 100:.1f}%",
                    "threshold": f"{MonitoringThresholds.RATE_LIMIT_WARNING * 100}%",
                }
            )
            if status == "healthy":
                status = "warning"

        # Check sync success rate
        if metrics.success_rate < MonitoringThresholds.SYNC_SUCCESS_RATE * 100:
            alerts.append(
                {
                    "level": "error",
                    "message": f"Low success rate: {metrics.success_rate:.2f}%",
                    "threshold": f"{MonitoringThresholds.SYNC_SUCCESS_RATE * 100}%",
                }
            )
            status = "error"

        return {
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": asdict(metrics),
            "alerts": alerts,
            "window_size_seconds": self.window_size,
        }

    def get_request_rate(self) -> float:
        """Get current request rate (requests per second).

        Returns:
            Requests per second in the current window
        """
        self._cleanup_old_metrics()
        if not self._requests:
            return 0.0

        time_span = time.time() - self._requests[0].timestamp
        if time_span == 0:
            return 0.0

        return len(self._requests) / time_span

    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent error details.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent error details
        """
        self._cleanup_old_metrics()

        errors = []
        for req in reversed(self._requests):
            if not req.success:
                errors.append(
                    {
                        "timestamp": datetime.fromtimestamp(req.timestamp).isoformat(),
                        "endpoint": req.endpoint,
                        "method": req.method,
                        "status_code": req.status_code,
                        "error_message": req.error_message,
                        "error_code": req.error_code,
                        "account_type": req.account_type,
                    }
                )
                if len(errors) >= limit:
                    break

        return errors

    def export_metrics(self, filepath: str):
        """Export metrics to JSON file for analysis.

        Args:
            filepath: Path to export file
        """
        metrics = self.get_metrics()
        health = self.get_health_status()
        recent_errors = self.get_recent_errors(50)

        export_data = {
            "export_timestamp": datetime.now(UTC).isoformat(),
            "window_size_seconds": self.window_size,
            "health_status": health,
            "metrics": asdict(metrics),
            "recent_errors": recent_errors,
            "request_rate_per_second": self.get_request_rate(),
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported metrics to {filepath}")


# Global monitor instance
_global_monitor: EmagMonitor | None = None


def get_monitor() -> EmagMonitor:
    """Get the global monitor instance.

    Returns:
        Global EmagMonitor instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = EmagMonitor()
    return _global_monitor


def reset_monitor():
    """Reset the global monitor instance."""
    global _global_monitor
    _global_monitor = None
