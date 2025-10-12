import asyncio
import os

from app.services.emag_integration_service import (
    EmagApiClient,
    EmagApiConfig,
    EmagApiEnvironment,
    EmagApiError,
)
from dotenv import load_dotenv


async def test_emag_client():
    # Load environment variables
    load_dotenv()

    # Create eMAG API config
    config = EmagApiConfig(
        environment=EmagApiEnvironment.SANDBOX,  # or PRODUCTION for production
        api_username=os.getenv("EMAG_API_USERNAME", ""),
        api_password=os.getenv("EMAG_API_PASSWORD", ""),
        api_timeout=30,
        max_retries=3,
        retry_delay=1.0,
    )

    # Initialize the eMAG API client
    async with EmagApiClient(config) as client:
        try:
            print("Testing eMAG API connection...")

            # Test getting categories
            print("\nFetching categories...")
            categories = await client.get_categories()
            print(f"Found {len(categories)} categories")

            # If we have categories, try getting products from the first one
            if categories and len(categories) > 0:
                first_category = categories[0]
                print(
                    f"\nFetching products for category: {first_category.get('name', 'Unknown')}"
                )
                products = await client.get_products(
                    category_id=first_category.get("id")
                )
                print(f"Found {len(products)} products")

            print("\nTest completed successfully!")

        except EmagApiError as e:
            details = getattr(e, "details", {}) or {}
            if (
                details.get("captcha_required")
                or getattr(e, "status_code", None) == 511
            ):
                print(
                    "The eMAG sandbox responded with a CAPTCHA challenge (HTTP 511). "
                    "Please complete the CAPTCHA by visiting the sandbox portal and retry."
                )
                if details.get("response_headers"):
                    print("Response headers:")
                    for header, value in details["response_headers"].items():
                        print(f"  {header}: {value}")
                return

            print(f"Error during eMAG API test: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error during eMAG API test: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(test_emag_client())
