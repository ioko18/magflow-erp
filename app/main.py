import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# from sentry_sdk import set_user
# OpenTelemetry instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
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
from app.core.logging_config import configure_logging, get_logger
from app.core.sentry import init_sentry
from app.middleware.compression import CompressionMiddleware
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.logging_middleware import setup_logging_middleware

# Import metrics
# from app.telemetry.otel_metrics import get_metrics_router

# Initialize logging and error tracking
configure_logging()
logger = get_logger(__name__)

# Initialize Sentry if configured
init_sentry()

# Global Redis client instance
redis_client: Optional[Redis] = None


async def setup_redis() -> Redis:
    """Initialize Redis connection for rate limiting."""
    logger = get_logger(__name__)
    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to Redis (attempt {attempt + 1}/{max_retries})...")
            global redis_client
            redis_client = Redis(
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
            await redis_client.ping()
            logger.info("Successfully connected to Redis")
            return redis_client
        except (ConnectionError, RedisError) as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"Failed to connect to Redis after {max_retries} attempts: {e}",
                )
                raise
            logger.warning(
                f"Redis connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...",
            )
            await asyncio.sleep(retry_delay)


def setup_opentelemetry(app: FastAPI, enable_sqlalchemy_instrumentation: bool = True) -> None:
    """Configure OpenTelemetry for the application.

    This is now a thin wrapper around our custom tracing setup in app.core.tracing
    to maintain backward compatibility.

    Args:
        app: The FastAPI application instance
        enable_sqlalchemy_instrumentation: Whether to enable SQLAlchemy instrumentation

    """
    if not settings.ENABLE_OTEL or not os.getenv("DOCKER_CONTAINER"):
        logger.info("OpenTelemetry is disabled or not in Docker container")
        return

    try:
        # Our custom tracing setup is already configured in app/__init__.py
        # This is just for backward compatibility and to instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/metrics,.well-known",
        )

        # Instrument Redis
        RedisInstrumentor().instrument()

        logger.info("OpenTelemetry instrumentation configured successfully")

    except Exception as e:
        logger.error("Failed to configure OpenTelemetry: %s", str(e), exc_info=True)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured FastAPI application with all middleware and error handling configured

    """
    # OpenAPI metadata
    openapi_tags = [
        {
            "name": "auth",
            "description": "Authentication and user management",
            "externalDocs": {
                "description": "JWT Authentication Guide",
                "url": "https://jwt.io/introduction/",
            },
        },
        {
            "name": "products",
            "description": "Product management",
        },
        {
            "name": "categories",
            "description": "Category management",
        },
        {
            "name": "health",
            "description": "Health checks and monitoring",
        },
        {
            "name": "Database Monitoring",
            "description": "Database health and performance monitoring",
        },
        {
            "name": "errors",
            "description": "Error handling and troubleshooting",
        },
    ]

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Initialize dependency injection container (if available)
        if container is not None:
            try:
                container.init_resources()
            except Exception as e:
                logger.warning("DI container init failed: %s", e)

        # Initialize Redis (non-fatal)
        global redis_client
        try:
            redis_client = await setup_redis()
        except Exception as e:
            logger.warning("Redis init failed; continuing without Redis: %s", e)
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

        ### Rate Limiting

        - 1000 requests per minute per IP
        - 100 requests per minute per user
        - 10 requests per second burst limit

        ### Idempotency

        - Use `Idempotency-Key` header for POST/PUT/PATCH/DELETE
        - Keys are valid for 24 hours
        """,
        version="1.0.0",
        contact={
            "name": "API Support",
            "email": "support@magflow.example.com",
            "url": "https://magflow.example.com/support",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://magflow.example.com/license",
        },
        openapi_tags=openapi_tags,
        servers=[
            {
                "url": "https://api.magflow.example.com",
                "description": "Production server",
            },
            {"url": "http://localhost:8000", "description": "Local development"},
        ],
    )

    # Security scheme
    security_schemes = {
        "OAuth2PasswordBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token (only the token, without 'Bearer ' prefix)",
        },
    }

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        # Import schemas here to avoid circular imports
        # from app.schemas.errors import (
        #     Problem,
        #     ValidationProblem,
        #     UnauthorizedProblem,
        #     ForbiddenProblem,
        #     NotFoundProblem,
        #     ConflictProblem,
        #     TooManyRequestsProblem,
        #     InternalServerErrorProblem,
        #     ServiceUnavailableProblem,
        # )

        # Get base OpenAPI schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )

        # Add components for error responses
        # openapi_schema.setdefault("components", {}).setdefault("schemas", {}).update(
        #     {
        #         "Problem": Problem.schema(ref_template="#/components/schemas/{model}"),
        #         "ValidationProblem": ValidationProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #         "UnauthorizedProblem": UnauthorizedProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #         "ForbiddenProblem": ForbiddenProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #         "NotFoundProblem": NotFoundProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #         "ConflictProblem": ConflictProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #         "TooManyRequestsProblem": TooManyRequestsProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #         "InternalServerErrorProblem": InternalServerErrorProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #         "ServiceUnavailableProblem": ServiceUnavailableProblem.schema(
        #             ref_template="#/components/schemas/{model}"
        #         ),
        #     }
        # )

        # Add error response examples
        openapi_schema.setdefault("components", {}).setdefault("examples", {}).update(
            {
                "validation-error": {
                    "summary": "Validation Error Example",
                    "value": {
                        "type": "https://example.com/probs/validation-error",
                        "title": "Validation Error",
                        "status": 422,
                        "detail": "Your request contains invalid parameters",
                        "instance": "/api/v1/resource/123",
                        "errors": [
                            {
                                "field": "email",
                                "message": "Not a valid email address",
                                "error_code": "invalid_email",
                            },
                        ],
                    },
                },
                "unauthorized-error": {
                    "summary": "Unauthorized Error Example",
                    "value": {
                        "type": "https://example.com/probs/unauthorized",
                        "title": "Unauthorized",
                        "status": 401,
                        "detail": "Authentication credentials were not provided",
                        "instance": "/api/v1/protected-resource",
                    },
                },
                "too-many-requests": {
                    "summary": "Too Many Requests Example",
                    "value": {
                        "type": "https://example.com/probs/too-many-requests",
                        "title": "Too Many Requests",
                        "status": 429,
                        "detail": "Rate limit exceeded. Please try again in 60 seconds.",
                        "instance": "/api/v1/resource",
                        "retry_after": 60,
                    },
                },
                "internal-server-error": {
                    "summary": "Internal Server Error Example",
                    "value": {
                        "type": "https://example.com/probs/internal-server-error",
                        "title": "Internal Server Error",
                        "status": 500,
                        "detail": "An unexpected error occurred. Please try again later.",
                        "instance": "/api/v1/resource/123",
                        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                    },
                },
            },
        )

        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = security_schemes
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # Add middleware - order is important here!

    # 1. First add correlation ID middleware to ensure all requests have a correlation ID
    app.add_middleware(CorrelationIdMiddleware)

    # 2. Add rate limiting middleware early in the chain
    # app.add_middleware(RateLimitMiddleware)  # TODO: Fix middleware implementation

    # Parse CORS origins from comma-separated string
    if settings.CORS_ORIGINS == "*":
        cors_origins = ["*"]
    else:
        cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Add idempotency middleware
    app.add_middleware(IdempotencyMiddleware, ttl_hours=24)

    # 4. Add logging middleware (will have access to correlation ID)
    app = setup_logging_middleware(app)

    # 5. Add compression middleware (should be early in the chain)
    app.add_middleware(CompressionMiddleware, minimum_size=1024)
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Add components for error responses
    # openapi_schema.setdefault("components", {}).setdefault("schemas", {}).update(
    #     {
    #         "Problem": Problem.schema(ref_template="#/components/schemas/{model}"),
    #         "ValidationProblem": ValidationProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #         "UnauthorizedProblem": UnauthorizedProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #         "ForbiddenProblem": ForbiddenProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #         "NotFoundProblem": NotFoundProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #         "ConflictProblem": ConflictProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #         "TooManyRequestsProblem": TooManyRequestsProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #         "InternalServerErrorProblem": InternalServerErrorProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #         "ServiceUnavailableProblem": ServiceUnavailableProblem.schema(
    #             ref_template="#/components/schemas/{model}"
    #         ),
    #     }
    # )

    # Add error response examples
    openapi_schema.setdefault("components", {}).setdefault("examples", {}).update(
        {
            "validation-error": {
                "summary": "Validation Error Example",
                "value": {
                    "type": "https://example.com/probs/validation-error",
                    "title": "Validation Error",
                    "status": 422,
                    "detail": "Your request contains invalid parameters",
                    "instance": "/api/v1/resource/123",
                    "errors": [
                        {
                            "field": "email",
                            "message": "Not a valid email address",
                            "error_code": "invalid_email",
                        },
                    ],
                },
            },
        },
    )

    # Add metrics middleware
    # @app.middleware("http")
    # async def metrics_middleware_wrapper(request: Request, call_next):
    #     return await metrics_middleware(request, call_next)

    # Register global exception handlers
    try:
        register_exception_handlers(app)
    except Exception as e:
        logger.warning("Failed to register exception handlers: %s", e)

    # Include the well-known router (for JWKS, OpenID configuration, etc.)
    app.include_router(well_known_router)

    # Include the v1 API router
    app.include_router(v1_router, prefix=settings.API_V1_STR)

    app.include_router(admin_router, prefix="/api/v1")
    # Include basic health router
    app.include_router(health_router)

    # Add user context to Sentry
    @app.middleware("http")
    async def sentry_user_middleware(request: Request, call_next) -> Response:
        # Set user context if authenticated
        if (
            hasattr(request.state, "user")
            and request.state.user
            and hasattr(request.state.user, "id")
        ):
            # set_user(user_id=str(request.state.user.id))
            pass
        response = await call_next(request)
        return response

    return app


app = create_app()

# Log application startup with structured extras
logger.info(
    "Application started",
    extra={
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    },
)
