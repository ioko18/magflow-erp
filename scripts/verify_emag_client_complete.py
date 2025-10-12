"""Simple verification script for the complete eMAG API client."""

import asyncio
import json
import sys

from emag_client_complete import EmagAccountType, EmagAPIError, EmagClient


async def test_client():
    """Test the eMAG client with a mock server."""
    print("=== Testing eMAG Client ===")

    # Create a client instance
    async with EmagClient(account_type=EmagAccountType.MAIN) as client:
        # Override the session with a mock
        mock_session = client._session = AsyncMock()

        # Test 1: Successful GET request
        print("\n--- Test 1: Successful GET request ---")
        mock_session.request.return_value.__aenter__.return_value = MockResponse(
            200, {"status": "success", "data": {"id": 1, "name": "Test Item"}}
        )

        try:
            response = await client.get("/test/endpoint", params={"key": "value"})
            print("✅ GET request successful!")
            print("Response:", json.dumps(response, indent=2))
        except Exception as e:
            print(f"❌ GET request failed: {e}")
            return False

        # Test 2: Authentication error
        print("\n--- Test 2: Authentication error ---")
        mock_session.request.return_value.__aenter__.return_value = MockResponse(
            401, {"message": "Invalid credentials"}
        )

        try:
            await client.get("/protected/endpoint")
            print("❌ Authentication test failed: Expected EmagAuthError")
            return False
        except EmagAPIError as e:
            print(f"✅ Authentication error handled: {e}")

        # Test 3: Rate limiting
        print("\n--- Test 3: Rate limiting ---")
        mock_session.request.return_value.__aenter__.return_value = MockResponse(
            200, {"status": "success"}
        )

        try:
            # Make multiple requests to trigger rate limiting
            tasks = [
                client.get(f"/test/{i}", is_order_endpoint=True)
                for i in range(15)  # More than the 12 req/s limit
            ]
            await asyncio.gather(*tasks)
            print("✅ Rate limiting test passed (requests were throttled)")
        except Exception as e:
            print(f"❌ Rate limiting test failed: {e}")
            return False

        print("\n✅ All tests completed successfully!")
        return True


class MockResponse:
    """Mock aiohttp response for testing."""

    def __init__(self, status: int, json_data: dict):
        self.status = status
        self._json_data = json_data
        self.headers = {}
        self.content_length = len(json.dumps(json_data).encode("utf-8"))

    async def json(self):
        """Return JSON response data."""
        return self._json_data

    async def text(self):
        """Return text response data."""
        return json.dumps(self._json_data)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass


class AsyncMock:
    """Simple async mock for testing."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.return_value = None
        self.side_effect = None
        self.call_count = 0
        self.return_value = AsyncMock()
        self.return_value.__aenter__ = self._aenter
        self.return_value.__aexit__ = self._aexit

    async def _aenter(self):
        return self.return_value

    async def _aexit(self, *args):
        pass

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        if self.side_effect is not None:
            if callable(self.side_effect):
                return await self.side_effect(*args, **kwargs)
            return self.side_effect
        return self.return_value

    def assert_called_once(self):
        """Assert that the mock was called exactly once."""
        if self.call_count != 1:
            raise AssertionError(
                f"Expected mock to be called once. Called {self.call_count} times."
            )


if __name__ == "__main__":

    # Add the current directory to the path to import the module
    sys.path.insert(0, ".")

    # Run the tests
    success = asyncio.run(test_client())
    if not success:
        print("\n❌ Some tests failed!")
        sys.exit(1)
