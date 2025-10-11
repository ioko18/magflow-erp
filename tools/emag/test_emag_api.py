import os
import aiohttp
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_emag_api():
    # Get credentials from environment
    username = os.getenv("EMAG_API_USERNAME")
    password = os.getenv("EMAG_API_PASSWORD")
    api_url = os.getenv("EMAG_API_URL", "https://marketplace-api.emag.ro/api-3")

    if not username or not password:
        print(
            "❌ Error: Please set EMAG_API_USERNAME and EMAG_API_PASSWORD in .env file"
        )
        return

    print(f"🔍 Testing connection to: {api_url}")
    print(f"👤 Using username: {username}")

    # Test authentication with a simple API call
    test_endpoint = f"{api_url.rstrip('/')}/product_offer/read"

    try:
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(username, password)
        ) as session:
            print(f"\n🔧 Making test request to: {test_endpoint}")
            async with session.get(test_endpoint) as response:
                print(f"\n📡 Response Status: {response.status}")

                # Try to get response text
                try:
                    response_text = await response.text()
                    print("📄 Response Body:")
                    print(json.dumps(json.loads(response_text), indent=2))
                except json.JSONDecodeError:
                    print("⚠️ Could not parse response as JSON")
                    print(f"Raw response: {response_text}")

                # Print headers for debugging
                print("\n📋 Response Headers:")
                for header, value in response.headers.items():
                    print(f"  {header}: {value}")

    except Exception as e:
        print(f"\n❌ Error making request: {str(e)}")
        if hasattr(e, "headers"):
            print("\n📋 Error Headers:")
            for header, value in e.headers.items():
                print(f"  {header}: {value}")


if __name__ == "__main__":
    print("🔌 eMAG API Connection Tester\n" + "=" * 40)
    asyncio.run(test_emag_api())
