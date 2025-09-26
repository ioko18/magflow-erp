import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError

# Import core modules
from app.core.config import settings

try:
    # Optional dependency: allow app to start even if dependency_injector is not installed
    from app.core.container import container
except Exception:  # ModuleNotFoundError or any import-time error inside container
    container = None  # Fallback: DI wiring is disabled
from app.api.health import router as health_router
from app.api.v1.api import api_router as v1_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.well_known import router as well_known_router
from app.core.error_handling import register_exception_handlers
from app.core.rate_limiting import init_rate_limiter
from app.core.logging_config import configure_logging, get_logger
from app.middleware.compression import CompressionMiddleware
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.logging_middleware import setup_logging_middleware

# Initialize logging
configure_logging()
logger = get_logger(__name__)

# Initialize Sentry (if configured)
try:
    if hasattr(settings, 'SENTRY_DSN') and settings.SENTRY_DSN:
        from app.core.sentry import init_sentry
        init_sentry()
except Exception as e:
    logger.warning(f"Failed to initialize Sentry: {e}")

# Global Redis client
redis_client: Optional[Redis] = None

async def setup_redis() -> Redis:
    """Initialize Redis connection for rate limiting."""
    global redis_client
    logger = get_logger(__name__)
    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to Redis (attempt {attempt + 1}/{max_retries})...")
            
            # Create a new Redis client
            client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                ssl=settings.REDIS_SSL,
                ssl_cert_reqs=settings.REDIS_SSL_CERT_REQS,
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )
            
            # Test the connection
            await client.ping()
            logger.info("Successfully connected to Redis")
            return client
        except (ConnectionError, RedisError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Redis after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)

def setup_opentelemetry(app: FastAPI, enable_sqlalchemy_instrumentation: bool = True) -> None:
    """Configure OpenTelemetry for the application."""
    from app.core.tracing import setup_tracing
    setup_tracing(app, enable_sqlalchemy_instrumentation=enable_sqlalchemy_instrumentation)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Application starting up...")

    # Initialize Redis (only if enabled)
    global redis_client
    if settings.REDIS_ENABLED:
        try:
            redis_client = await setup_redis()
        except Exception as e:
            logger.warning(f"Redis init failed; continuing without Redis: {e}")
            redis_client = None
    else:
        logger.info("Redis is disabled, skipping Redis initialization")
        redis_client = None

    logger.info(
        "Application startup complete",
        extra={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "version": settings.VERSION,
        },
    )

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Close Redis connection
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

    logger.info("Application shutdown complete")

# Initialize FastAPI app with lifespan
app = FastAPI(
    lifespan=lifespan,
    title="MagFlow ERP API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    description="""
    ## MagFlow ERP System

    Enterprise Resource Planning system with JWT authentication and RBAC.

    ### Authentication

    1. Get your access token from `/auth/login`
    2. Use the token in the `Authorization` header: `Bearer <token>`
    """,
    version="1.0.0",
    contact={
        "name": "Support",
        "email": "support@magflow.com",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://magflow.com/license",
    },
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CompressionMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(IdempotencyMiddleware)

# Setup logging middleware
setup_logging_middleware(app)

# Register exception handlers
register_exception_handlers(app)

# Initialize lightweight rate limiter used in integration tests,
# enabling rate limiting for health endpoints as expected by integration tests
init_rate_limiter(app, rate_limit_health=True)

# Setup OpenTelemetry
if hasattr(settings, 'OTEL_ENABLED') and settings.OTEL_ENABLED:
    setup_opentelemetry(app)

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(v1_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(well_known_router, prefix="/.well-known", tags=["well-known"])

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their responses."""
    logger.info(
        "Request received",
        extra={
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
        },
    )

    try:
        response = await call_next(request)
        logger.info(
            "Response sent",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
            },
        )
        return response
    except Exception as e:
        logger.exception(
            "Request failed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "error": str(e),
            },
        )
        raise

# Health check endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint that returns a welcome message."""
    return {
        "message": "Welcome to MagFlow ERP API",
        "version": "1.0.0",
        "docs": "/docs",
    }

# Add a test Redis endpoint
@app.get("/test-redis", include_in_schema=False)
async def test_redis():
    """Test Redis connection."""
    if not redis_client:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": "Redis not available"},
        )

    try:
        # Test Redis connection
        await redis_client.ping()
        return {"status": "success", "message": "Redis is connected"}
    except Exception as e:
        logger.error(f"Redis test failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": str(e)},
        )

# Add a test database endpoint
@app.get("/test-db", include_in_schema=False)
async def test_db():
    """Test database connection."""
    from sqlalchemy import text
    from app.core.database import get_async_session

    try:
        async for session in get_async_session():
            result = await session.execute(text("SELECT 1"))
            return {"status": "success", "message": "Database is connected", "data": result.scalar()}
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": str(e)},
        )

# Add a test endpoint to check environment variables
@app.get("/env", include_in_schema=False)
async def get_env():
    """Get environment variables (for debugging)."""
    return {
        "REDIS_HOST": settings.REDIS_HOST,
        "REDIS_PORT": settings.REDIS_PORT,
        "REDIS_DB": settings.REDIS_DB,
        "REDIS_SSL": settings.REDIS_SSL,
        "REDIS_URL": settings.REDIS_URL,
        "DATABASE_URL": settings.DATABASE_URL,
    }
