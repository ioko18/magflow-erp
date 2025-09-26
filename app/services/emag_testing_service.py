"""eMAG Credentials Testing Service for MagFlow ERP.

This module provides safe testing capabilities with real eMAG credentials,
including connection testing, API validation, and production-ready testing workflows.
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.dependency_injection import ServiceBase, ServiceContext
from app.services.emag_integration_service import EmagIntegrationService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Timezone-aware current UTC timestamp."""
    return datetime.now(timezone.utc)


class TestEnvironment(str, Enum):
    """Testing environments for eMAG API."""

    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"


class TestType(str, Enum):
    """Types of tests that can be performed."""

    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    RATE_LIMITS = "rate_limits"
    PAGINATION = "pagination"
    DATA_RETRIEVAL = "data_retrieval"
    SYNC_OPERATION = "sync_operation"
    ERROR_HANDLING = "error_handling"


@dataclass
class EmagCredentials:
    """eMAG API credentials configuration."""

    username: str
    password: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    environment: TestEnvironment = TestEnvironment.PRODUCTION
    whitelisted_ips: List[str] = field(default_factory=list)
    test_mode: bool = False
    rate_limits: Dict[str, int] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of a test operation."""

    test_id: str
    test_type: TestType
    environment: TestEnvironment
    success: bool
    duration_ms: int
    timestamp: datetime
    request_count: int
    response_time_avg_ms: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    """Complete test suite for eMAG integration."""

    suite_id: str
    credentials: EmagCredentials
    tests: List[TestType]
    results: List[TestResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    overall_success: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)


class EmagTestingService(ServiceBase):
    """Service for testing eMAG integration with real credentials."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self.test_suites: Dict[str, TestSuite] = {}
        self.active_tests: Dict[str, asyncio.Task] = {}
        self.emag_service: Optional[EmagIntegrationService] = None

        # Load test configuration
        self._load_test_config()

    def _load_test_config(self):
        """Load testing configuration from settings."""
        # Test configuration could be loaded from settings
        # For now, we'll use environment variables or config files

        logger.info("eMAG Testing Service initialized")

    async def initialize(self):
        """Initialize testing service."""
        await super().initialize()

        # Initialize eMAG service for testing
        self.emag_service = EmagIntegrationService(self.context)
        await self.emag_service.initialize()

        logger.info("eMAG Testing Service initialized")

    async def test_credentials_connection(
        self,
        credentials: EmagCredentials,
    ) -> TestResult:
        """Test basic connection with eMAG credentials."""
        test_id = secrets.token_hex(16)
        start_time = _utcnow()

        try:
            logger.info(f"Testing eMAG connection for {credentials.environment.value}")

            # Test basic authentication and connection
            test_result = await self.emag_service.test_emag_connection(
                (
                    "main"
                    if credentials.environment == TestEnvironment.PRODUCTION
                    else "sandbox"
                ),
            )

            duration = int((_utcnow() - start_time).total_seconds() * 1000)

            success = test_result.get("status") == "success"

            metadata = {
                "account_type": "main",
                "connection_status": test_result.get("status"),
                "response_data": test_result,
            }

            return TestResult(
                test_id=test_id,
                test_type=TestType.CONNECTION,
                environment=credentials.environment,
                success=success,
                duration_ms=duration,
                timestamp=start_time,
                request_count=1,
                response_time_avg_ms=duration,
                metadata=metadata,
            )

        except Exception as e:
            duration = int((_utcnow() - start_time).total_seconds() * 1000)

            logger.error(f"Connection test failed: {e}")

            return TestResult(
                test_id=test_id,
                test_type=TestType.CONNECTION,
                environment=credentials.environment,
                success=False,
                duration_ms=duration,
                timestamp=start_time,
                request_count=1,
                response_time_avg_ms=duration,
                error_message=str(e),
            )

    async def test_authentication(self, credentials: EmagCredentials) -> TestResult:
        """Test eMAG authentication."""
        test_id = secrets.token_hex(16)
        start_time = _utcnow()

        try:
            logger.info(
                f"Testing eMAG authentication for {credentials.environment.value}",
            )

            # Test authentication by trying to access protected resources
            try:
                # Attempt to get products (requires authentication)
                products = await self.emag_service.get_all_products(
                    (
                        "main"
                        if credentials.environment == TestEnvironment.PRODUCTION
                        else "sandbox"
                    ),
                    max_pages=1,
                    delay_between_requests=0,
                )

                duration = int((_utcnow() - start_time).total_seconds() * 1000)

                success = len(products) >= 0  # Even empty result means auth worked

                metadata = {
                    "products_retrieved": len(products),
                    "authentication_status": "success",
                }

                return TestResult(
                    test_id=test_id,
                    test_type=TestType.AUTHENTICATION,
                    environment=credentials.environment,
                    success=success,
                    duration_ms=duration,
                    timestamp=start_time,
                    request_count=1,
                    response_time_avg_ms=duration,
                    metadata=metadata,
                )

            except Exception as auth_error:
                # Check if it's an authentication error
                if (
                    "auth" in str(auth_error).lower()
                    or "credential" in str(auth_error).lower()
                ):
                    duration = int((_utcnow() - start_time).total_seconds() * 1000)

                    return TestResult(
                        test_id=test_id,
                        test_type=TestType.AUTHENTICATION,
                        environment=credentials.environment,
                        success=False,
                        duration_ms=duration,
                        timestamp=start_time,
                        request_count=1,
                        response_time_avg_ms=duration,
                        error_message="Authentication failed",
                        metadata={"auth_error": str(auth_error)},
                    )
                raise auth_error

        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.error(f"Authentication test failed: {e}")

            return TestResult(
                test_id=test_id,
                test_type=TestType.AUTHENTICATION,
                environment=credentials.environment,
                success=False,
                duration_ms=duration,
                timestamp=start_time,
                request_count=1,
                response_time_avg_ms=duration,
                error_message=str(e),
            )

    async def test_rate_limits(
        self,
        credentials: EmagCredentials,
        test_duration_seconds: int = 60,
    ) -> TestResult:
        """Test eMAG API rate limits."""
        test_id = secrets.token_hex(16)
        start_time = datetime.utcnow()

        try:
            logger.info(f"Testing eMAG rate limits for {credentials.environment.value}")

            request_times = []
            success_count = 0
            error_count = 0
            rate_limited_count = 0

            end_time = _utcnow() + timedelta(seconds=test_duration_seconds)

            while _utcnow() < end_time:
                try:
                    request_start = _utcnow()

                    # Make a test request
                    await self.emag_service.get_all_products(
                        (
                            "main"
                            if credentials.environment == TestEnvironment.PRODUCTION
                            else "sandbox"
                        ),
                        max_pages=1,
                        delay_between_requests=0,
                    )

                    request_duration = (
                        _utcnow() - request_start
                    ).total_seconds() * 1000
                    request_times.append(request_duration)
                    success_count += 1

                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.1)

                except Exception as e:
                    error_count += 1
                    if "rate limit" in str(e).lower():
                        rate_limited_count += 1

                    # Continue testing even on errors
                    await asyncio.sleep(1)

            total_duration = int((_utcnow() - start_time).total_seconds() * 1000)
            avg_response_time = (
                sum(request_times) / len(request_times) if request_times else 0
            )

            # Calculate requests per second
            requests_per_second = (
                success_count / test_duration_seconds
                if test_duration_seconds > 0
                else 0
            )

            success = success_count > 0 and rate_limited_count < success_count

            metadata = {
                "total_requests": success_count + error_count,
                "successful_requests": success_count,
                "failed_requests": error_count,
                "rate_limited_requests": rate_limited_count,
                "requests_per_second": requests_per_second,
                "rate_limit_hit": rate_limited_count > 0,
            }

            return TestResult(
                test_id=test_id,
                test_type=TestType.RATE_LIMITS,
                environment=credentials.environment,
                success=success,
                duration_ms=total_duration,
                timestamp=start_time,
                request_count=success_count + error_count,
                response_time_avg_ms=avg_response_time,
                metadata=metadata,
            )

        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.error(f"Rate limits test failed: {e}")

            return TestResult(
                test_id=test_id,
                test_type=TestType.RATE_LIMITS,
                environment=credentials.environment,
                success=False,
                duration_ms=duration,
                timestamp=start_time,
                request_count=0,
                response_time_avg_ms=0,
                error_message=str(e),
            )

    async def test_data_retrieval(
        self,
        credentials: EmagCredentials,
        max_pages: int = 5,
    ) -> TestResult:
        """Test data retrieval capabilities."""
        test_id = secrets.token_hex(16)
        start_time = datetime.utcnow()

        try:
            logger.info(f"Testing data retrieval for {credentials.environment.value}")

            request_times = []
            total_products = 0
            total_offers = 0
            request_count = 0

            # Test product retrieval
            try:
                request_start = datetime.utcnow()

                products = await self.emag_service.get_all_products(
                    (
                        "main"
                        if credentials.environment == TestEnvironment.PRODUCTION
                        else "sandbox"
                    ),
                    max_pages=max_pages,
                    delay_between_requests=0.2,
                )

                request_duration = (
                    _utcnow() - request_start
                ).total_seconds() * 1000
                request_times.append(request_duration)
                total_products = len(products)
                request_count += max_pages

            except Exception as e:
                logger.error(f"Product retrieval failed: {e}")

            # Test offer retrieval
            try:
                request_start = datetime.utcnow()

                offers = await self.emag_service.get_all_offers(
                    (
                        "main"
                        if credentials.environment == TestEnvironment.PRODUCTION
                        else "sandbox"
                    ),
                    max_pages=min(max_pages, 3),  # Fewer pages for offers
                    delay_between_requests=0.2,
                )

                request_duration = (
                    datetime.utcnow() - request_start
                ).total_seconds() * 1000
                request_times.append(request_duration)
                total_offers = len(offers)
                request_count += min(max_pages, 3)

            except Exception as e:
                logger.error(f"Offer retrieval failed: {e}")

            total_duration = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000,
            )
            avg_response_time = (
                sum(request_times) / len(request_times) if request_times else 0
            )

            success = total_products > 0 or total_offers > 0

            metadata = {
                "products_retrieved": total_products,
                "offers_retrieved": total_offers,
                "pages_processed": max_pages,
                "data_quality_score": self._calculate_data_quality_score(
                    products,
                    offers,
                ),
            }

            return TestResult(
                test_id=test_id,
                test_type=TestType.DATA_RETRIEVAL,
                environment=credentials.environment,
                success=success,
                duration_ms=total_duration,
                timestamp=start_time,
                request_count=request_count,
                response_time_avg_ms=avg_response_time,
                metadata=metadata,
            )

        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.error(f"Data retrieval test failed: {e}")

            return TestResult(
                test_id=test_id,
                test_type=TestType.DATA_RETRIEVAL,
                environment=credentials.environment,
                success=False,
                duration_ms=duration,
                timestamp=start_time,
                request_count=0,
                response_time_avg_ms=0,
                error_message=str(e),
            )

    async def test_sync_operation(
        self,
        credentials: EmagCredentials,
        max_pages: int = 3,
    ) -> TestResult:
        """Test complete sync operation."""
        test_id = secrets.token_hex(16)
        start_time = datetime.utcnow()

        try:
            logger.info(f"Testing sync operation for {credentials.environment.value}")

            # Test complete sync from both accounts
            sync_result = await self.emag_service.sync_all_products_from_both_accounts(
                max_pages_per_account=max_pages,
                delay_between_requests=0.3,
            )

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            success = (
                sync_result.get("main_account", {}).get("products_count", 0) >= 0
                and sync_result.get("fbe_account", {}).get("products_count", 0) >= 0
            )

            metadata = {
                "main_products": sync_result.get("main_account", {}).get(
                    "products_count",
                    0,
                ),
                "fbe_products": sync_result.get("fbe_account", {}).get(
                    "products_count",
                    0,
                ),
                "combined_products": sync_result.get("combined", {}).get(
                    "products_count",
                    0,
                ),
                "total_processed": sync_result.get("total_products_processed", 0),
                "sync_timestamp": sync_result.get("sync_timestamp"),
            }

            return TestResult(
                test_id=test_id,
                test_type=TestType.SYNC_OPERATION,
                environment=credentials.environment,
                success=success,
                duration_ms=duration,
                timestamp=start_time,
                request_count=max_pages * 2,  # Both accounts
                response_time_avg_ms=duration / max(max_pages * 2, 1),
                metadata=metadata,
            )

        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.error(f"Sync operation test failed: {e}")

            return TestResult(
                test_id=test_id,
                test_type=TestType.SYNC_OPERATION,
                environment=credentials.environment,
                success=False,
                duration_ms=duration,
                timestamp=start_time,
                request_count=0,
                response_time_avg_ms=0,
                error_message=str(e),
            )

    async def run_complete_test_suite(
        self,
        credentials: EmagCredentials,
        test_types: Optional[List[TestType]] = None,
    ) -> TestSuite:
        """Run complete test suite with all tests."""
        suite_id = secrets.token_hex(16)

        if test_types is None:
            test_types = [
                TestType.CONNECTION,
                TestType.AUTHENTICATION,
                TestType.RATE_LIMITS,
                TestType.DATA_RETRIEVAL,
                TestType.SYNC_OPERATION,
            ]

        test_suite = TestSuite(
            suite_id=suite_id,
            credentials=credentials,
            tests=test_types,
        )

        logger.info(f"Starting test suite {suite_id} with {len(test_types)} tests")

        for test_type in test_types:
            try:
                logger.info(f"Running test: {test_type.value}")

                if test_type == TestType.CONNECTION:
                    result = await self.test_credentials_connection(credentials)
                elif test_type == TestType.AUTHENTICATION:
                    result = await self.test_authentication(credentials)
                elif test_type == TestType.RATE_LIMITS:
                    result = await self.test_rate_limits(credentials)
                elif test_type == TestType.DATA_RETRIEVAL:
                    result = await self.test_data_retrieval(credentials)
                elif test_type == TestType.SYNC_OPERATION:
                    result = await self.test_sync_operation(credentials)
                else:
                    result = TestResult(
                        test_id=secrets.token_hex(16),
                        test_type=test_type,
                        environment=credentials.environment,
                        success=False,
                        duration_ms=0,
                        timestamp=_utcnow(),
                        request_count=0,
                        response_time_avg_ms=0,
                        error_message=f"Unsupported test type: {test_type}",
                    )

                test_suite.results.append(result)

            except Exception as e:
                logger.error(f"Test {test_type.value} failed: {e}")

                result = TestResult(
                    test_id=secrets.token_hex(16),
                    test_type=test_type,
                    environment=credentials.environment,
                    success=False,
                    duration_ms=0,
                    timestamp=datetime.utcnow(),
                    request_count=0,
                    response_time_avg_ms=0,
                    error_message=str(e),
                )
                test_suite.results.append(result)

        # Calculate overall results
        test_suite.completed_at = _utcnow()
        test_suite.overall_success = all(
            result.success for result in test_suite.results
        )

        # Generate summary
        test_suite.summary = {
            "total_tests": len(test_suite.results),
            "successful_tests": len([r for r in test_suite.results if r.success]),
            "failed_tests": len([r for r in test_suite.results if not r.success]),
            "total_duration_ms": sum(r.duration_ms for r in test_suite.results),
            "average_response_time_ms": sum(
                r.response_time_avg_ms for r in test_suite.results
            )
            / len(test_suite.results),
            "total_requests": sum(r.request_count for r in test_suite.results),
        }

        # Store test suite
        self.test_suites[suite_id] = test_suite

        logger.info(
            f"Test suite {suite_id} completed. Success: {test_suite.overall_success}",
        )

        return test_suite

    def _calculate_data_quality_score(
        self,
        products: List[Dict[str, Any]],
        offers: List[Dict[str, Any]],
    ) -> float:
        """Calculate data quality score (0-1)."""
        try:
            if not products and not offers:
                return 0.0

            total_items = len(products) + len(offers)
            quality_score = 0

            # Check required fields in products
            if products:
                required_fields = ["id", "sku", "name", "price", "stock"]
                for product in products:
                    field_score = sum(
                        1 for field in required_fields if product.get(field)
                    ) / len(required_fields)
                    quality_score += field_score

            # Check required fields in offers
            if offers:
                required_fields = ["id", "sku", "name", "price", "stock"]
                for offer in offers:
                    field_score = sum(
                        1 for field in required_fields if offer.get(field)
                    ) / len(required_fields)
                    quality_score += field_score

            return min(quality_score / total_items, 1.0) if total_items > 0 else 0.0

        except Exception as e:
            logger.error(f"Failed to calculate data quality score: {e}")
            return 0.0
