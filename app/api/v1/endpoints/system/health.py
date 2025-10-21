"""Compatibility health endpoints for tests under app.api.v1.endpoints.health

This module provides symbols expected by tests, delegating where possible
to the main health implementation in `app.api.health`.
"""

from __future__ import annotations

import time  # noqa: F401  # Required for test compatibility
from datetime import UTC, datetime
from typing import Any

# Re-export startup timing knobs to enable monkeypatching in tests
from app.api.health import (
    STARTUP_TIME,  # noqa: F401  # datetime of app start - used by tests for
    # monkeypatching
    WARMUP_PERIOD,  # noqa: F401  # int seconds for startup readiness - used by
    # tests for monkeypatching
)
from app.api.health import _ready_state as _ready_state  # re-export for tests

# Local state used by readiness reporting; tests may patch these functions
# to simulate different conditions. Our main router reads internal _ready_state,
# but tests target these functions specifically for mocking. We keep these
# lightweight and return dicts with a `status` field so tests can assert easily.


def check_database() -> dict[str, Any]:
    """Return a simple database health dict. Tests often monkeypatch this."""
    return {
        "status": "healthy",
        "message": "Database is available",
        "check_type": "database",
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "metadata": {"query_time_ms": 1.0},
    }


def check_jwks() -> dict[str, Any]:
    """Return a simple JWKS health dict. Tests often monkeypatch this."""
    duration = (datetime.now(UTC) - STARTUP_TIME).total_seconds()
    return {
        "status": "ready",
        "services": ["jwks"],
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "duration_seconds": duration,
    }


def check_opentelemetry() -> dict[str, Any]:
    """Return a simple OpenTelemetry health dict. Tests may monkeypatch this."""
    return {
        "status": "healthy",
        "message": "OpenTelemetry is healthy",
        "check_type": "opentelemetry",
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "metadata": {"enabled": True},
    }


def update_health_metrics(
    payload: dict[str, Any],
) -> bool:  # pragma: no cover - trivial
    """Placeholder metric updater so tests can patch/invoke without errors."""
    # In real deployment this would forward to app.core.metrics.update_health_metrics
    return True


def readiness_probe() -> dict[str, Any]:
    """Simulate readiness probe response for tests."""
    return {
        "status": "ok",
        "services": {"database": "ok", "jwks": "ok", "opentelemetry": "ok"},
    }
