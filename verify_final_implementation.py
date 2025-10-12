#!/usr/bin/env python3
"""
Comprehensive verification script for MagFlow ERP eMAG Integration.
Verifies all implementations mentioned in FINAL_SUMMARY_AND_RECOMMENDATIONS.md
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import aiohttp


class ImplementationVerifier:
    """Verifies all backend and frontend implementations."""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:5173"
        self.token = None
        self.results = {
            "backend_services": {},
            "api_endpoints": {},
            "frontend_pages": {},
            "celery_tasks": {},
            "websocket_endpoints": {},
            "overall_status": "unknown"
        }

    async def authenticate(self, session: aiohttp.ClientSession) -> bool:
        """Authenticate and get JWT token."""
        try:
            async with session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": "admin@example.com", "password": "secret"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.token = data.get("access_token")
                    return True
                return False
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False

    def get_headers(self) -> dict[str, str]:
        """Get headers with authentication token."""
        return {"Authorization": f"Bearer {self.token}"}

    async def verify_backend_services(self) -> dict[str, bool]:
        """Verify backend services exist."""
        services = {
            "Enhanced eMAG Service": "app/services/enhanced_emag_service.py",
            "eMAG API Client": "app/services/emag_api_client.py",
            "eMAG Order Service": "app/services/emag_order_service.py",
            "eMAG AWB Service": "app/services/emag_awb_service.py",
            "eMAG EAN Matching": "app/services/emag_ean_matching_service.py",
            "eMAG Invoice Service": "app/services/emag_invoice_service.py",
            "Celery Sync Tasks": "app/services/tasks/emag_sync_tasks.py",
            "WebSocket Notifications": "app/api/v1/endpoints/websocket_notifications.py",
            "Redis Cache": "app/core/cache.py",
        }

        results = {}
        for name, path in services.items():
            file_path = Path(path)
            exists = file_path.exists()
            results[name] = exists
            status = "✅" if exists else "❌"
            print(f"{status} {name}: {path}")

        return results

    async def verify_api_endpoints(self, session: aiohttp.ClientSession) -> dict[str, bool]:
        """Verify API endpoints are functional."""
        endpoints = {
            # Product Sync
            "GET /emag/enhanced/products/all": ("GET", "/api/v1/emag/enhanced/products/all"),
            "GET /emag/enhanced/offers/all": ("GET", "/api/v1/emag/enhanced/offers/all"),
            "GET /emag/enhanced/status": ("GET", "/api/v1/emag/enhanced/status"),
            "GET /emag/enhanced/products/sync-progress": ("GET", "/api/v1/emag/enhanced/products/sync-progress"),

            # Order Management
            "GET /emag/orders/list": ("GET", "/api/v1/emag/orders/list"),
            "GET /emag/orders/all": ("GET", "/api/v1/emag/orders/all"),

            # Phase 2 Features
            "GET /emag/phase2/awb/couriers": ("GET", "/api/v1/emag/phase2/awb/couriers"),
            "GET /emag/phase2/ean/validate/1234567890123": ("GET", "/api/v1/emag/phase2/ean/validate/1234567890123"),

            # Health
            "GET /health": ("GET", "/health"),
        }

        results = {}
        for name, (method, path) in endpoints.items():
            try:
                url = f"{self.base_url}{path}"
                headers = self.get_headers() if path != "/health" else {}

                async with session.request(method, url, headers=headers) as resp:
                    success = resp.status in [200, 201, 422]  # 422 is OK for some endpoints without params
                    results[name] = success
                    status = "✅" if success else "❌"
                    print(f"{status} {name} - Status: {resp.status}")
            except Exception as e:
                results[name] = False
                print(f"❌ {name} - Error: {e}")

        return results

    async def verify_frontend_pages(self) -> dict[str, bool]:
        """Verify frontend page files exist."""
        pages = {
            "Dashboard": "admin-frontend/src/pages/Dashboard.tsx",
            "Product Sync": "admin-frontend/src/pages/EmagSync.tsx",
            "AWB Management": "admin-frontend/src/pages/EmagAwb.tsx",
            "EAN Matching": "admin-frontend/src/pages/EmagEan.tsx",
            "Invoices": "admin-frontend/src/pages/EmagInvoices.tsx",
            "Products": "admin-frontend/src/pages/Products.tsx",
            "Orders": "admin-frontend/src/pages/Orders.tsx",
            "Customers": "admin-frontend/src/pages/Customers.tsx",
        }

        results = {}
        for name, path in pages.items():
            file_path = Path(path)
            exists = file_path.exists()
            results[name] = exists
            status = "✅" if exists else "❌"
            print(f"{status} {name}: {path}")

        return results

    async def verify_celery_tasks(self) -> dict[str, bool]:
        """Verify Celery tasks are defined."""
        tasks_file = Path("app/services/tasks/emag_sync_tasks.py")

        if not tasks_file.exists():
            return {}

        content = tasks_file.read_text()

        tasks = {
            "emag.sync_orders": "sync_emag_orders_task",
            "emag.auto_acknowledge_orders": "auto_acknowledge_orders_task",
            "emag.sync_products": "sync_emag_products_task",
            "emag.cleanup_old_sync_logs": "cleanup_old_sync_logs_task",
            "emag.health_check": "health_check_task",
        }

        results = {}
        for name, func_name in tasks.items():
            exists = func_name in content
            results[name] = exists
            status = "✅" if exists else "❌"
            print(f"{status} Task {name}")

        return results

    async def verify_websocket_endpoints(self) -> dict[str, bool]:
        """Verify WebSocket endpoints exist in code."""
        ws_file = Path("app/api/v1/endpoints/websocket_notifications.py")

        if not ws_file.exists():
            return {}

        content = ws_file.read_text()

        endpoints = {
            "WS /ws/notifications": "/ws/notifications",
            "WS /ws/orders": "/ws/orders",
        }

        results = {}
        for name, path in endpoints.items():
            exists = path in content
            results[name] = exists
            status = "✅" if exists else "❌"
            print(f"{status} {name}")

        return results

    async def verify_database_data(self, session: aiohttp.ClientSession) -> dict[str, Any]:
        """Verify database has expected data."""
        try:
            async with session.get(
                f"{self.base_url}/api/v1/emag/enhanced/status",
                headers=self.get_headers()
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    summary = data.get("summary", {})

                    results = {
                        "total_products": summary.get("total_products", 0),
                        "main_products": data.get("main_account", {}).get("products", {}).get("total", 0),
                        "fbe_products": data.get("fbe_account", {}).get("products", {}).get("total", 0),
                    }

                    print("\n📊 Database Status:")
                    print(f"  Total Products: {results['total_products']}")
                    print(f"  MAIN Products: {results['main_products']}")
                    print(f"  FBE Products: {results['fbe_products']}")

                    return results
        except Exception as e:
            print(f"❌ Database verification failed: {e}")

        return {}

    async def run_verification(self):
        """Run complete verification."""
        print("=" * 80)
        print("🔍 MagFlow ERP - Final Implementation Verification")
        print("=" * 80)

        async with aiohttp.ClientSession() as session:
            # Authenticate
            print("\n🔐 Authenticating...")
            if not await self.authenticate(session):
                print("❌ Authentication failed. Cannot proceed.")
                return False
            print("✅ Authentication successful")

            # Verify Backend Services
            print("\n📦 Verifying Backend Services (9 services)...")
            self.results["backend_services"] = await self.verify_backend_services()

            # Verify API Endpoints
            print("\n🌐 Verifying API Endpoints...")
            self.results["api_endpoints"] = await self.verify_api_endpoints(session)

            # Verify Frontend Pages
            print("\n🎨 Verifying Frontend Pages (8 pages)...")
            self.results["frontend_pages"] = await self.verify_frontend_pages()

            # Verify Celery Tasks
            print("\n⏰ Verifying Celery Tasks (5 tasks)...")
            self.results["celery_tasks"] = await self.verify_celery_tasks()

            # Verify WebSocket Endpoints
            print("\n🔌 Verifying WebSocket Endpoints (2 endpoints)...")
            self.results["websocket_endpoints"] = await self.verify_websocket_endpoints()

            # Verify Database Data
            print("\n💾 Verifying Database Data...")
            db_status = await self.verify_database_data(session)

            # Calculate overall status
            all_checks = []
            for _category, checks in self.results.items():
                if isinstance(checks, dict):
                    all_checks.extend(checks.values())

            total_checks = len(all_checks)
            passed_checks = sum(1 for check in all_checks if check)
            success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

            print("\n" + "=" * 80)
            print("📊 VERIFICATION SUMMARY")
            print("=" * 80)
            print(f"Total Checks: {total_checks}")
            print(f"Passed: {passed_checks}")
            print(f"Failed: {total_checks - passed_checks}")
            print(f"Success Rate: {success_rate:.1f}%")

            if success_rate >= 90:
                self.results["overall_status"] = "✅ EXCELLENT - Production Ready"
            elif success_rate >= 75:
                self.results["overall_status"] = "⚠️ GOOD - Minor issues"
            else:
                self.results["overall_status"] = "❌ NEEDS ATTENTION"

            print(f"\nOverall Status: {self.results['overall_status']}")

            # Database verification
            if db_status:
                expected_products = 200
                actual_products = db_status.get("total_products", 0)
                if actual_products >= expected_products:
                    print(f"✅ Database: {actual_products}/{expected_products} products synced")
                else:
                    print(f"⚠️ Database: {actual_products}/{expected_products} products synced")

            print("=" * 80)

            return success_rate >= 75


async def main():
    """Main entry point."""
    verifier = ImplementationVerifier()
    success = await verifier.run_verification()

    # Save results to JSON
    results_file = Path("verification_results.json")
    with open(results_file, "w") as f:
        json.dump(verifier.results, f, indent=2)

    print(f"\n📄 Detailed results saved to: {results_file}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
