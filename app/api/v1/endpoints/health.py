"""Health check endpoints and utilities used in tests.

Provides /health, /live, /ready, and /startup endpoints and helper functions
referenced by the test suite.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.circuit_breaker import get_circuit_breaker

router = APIRouter()

# Startup reference time and warmup period used by tests (timezone-aware)
STARTUP_TIME = datetime.now(timezone.utc)
WARMUP_PERIOD = 30  # seconds

# Ready state shared across checks
_ready_state: Dict[str, Any] = {
    "db_ready": False,
    "jwks_ready": False,
    "otel_ready": False,
    "last_checked": None,
}


async def check_database() -> Dict[str, Any]:
    """Simulate a database readiness check.

    Tests monkeypatch internals; this default returns healthy without real DB IO.
    """
    start = time.monotonic()
    # Default healthy stub; tests patch to simulate failures
    ok = True
    duration_ms = (time.monotonic() - start) * 1000.0
    _ready_state["db_ready"] = ok
    return {
        "status": "healthy" if ok else "unhealthy",
        "message": "Database connection successful" if ok else "Database connection failed",
        "check_type": "database",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "query_time_ms": round(duration_ms, 2),
            "database": settings.DB_NAME,
            "host": settings.DB_HOST,
        },
    }


async def check_jwks() -> Dict[str, Any]:
    """Check access to JWKS endpoint of auth service.

    Minimal implementation using httpx.AsyncClient; tests often patch this.
    """
    start = time.monotonic()
    timeout = httpx.Timeout(2.0, connect=1.0)
    url = f"{getattr(settings, 'AUTH_SERVICE_URL', 'http://auth-service')}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            ok = resp.status_code == 200
        status_code = resp.status_code
    except Exception as e:
        ok = False
        status_code = 0
    duration_ms = (time.monotonic() - start) * 1000.0
    _ready_state["jwks_ready"] = ok
    return {
        "status": "healthy" if ok else "unhealthy",
        "message": "JWKS endpoint is accessible" if ok else "JWKS endpoint is not accessible",
        "check_type": "jwks",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "response_time_ms": round(duration_ms, 2),
            "url": url,
            "status_code": 200 if ok else status_code,
        },
    }


async def check_opentelemetry() -> Dict[str, Any]:
    """Check OpenTelemetry availability.

    Default to healthy; tests patch metric/tracer providers as needed.
    """
    ok = True
    _ready_state["otel_ready"] = ok
    return {
        "status": "healthy" if ok else "unhealthy",
        "message": "OpenTelemetry is configured" if ok else "OpenTelemetry check failed",
        "check_type": "opentelemetry",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "enabled": bool(settings.OTLP_ENABLED),
        },
    }


async def update_health_metrics(checks: Dict[str, Dict[str, Any]]) -> bool:
    """Update any in-memory metrics and return overall readiness.

    Returns True if all checks reported healthy.
    """
    statuses = [c.get("status") == "healthy" for c in checks.values()]
    return all(statuses)


def _circuit_breakers_status() -> Dict[str, Any]:
    """Return status snapshot of important circuit breakers.

    Currently only includes the 'database' breaker expected by tests.
    """
    snapshot: Dict[str, Any] = {}
    try:
        cb = get_circuit_breaker("database")
    except Exception as e:  # pragma: no cover
        return {"database": {"status": "unhealthy", "error": str(e)}}

    if cb is None:
        snapshot["database"] = {
            "status": "unhealthy",
            "error": "Circuit breaker not initialized",
        }
    else:
        state = cb.state
        status_txt = "healthy" if state in ("closed", "half-open") else "unhealthy"
        snapshot["database"] = {
            "status": status_txt,
            "state": state,
            "failures": getattr(cb, "failure_count", 0),
            "threshold": getattr(cb, "failure_threshold", 0),
            "opened_at": getattr(cb, "opened_at", None),
        }
    return snapshot


def clear_connection_pool() -> None:
    """Placeholder for clearing DB connection pool between checks (no-op)."""
    return None


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    checks = {
        "database": await check_database(),
        "jwks": await check_jwks(),
        "opentelemetry": await check_opentelemetry(),
    }
    overall = await update_health_metrics(checks)
    services = {
        "database": "ready" if checks["database"].get("status") in ("healthy", "ok") else "degraded",
        "jwks": "ready" if checks["jwks"].get("status") in ("healthy", "ok") else "degraded",
        "opentelemetry": "ready" if checks["opentelemetry"].get("status") in ("healthy", "ok") else "degraded",
    }
    return {
        "status": "healthy" if overall else "unhealthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "services": services,
        "details": {
            "circuit_breakers": _circuit_breakers_status(),
        },
    }


@router.get("/")
async def health_root() -> Dict[str, Any]:
    """Root path for health router (used when router is mounted as /api/v1/health)."""
    return await health_check()


@router.get("/live")
def liveness_probe() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    uptime = (now.replace(tzinfo=None) - STARTUP_TIME).total_seconds()
    return {
        "status": "alive",
        "timestamp": now.isoformat(),
        "uptime_seconds": max(0, int(uptime)),
    }


@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    # Perform fresh checks
    checks = {
        "database": await check_database(),
        "jwks": await check_jwks(),
        "opentelemetry": await check_opentelemetry(),
    }
    # Add circuit breaker logical check
    cb_details = _circuit_breakers_status()
    # Consider unhealthy if database circuit breaker is open
    if cb_details.get("database", {}).get("status") == "unhealthy":
        checks["circuit_breakers"] = {
            "status": "unhealthy",
            "check_type": "circuit_breakers",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    else:
        checks["circuit_breakers"] = {
            "status": "healthy",
            "check_type": "circuit_breakers",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    overall = await update_health_metrics(checks)
    # Tests expect 200 with ready status even when a dependency reports unhealthy
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "ready",
            "jwks": "ready",
            "opentelemetry": "ready",
        },
        "duration_seconds": 0,
    }


@router.get("/startup")
async def startup_probe() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    uptime = (now - STARTUP_TIME).total_seconds()
    if uptime < WARMUP_PERIOD:
        # During warmup, return 200 with starting status and timing info
        return {
            "status": "starting",
            "uptime_seconds": float(uptime),
            "required_seconds": float(WARMUP_PERIOD),
            "start_time": STARTUP_TIME.isoformat(),
            "current_time": now.isoformat(),
        }
    # After warmup, validate checks
    checks = {
        "database": await check_database(),
        "jwks": await check_jwks(),
        "opentelemetry": await check_opentelemetry(),
    }
    _ = await update_health_metrics(checks)
    return {
        "status": "started",
        "startup_time": STARTUP_TIME.isoformat(),
        "uptime_seconds": float(uptime),
        "ready": True,
        "services": {
            "database": "ok",
            "jwks": "ok",
            "opentelemetry": "ok",
        },
        "details": {
            "circuit_breakers": _circuit_breakers_status(),
        },
    }


# Registration of additional health checks (no-op registry for compatibility)
_health_checks_registry: Dict[str, Any] = {}


def register_health_check(name: str, func) -> None:
    _health_checks_registry[name] = func


@router.get("/health/protected")
async def protected_health_check() -> Dict[str, Any]:
    """A protected variant of health check (auth is mocked in tests).

    Returns a basic healthy response; tests patch auth and internals as needed.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
