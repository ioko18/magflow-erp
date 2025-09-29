import asyncio
import os
from dotenv import load_dotenv
from app.core.config import settings
from app.services.emag_integration_service import EmagIntegrationService
from app.core.dependency_injection import ServiceContext


async def test_emag_sync():
    # Load environment variables
    load_dotenv()

    # Create a service context with settings
    context = ServiceContext(settings=settings)

    # Initialize the eMAG integration service
    emag_service = EmagIntegrationService(context, account_type="main")

    try:
        print("Starting eMAG order sync...")
        await emag_service.sync_orders()
        print("eMAG order sync completed successfully!")
    except Exception as e:
        print(f"Error during eMAG sync: {str(e)}")
        raise
    finally:
        # Cleanup resources
        await emag_service.cleanup()


if __name__ == "__main__":
    asyncio.run(test_emag_sync())
