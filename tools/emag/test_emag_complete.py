#!/usr/bin/env python3
"""
Comprehensive eMAG Integration Test Script
Tests all endpoints and functionality of the MagFlow ERP eMAG integration.
"""

import asyncio
import json
import sys
from datetime import datetime

import httpx


class EmagIntegrationTester:
    """Comprehensive tester for eMAG integration."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "tests": []
        }

    def log_test(self, name: str, passed: bool, details: str = ""):
        """Log test result."""
        self.results["total_tests"] += 1
        if passed:
            self.results["passed"] += 1
            print(f"✅ PASS: {name}")
        else:
            self.results["failed"] += 1
            print(f"❌ FAIL: {name}")

        if details:
            print(f"   {details}")

        self.results["tests"].append({
            "name": name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def authenticate(self) -> bool:
        """Authenticate and get JWT token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={"username": "admin@example.com", "password": "secret"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    self.log_test("Authentication", True, "Token obtained")
                    return True
                else:
                    self.log_test("Authentication", False, f"Status: {response.status_code}")
                    return False
            except Exception as e:
                self.log_test("Authentication", False, f"Error: {str(e)}")
                return False

    async def test_health_endpoint(self):
        """Test basic health endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)
                passed = response.status_code == 200
                self.log_test(
                    "Health Endpoint",
                    passed,
                    f"Status: {response.status_code}"
                )
            except Exception as e:
                self.log_test("Health Endpoint", False, f"Error: {str(e)}")

    async def test_emag_products_endpoint(self):
        """Test eMAG products listing."""
        if not self.token:
            self.log_test("eMAG Products Endpoint", False, "No auth token")
            return

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/enhanced/products/all?limit=10",
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    products = data.get("products", [])
                    self.log_test(
                        "eMAG Products Endpoint",
                        True,
                        f"Retrieved {len(products)} products"
                    )
                else:
                    self.log_test(
                        "eMAG Products Endpoint",
                        False,
                        f"Status: {response.status_code}"
                    )
            except Exception as e:
                self.log_test("eMAG Products Endpoint", False, f"Error: {str(e)}")

    async def test_emag_status_endpoint(self):
        """Test eMAG status endpoint."""
        if not self.token:
            self.log_test("eMAG Status Endpoint", False, "No auth token")
            return

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/enhanced/status",
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    stats = data.get("sync_statistics", {})
                    total_syncs = stats.get("total_syncs", 0)
                    success_rate = stats.get("success_rate", 0)
                    self.log_test(
                        "eMAG Status Endpoint",
                        True,
                        (
                            f"Total syncs: {total_syncs}, "
                            f"Success rate: {success_rate}%"
                        ),
                    )
                else:
                    self.log_test(
                        "eMAG Status Endpoint",
                        False,
                        f"Status: {response.status_code}"
                    )
            except Exception as e:
                self.log_test("eMAG Status Endpoint", False, f"Error: {str(e)}")

    async def test_emag_management_health(self):
        """Test eMAG management health endpoint."""
        if not self.token:
            self.log_test("eMAG Management Health", False, "No auth token")
            return

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/management/health",
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "unknown")
                    score = data.get("health_score", 0)
                    self.log_test(
                        "eMAG Management Health",
                        True,
                        f"Status: {status}, Score: {score}"
                    )
                else:
                    self.log_test(
                        "eMAG Management Health",
                        False,
                        f"Status: {response.status_code}"
                    )
            except Exception as e:
                self.log_test("eMAG Management Health", False, f"Error: {str(e)}")

    async def test_emag_monitoring_metrics(self):
        """Test eMAG monitoring metrics endpoint."""
        if not self.token:
            self.log_test("eMAG Monitoring Metrics", False, "No auth token")
            return

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/management/monitoring/metrics",
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    metrics = data.get("metrics", {})
                    self.log_test(
                        "eMAG Monitoring Metrics",
                        True,
                        f"Metrics retrieved: {len(metrics)} fields"
                    )
                else:
                    self.log_test(
                        "eMAG Monitoring Metrics",
                        False,
                        f"Status: {response.status_code}"
                    )
            except Exception as e:
                self.log_test("eMAG Monitoring Metrics", False, f"Error: {str(e)}")

    async def test_database_products_count(self):
        """Test database has products."""
        if not self.token:
            self.log_test("Database Products Count", False, "No auth token")
            return

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/enhanced/products/all?limit=1000",
                    headers=headers,
                    timeout=15.0
                )

                if response.status_code == 200:
                    data = response.json()
                    products = data.get("products", [])
                    total = len(products)

                    # Count by account type
                    main_count = len([p for p in products if p.get("account_type") == "main"])
                    fbe_count = len([p for p in products if p.get("account_type") == "fbe"])

                    passed = total >= 100  # Should have at least 100 products
                    self.log_test(
                        "Database Products Count",
                        passed,
                        f"Total: {total}, MAIN: {main_count}, FBE: {fbe_count}"
                    )
                else:
                    self.log_test(
                        "Database Products Count",
                        False,
                        f"Status: {response.status_code}"
                    )
            except Exception as e:
                self.log_test("Database Products Count", False, f"Error: {str(e)}")

    async def run_all_tests(self):
        """Run all tests."""
        print("\n" + "="*60)
        print("🧪 MagFlow ERP - eMAG Integration Test Suite")
        print("="*60 + "\n")

        # Authenticate first
        if not await self.authenticate():
            print("\n❌ Authentication failed. Cannot proceed with tests.")
            return

        print()

        # Run all tests
        await self.test_health_endpoint()
        await self.test_emag_products_endpoint()
        await self.test_emag_status_endpoint()
        await self.test_emag_management_health()
        await self.test_emag_monitoring_metrics()
        await self.test_database_products_count()

        # Print summary
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"Success Rate: {(self.results['passed'] / self.results['total_tests'] * 100):.1f}%")
        print("="*60 + "\n")

        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("📝 Detailed results saved to: test_results.json\n")

        return self.results['failed'] == 0


async def main():
    """Main test runner."""
    tester = EmagIntegrationTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
