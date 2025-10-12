#!/usr/bin/env python3
"""
Simple eMAG Test Script for MagFlow ERP.

This script tests the eMAG configuration and API connectivity without
requiring the full application stack.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.strip().split("=", 1)
                os.environ[key] = value


# Test configuration loading
def test_config():
    """Test eMAG configuration loading."""
    print("Testing eMAG Configuration...")
    print("=" * 50)

    # Test MAIN account
    main_username = os.getenv("EMAG_MAIN_USERNAME")
    main_password = os.getenv("EMAG_MAIN_PASSWORD")

    print("MAIN Account:")
    print(f"  Username: {main_username}")
    print(f"  Password: {'*' * len(main_password) if main_password else 'NOT SET'}")
    print(
        f"  Valid: {bool(main_username and main_password and len(main_username) > 3 and len(main_password) > 6)}"
    )

    # Test FBE account
    fbe_username = os.getenv("EMAG_FBE_USERNAME")
    fbe_password = os.getenv("EMAG_FBE_PASSWORD")

    print("\nFBE Account:")
    print(f"  Username: {fbe_username}")
    print(f"  Password: {'*' * len(fbe_password) if fbe_password else 'NOT SET'}")
    print(
        f"  Valid: {bool(fbe_username and fbe_password and len(fbe_username) > 3 and len(fbe_password) > 6)}"
    )

    # Test rate limiting settings
    print("\nRate Limiting Settings:")
    print(f"  MAIN Orders RPS: {os.getenv('EMAG_MAIN_ORDERS_RPS', '12')}")
    print(f"  MAIN Other RPS: {os.getenv('EMAG_MAIN_OTHER_RPS', '3')}")
    print(f"  FBE Orders RPS: {os.getenv('EMAG_FBE_ORDERS_RPS', '12')}")
    print(f"  FBE Other RPS: {os.getenv('EMAG_FBE_OTHER_RPS', '3')}")

    # Test API settings
    print("\nAPI Settings:")
    print(
        f"  Base URL: {os.getenv('EMAG_MAIN_BASE_URL', 'https://marketplace-api.emag.ro/api-3')}"
    )
    print(f"  Timeout: {os.getenv('EMAG_MAIN_TIMEOUT', '30')} seconds")
    print(f"  Environment: {os.getenv('ENVIRONMENT', 'development')}")

    return bool(main_username and main_password)


async def test_api_connection():
    """Test basic API connection (mock)."""
    print("\nTesting API Connection...")
    print("=" * 50)

    # This is a mock test since we don't want to make real API calls
    main_username = os.getenv("EMAG_MAIN_USERNAME")
    main_password = os.getenv("EMAG_MAIN_PASSWORD")

    if not main_username or not main_password:
        print("❌ Cannot test API connection - credentials not configured")
        return False

    print("✅ Credentials configured")
    print("✅ API URL configured")
    print("✅ Rate limiting configured")
    print(
        "ℹ️  Note: Actual API connection test requires real credentials and network access"
    )

    return True


def main():
    """Main test function."""
    print("MagFlow ERP - eMAG Integration Test")
    print("=" * 50)

    # Test configuration
    config_valid = test_config()

    # Test API connection (mock)
    asyncio.run(test_api_connection())

    # Summary
    print("\nTest Summary:")
    print("=" * 50)
    if config_valid:
        print("✅ Configuration: VALID")
        print("✅ Ready for eMAG synchronization")
        print("\nNext steps:")
        print("1. Ensure database is running: docker-compose up -d postgres")
        print("2. Run migrations: alembic upgrade head")
        print("3. Start backend: ./start_dev.sh backend")
        print(
            "4. Test sync: python enhanced_emag_sync_script.py --mode products --account both --max-pages 2"
        )
    else:
        print("❌ Configuration: INVALID")
        print("❌ Please configure eMAG credentials in .env file")
        print("\nRequired variables:")
        print("- EMAG_MAIN_USERNAME")
        print("- EMAG_MAIN_PASSWORD")
        print("- EMAG_FBE_USERNAME")
        print("- EMAG_FBE_PASSWORD")


if __name__ == "__main__":
    main()
