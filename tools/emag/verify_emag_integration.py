#!/usr/bin/env python3
"""
eMAG Integration Verification Script
Comprehensive test of all eMAG integration components
"""

import json
import sys
from datetime import datetime
from typing import Any

import requests

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
CREDENTIALS = {"username": "admin@example.com", "password": "secret"}


class EmagIntegrationVerifier:
    def __init__(self):
        self.token = None
        self.headers = {}
        self.results = {
            "authentication": False,
            "database_products": 0,
            "main_products": 0,
            "fbe_products": 0,
            "total_offers": 0,
            "api_endpoints": {},
            "frontend_accessible": False,
            "errors": [],
        }

    def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        try:
            print("🔐 Testing authentication...")
            response = requests.post(LOGIN_URL, json=CREDENTIALS, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                self.results["authentication"] = True
                print("✅ Authentication successful")
                return True
            else:
                self.results["errors"].append(
                    f"Authentication failed: {response.status_code}"
                )
                print(f"❌ Authentication failed: {response.status_code}")
                return False

        except Exception as e:
            self.results["errors"].append(f"Authentication error: {str(e)}")
            print(f"❌ Authentication error: {str(e)}")
            return False

    def test_database_products(self) -> bool:
        """Test database product counts"""
        try:
            print("🗄️ Testing database products...")

            # Test database connection via API
            response = requests.get(
                f"{BASE_URL}/api/v1/emag/enhanced/products/all?account_type=both&max_pages_per_account=1",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.results["database_products"] = len(data)
                    print(f"✅ Database products: {len(data)}")
                    return True
                elif isinstance(data, dict) and "total_count" in data:
                    self.results["database_products"] = data.get("total_count", 0)
                    print(f"✅ Database products: {data.get('total_count', 0)}")
                    return True
                else:
                    self.results["errors"].append("Invalid products response format")
                    print("❌ Invalid products response format")
                    return False
            else:
                self.results["errors"].append(
                    f"Database products test failed: {response.status_code}"
                )
                print(f"❌ Database products test failed: {response.status_code}")
                return False

        except Exception as e:
            self.results["errors"].append(f"Database products error: {str(e)}")
            print(f"❌ Database products error: {str(e)}")
            return False

    def test_account_products(self) -> bool:
        """Test MAIN and FBE account products"""
        try:
            print("📱 Testing MAIN account products...")

            # Test MAIN account
            response = requests.get(
                f"{BASE_URL}/api/v1/emag/enhanced/products/all?account_type=main&max_pages_per_account=1",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self.results["main_products"] = data.get("total_count", 0)
                print(f"✅ MAIN products: {self.results['main_products']}")
            else:
                self.results["errors"].append(
                    f"MAIN products test failed: {response.status_code}"
                )
                print(f"❌ MAIN products test failed: {response.status_code}")
                return False

            print("🏪 Testing FBE account products...")

            # Test FBE account
            response = requests.get(
                f"{BASE_URL}/api/v1/emag/enhanced/products/all?account_type=fbe&max_pages_per_account=1",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self.results["fbe_products"] = data.get("total_count", 0)
                print(f"✅ FBE products: {self.results['fbe_products']}")
                return True
            else:
                self.results["errors"].append(
                    f"FBE products test failed: {response.status_code}"
                )
                print(f"❌ FBE products test failed: {response.status_code}")
                return False

        except Exception as e:
            self.results["errors"].append(f"Account products error: {str(e)}")
            print(f"❌ Account products error: {str(e)}")
            return False

    def test_offers(self) -> bool:
        """Test offers endpoint"""
        try:
            print("🛒 Testing offers...")

            response = requests.get(
                f"{BASE_URL}/api/v1/emag/enhanced/offers/all?account_type=both&max_pages_per_account=1",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self.results["total_offers"] = data.get("total_count", 0)
                print(f"✅ Total offers: {self.results['total_offers']}")
                return True
            else:
                self.results["errors"].append(
                    f"Offers test failed: {response.status_code}"
                )
                print(f"❌ Offers test failed: {response.status_code}")
                return False

        except Exception as e:
            self.results["errors"].append(f"Offers error: {str(e)}")
            print(f"❌ Offers error: {str(e)}")
            return False

    def test_api_endpoints(self) -> bool:
        """Test all API endpoints"""
        endpoints = {
            "health": "/health",
            "products_all": "/api/v1/emag/enhanced/products/all?account_type=both&max_pages_per_account=1",
            "offers_all": "/api/v1/emag/enhanced/offers/all?account_type=both&max_pages_per_account=1",
            "status_main": "/api/v1/emag/enhanced/status?account_type=main",
            "status_fbe": "/api/v1/emag/enhanced/status?account_type=fbe",
            "sync_progress": "/api/v1/emag/enhanced/products/sync-progress",
        }

        print("🌐 Testing API endpoints...")

        for name, endpoint in endpoints.items():
            try:
                headers = self.headers if name != "health" else {}
                response = requests.get(
                    f"{BASE_URL}{endpoint}", headers=headers, timeout=15
                )

                self.results["api_endpoints"][name] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                }

                status = "✅" if response.status_code == 200 else "❌"
                print(f"  {status} {name}: {response.status_code}")

            except Exception as e:
                self.results["api_endpoints"][name] = {
                    "status_code": None,
                    "success": False,
                    "error": str(e),
                }
                print(f"  ❌ {name}: {str(e)}")

        return True

    def test_frontend(self) -> bool:
        """Test frontend accessibility"""
        try:
            print("📱 Testing frontend...")

            response = requests.get("http://localhost:5173", timeout=10)

            if response.status_code == 200:
                self.results["frontend_accessible"] = True
                print("✅ Frontend accessible")
                return True
            else:
                self.results["errors"].append(
                    f"Frontend test failed: {response.status_code}"
                )
                print(f"❌ Frontend test failed: {response.status_code}")
                return False

        except Exception as e:
            self.results["errors"].append(f"Frontend error: {str(e)}")
            print(f"❌ Frontend error: {str(e)}")
            return False

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive report"""
        total_products = self.results["main_products"] + self.results["fbe_products"]

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "authentication": self.results["authentication"],
                "total_products": total_products,
                "main_products": self.results["main_products"],
                "fbe_products": self.results["fbe_products"],
                "total_offers": self.results["total_offers"],
                "frontend_accessible": self.results["frontend_accessible"],
                "api_endpoints_working": sum(
                    1
                    for ep in self.results["api_endpoints"].values()
                    if ep.get("success", False)
                ),
                "total_api_endpoints": len(self.results["api_endpoints"]),
                "errors_count": len(self.results["errors"]),
            },
            "detailed_results": self.results,
            "integration_status": {
                "complete": (
                    self.results["authentication"]
                    and total_products >= 200
                    and self.results["main_products"] >= 100
                    and self.results["fbe_products"] >= 100
                    and self.results["frontend_accessible"]
                    and len(
                        [
                            e
                            for e in self.results["errors"]
                            if "sync_progress" not in e.lower()
                        ]
                    )
                    == 0
                ),
                "requirements_met": {
                    "authentication_working": self.results["authentication"],
                    "200_products_synced": total_products >= 200,
                    "100_main_products": self.results["main_products"] >= 100,
                    "100_fbe_products": self.results["fbe_products"] >= 100,
                    "frontend_accessible": self.results["frontend_accessible"],
                    "no_critical_errors": len(self.results["errors"]) == 0,
                },
            },
        }

        return report

    def run_verification(self) -> dict[str, Any]:
        """Run complete verification"""
        print("🚀 Starting eMAG Integration Verification")
        print("=" * 50)

        # Run all tests
        self.authenticate()
        self.test_database_products()
        self.test_account_products()
        self.test_offers()
        self.test_api_endpoints()
        self.test_frontend()

        # Generate report
        report = self.generate_report()

        print("\n" + "=" * 50)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 50)

        summary = report["summary"]
        print(f"🔐 Authentication: {'✅' if summary['authentication'] else '❌'}")
        print(f"📦 Total Products: {summary['total_products']} (Target: 200)")
        print(f"📱 MAIN Products: {summary['main_products']} (Target: 100)")
        print(f"🏪 FBE Products: {summary['fbe_products']} (Target: 100)")
        print(f"🛒 Total Offers: {summary['total_offers']}")
        print(
            f"🌐 API Endpoints: {summary['api_endpoints_working']}/{summary['total_api_endpoints']} working"
        )
        print(f"📱 Frontend: {'✅' if summary['frontend_accessible'] else '❌'}")
        print(f"❌ Errors: {summary['errors_count']}")

        integration_complete = report["integration_status"]["complete"]
        print(
            f"\n🎯 INTEGRATION STATUS: {'✅ COMPLETE' if integration_complete else '❌ INCOMPLETE'}"
        )

        if not integration_complete:
            print("\n❌ Requirements not met:")
            for req, met in report["integration_status"]["requirements_met"].items():
                if not met:
                    print(f"  - {req}")

        if self.results["errors"]:
            print("\n❌ Errors encountered:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        return report


def main():
    """Main verification function"""
    verifier = EmagIntegrationVerifier()
    report = verifier.run_verification()

    # Save report to file
    with open("emag_integration_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n📄 Detailed report saved to: emag_integration_report.json")

    # Exit with appropriate code
    if report["integration_status"]["complete"]:
        print("\n🎉 eMAG Integration is COMPLETE and FUNCTIONAL!")
        sys.exit(0)
    else:
        print("\n⚠️ eMAG Integration needs attention.")
        sys.exit(1)


if __name__ == "__main__":
    main()
