"""Minimal test for eMAG API client core functionality."""


class EmagAccountType:
    """eMAG account types."""

    MAIN = "main"
    FBE = "fbe"


class EmagAccountConfig:
    """Configuration for a single eMAG account."""

    def __init__(
        self, username, password, warehouse_id, ip_whitelist_name, callback_base
    ):
        self.username = username
        self.password = password
        self.warehouse_id = warehouse_id
        self.ip_whitelist_name = ip_whitelist_name
        self.callback_base = callback_base


class EmagSettings:
    """eMAG API settings with rate limiting configuration."""

    def __init__(self):
        self.api_base_url = "https://marketplace-api.emag.pl/api-3"
        self.api_timeout = 30
        self.rate_limit_orders = 12  # requests per second for order endpoints
        self.rate_limit_other = 3  # requests per second for other endpoints
        self.retry_attempts = 3  # number of retry attempts for failed requests
        self.retry_delay = 1.0  # initial delay between retries in seconds
        self.jitter = 0.1  # jitter factor for retry delay

    def get_account_config(self, account_type):
        """Get configuration for the specified account type."""
        if account_type == EmagAccountType.MAIN:
            return EmagAccountConfig(
                username="test_main_user",
                password="test_main_pass",
                warehouse_id=1,
                ip_whitelist_name="test_whitelist",
                callback_base="https://test.com/emag",
            )
        else:  # FBE
            return EmagAccountConfig(
                username="test_fbe_user",
                password="test_fbe_pass",
                warehouse_id=2,
                ip_whitelist_name="test_fbe_whitelist",
                callback_base="https://test.com/emag/fbe",
            )


class RateLimiter:
    """Rate limiter for eMAG API requests with separate limits for order and other endpoints."""

    def __init__(self, orders_per_second, other_per_second):
        self.orders_per_second = orders_per_second
        self.other_per_second = other_per_second
        self.order_requests = []
        self.other_requests = []

    async def wait_if_needed(self, is_order_endpoint=False):
        """Wait if rate limit would be exceeded for the given endpoint type."""
        import time

        now = time.time()

        # Clean up old requests (older than 1 second)
        cutoff = now - 1.0

        if is_order_endpoint:
            self.order_requests = [t for t in self.order_requests if t > cutoff]

            # If we've hit the rate limit, wait until the oldest request is older than 1 second
            if len(self.order_requests) >= self.orders_per_second:
                sleep_time = 1.0 - (now - self.order_requests[0])
                if sleep_time > 0:
                    import asyncio

                    await asyncio.sleep(sleep_time)

            self.order_requests.append(time.time())
        else:
            self.other_requests = [t for t in self.other_requests if t > cutoff]

            if len(self.other_requests) >= self.other_per_second:
                sleep_time = 1.0 - (now - self.other_requests[0])
                if sleep_time > 0:
                    import asyncio

                    await asyncio.sleep(sleep_time)

            self.other_requests.append(time.time())


class EmagAPIError(Exception):
    """Base exception for eMAG API errors."""

    def __init__(self, message, status_code=None):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)


async def test_rate_limiter():
    """Test the rate limiter functionality."""
    print("=== Testing Rate Limiter ===")

    # Create a rate limiter with low limits for testing
    rate_limiter = RateLimiter(orders_per_second=2, other_per_second=1)

    # Test order endpoint rate limiting
    print("\nTesting order endpoint rate limiting (2 requests per second):")
    start_time = time.time()
    for i in range(5):
        await rate_limiter.wait_if_needed(is_order_endpoint=True)
        print(f"  Order request {i + 1} at {time.time() - start_time:.2f}s")

    # Test other endpoint rate limiting
    print("\nTesting other endpoint rate limiting (1 request per second):")
    start_time = time.time()
    for i in range(3):
        await rate_limiter.wait_if_needed(is_order_endpoint=False)
        print(f"  Other request {i + 1} at {time.time() - start_time:.2f}s")

    print("\n✅ Rate limiter test completed successfully!")


if __name__ == "__main__":
    import asyncio
    import time

    # Run the rate limiter test
    asyncio.run(test_rate_limiter())

    # Test account configuration
    print("\n=== Testing Account Configuration ===")
    settings = EmagSettings()

    # Test MAIN account config
    main_config = settings.get_account_config(EmagAccountType.MAIN)
    print("MAIN Account Config:")
    print(f"  Username: {main_config.username}")
    print(f"  Warehouse ID: {main_config.warehouse_id}")
    print(f"  IP Whitelist: {main_config.ip_whitelist_name}")

    # Test FBE account config
    fbe_config = settings.get_account_config(EmagAccountType.FBE)
    print("\nFBE Account Config:")
    print(f"  Username: {fbe_config.username}")
    print(f"  Warehouse ID: {fbe_config.warehouse_id}")
    print(f"  IP Whitelist: {fbe_config.ip_whitelist_name}")

    print("\n✅ Account configuration test completed successfully!")
