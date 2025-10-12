"""Simple verification script for the eMAG API client."""

import asyncio
import sys
from enum import Enum

from pydantic import BaseModel


# Define minimal test doubles
class EmagAccountType(str, Enum):
    MAIN = "main"
    FBE = "fbe"


class EmagAccountConfig(BaseModel):
    username: str
    password: str
    warehouse_id: int
    ip_whitelist_name: str
    callback_base: str


class EmagSettings:
    def __init__(self):
        self.api_base_url = "https://marketplace-api.emag.pl/api-3"
        self.api_timeout = 30
        self.rate_limit_orders = 12
        self.rate_limit_other = 3

    def get_account_config(self, account_type: EmagAccountType) -> EmagAccountConfig:
        return EmagAccountConfig(
            username="test_user",
            password="test_pass",
            warehouse_id=1,
            ip_whitelist_name="test_whitelist",
            callback_base="https://test.com/emag",
        )


# Import the client
sys.path.insert(0, "/Users/macos/anaconda3/envs/MagFlow/app/integrations/emag")
from client import EmagAPIClient


async def test_client():
    print("Testing eMAG API client...")

    # Create a client instance
    client = EmagAPIClient(account_type=EmagAccountType.MAIN, settings=EmagSettings())

    # Test authentication token generation
    print("\n1. Testing authentication token generation...")
    token = await client._get_auth_token()
    print(f"Generated auth token: {token[:10]}...")

    # Test making a request (mocked)
    print("\n2. Testing request with mocked response...")

    # Mock response
    class MockResponse:
        def __init__(self):
            self.status = 200
            self.headers = {}

        async def json(self):
            return {"isError": False, "results": "success"}

        async def text(self):
            return '{"isError": false, "results": "success"}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    # Patch the session
    class MockSession:
        def __init__(self):
            self.closed = False

        async def request(self, *args, **kwargs):
            print(f"\nMock request made to: {args[1]}")
            print(f"Headers: {kwargs.get('headers', {}).keys()}")
            return MockResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    # Replace the client's session with our mock
    client._session = MockSession()

    # Make a test request
    try:
        result = await client._make_request(
            "GET", "/test", response_model=dict, is_order_endpoint=False
        )
        print(f"Request successful! Response: {result}")
    except Exception as e:
        print(f"Request failed: {e}")

    # Close the client
    await client.close()
    print("\nTest completed!")


if __name__ == "__main__":
    asyncio.run(test_client())
