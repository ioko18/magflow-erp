import asyncio
import logging
import socket
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiodns
import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.db_health import get_database_health
from app.core.metrics import update_database_metrics, update_health_metrics

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Cache health check results for 30 seconds
HEALTH_CHECK_CACHE_TTL = 30
health_check_cache = {}
health_check_time = 0

# Pydantic models for health check responses
class HealthCheckResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

class DatabaseHealthCheck(BaseModel):
    status: str
    connection: Dict[str, Any]
    migrations: Dict[str, Any]
    metrics: Dict[str, Any]

class JWKSHealthCheck(BaseModel):
    ok: bool
    keys_count: int = 0
    url: str
    error: Optional[str] = None
    response_time_ms: Optional[float] = None

class FullHealthCheckResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    db: DatabaseHealthCheck
    jwks: JWKSHealthCheck
    version: str = settings.APP_VERSION
    environment: str = settings.ENVIRONMENT


async def resolve_dns(hostname: str) -> Tuple[List[str], Optional[str]]:
    """Resolve a hostname to a list of IP addresses."""
    try:
        # First try using aiodns for async DNS resolution
        resolver = aiodns.DNSResolver()
        result = await resolver.gethostbyname(hostname, socket.AF_UNSPEC)
        return result.addresses, None
    except aiodns.error.DNSError:
        try:
            # Fall back to socket.gethostbyname if aiodns fails
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, socket.gethostbyname_ex, hostname)
            return result[2], None  # Return the list of IP addresses
        except socket.gaierror as e:
            return [], f"DNS resolution failed: {str(e)}"
    except Exception as e:
        return [], f"Unexpected error during DNS resolution: {str(e)}"

async def check_database_health() -> DatabaseHealthCheck:
    """Check database connectivity with DNS resolution."""
    from app.core.config import settings
    
    # Get database host and resolve it
    db_host = settings.DB_HOST
    resolved_ips, dns_error = await resolve_dns(db_host)
    
    if dns_error or not resolved_ips:
        return DatabaseHealthCheck(
            ok=False,
            dsn_host=db_host,
            resolved_ips=[],
            error=f"DNS resolution failed: {dns_error or 'No IP addresses found'}"
        )
    
    # Prepare the database URL with the actual host
    db_url = settings.database_url_async
    
    # Create a new engine for the health check
    engine = create_async_engine(
        db_url,
        **settings.database_connection_args,
        connect_args=settings.get_async_db_connect_args(for_health_check=True)
    )
    
    try:
        async with engine.connect() as conn:
            # Simple query to check connectivity
            await conn.execute(text("SELECT 1"))
            await conn.execute(text("SET search_path TO app,public"))
            
            return DatabaseHealthCheck(
                ok=True,
                dsn_host=db_host,
                resolved_ips=resolved_ips,
            )
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        return DatabaseHealthCheck(
            ok=False,
            dsn_host=db_host,
            resolved_ips=resolved_ips,
            error=f"Database connection failed: {str(e)}"
        )
    finally:
        await engine.dispose()

async def check_jwks_health() -> JWKSHealthCheck:
    """Check JWKS endpoint availability and key count."""
    from app.core.config import settings
    
    url = settings.JWKS_URL
    min_keys = settings.JWKS_MIN_KEYS
    timeout = settings.JWKS_TIMEOUT
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            jwks_data = response.json()
            
            keys = jwks_data.get("keys", [])
            keys_count = len(keys)
            
            if keys_count < min_keys:
                return JWKSHealthCheck(
                    ok=False,
                    keys_count=keys_count,
                    url=url,
                    error=f"Insufficient keys: expected at least {min_keys}, got {keys_count}"
                )
                
            return JWKSHealthCheck(
                ok=True,
                keys_count=keys_count,
                url=url
            )
    except httpx.HTTPStatusError as e:
        return JWKSHealthCheck(
            ok=False,
            keys_count=0,
            url=url,
            error=f"HTTP error: {e.response.status_code} - {str(e)}"
        )
    except Exception as e:
        return JWKSHealthCheck(
            ok=False,
            keys_count=0,
            url=url,
            error=f"Error fetching JWKS: {str(e)}"
        )

async def check_migrations() -> Dict[str, Any]:
    """Check if database migrations are up to date."""
    # This is a placeholder for the migration check
    # In a real implementation, you would check if all migrations have been applied
    return {
        "status": "ok",
        "migrations_up_to_date": True,
    }

@router.get("/health", response_model=HealthCheckResponse)
async def health() -> Dict[str, str]:
    """
    Basic health check endpoint.
    
    This is a lightweight check that only verifies the API is running.
    For a full system health check, use /health/full
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/health/database", response_model=DatabaseHealthCheck)
async def database_health() -> Dict[str, Any]:
    """
    Database health check endpoint.
    
    Returns detailed information about the database connection status,
    migrations, and performance metrics.
    """
    health_data = await get_database_health()
    
    # Update metrics
    update_database_metrics(health_data)
    
    return health_data

@router.get("/health/full", response_model=FullHealthCheckResponse)
async def full_health_check() -> Dict[str, Any]:
    """
    Full system health check that verifies all critical dependencies:
    - Database connection and performance
    - Database migrations status
    - JWKS endpoint availability
    - System metrics
    
    Returns:
        FullHealthCheckResponse: Detailed health status with individual component statuses
    """
    global health_check_cache, health_check_time
    
    # Check if we have a cached result that's still valid
    current_time = time.time()
    if current_time - health_check_time < HEALTH_CHECK_CACHE_TTL and health_check_cache:
        return health_check_cache
    
    # Run health checks in parallel
    db_health, jwks_check = await asyncio.gather(
        get_database_health(),
        check_jwks_health()
    )
    
    # Determine overall status
    overall_status = "ok"
    if db_health["status"] == "unhealthy" or not jwks_check.ok:
        overall_status = "unhealthy"
    elif db_health["status"] == "degraded":
        overall_status = "degraded"
    
    # Prepare response
    response = {
        "status": overall_status,
        "db": db_health,
        "jwks": jwks_check.dict(),
        "version": getattr(settings, "APP_VERSION", "unknown"),
        "environment": getattr(settings, "ENVIRONMENT", "development")
    }
    
    # Cache the result
    health_check_cache = response
    health_check_time = current_time
    
    # Update metrics
    update_health_metrics({
        "status": overall_status,
        "duration_ms": (time.time() - current_time) * 1000
    })
    update_database_metrics(db_health)
    
    return response
