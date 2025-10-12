#!/usr/bin/env python3
"""
End-to-End Test for eMAG Product Publishing

Tests real API endpoints with actual eMAG API integration.
Run this script to verify the complete product publishing workflow.

Usage:
    python test_product_publishing_e2e.py
"""

import asyncio
import sys

import httpx

# Configuration
BASE_URL = "http://localhost:8000"
CREDENTIALS = {
    "username": "admin@example.com",
    "password": "secret"
}


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


class ProductPublishingE2ETest:
    """End-to-end test suite for product publishing"""

    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    async def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        console.print("\n[bold blue]🔐 Authenticating...[/bold blue]")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json=CREDENTIALS,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    console.print("[green]✓ Authentication successful[/green]")
                    return True
                else:
                    console.print(f"[red]✗ Authentication failed: {response.status_code}[/red]")
                    return False
        except Exception as e:
            console.print(f"[red]✗ Authentication error: {str(e)}[/red]")
            return False

    def get_headers(self) -> dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}

    async def test_vat_rates(self) -> bool:
        """Test VAT rates endpoint"""
        console.print("\n[bold blue]📊 Testing VAT Rates Endpoint...[/bold blue]")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/publishing/vat-rates?account_type=main",
                    headers=self.get_headers(),
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    count = data.get("data", {}).get("count", 0)
                    console.print(f"[green]✓ VAT Rates: {count} rates found[/green]")
                    self.results["passed"] += 1
                    return True
                else:
                    console.print(f"[red]✗ VAT Rates failed: {response.status_code}[/red]")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"VAT Rates: {response.text}")
                    return False
        except Exception as e:
            console.print(f"[red]✗ VAT Rates error: {str(e)}[/red]")
            self.results["failed"] += 1
            self.results["errors"].append(f"VAT Rates: {str(e)}")
            return False

    async def test_handling_times(self) -> bool:
        """Test handling times endpoint"""
        console.print("\n[bold blue]⏱️  Testing Handling Times Endpoint...[/bold blue]")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/publishing/handling-times?account_type=main",
                    headers=self.get_headers(),
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    count = data.get("data", {}).get("count", 0)
                    console.print(f"[green]✓ Handling Times: {count} options found[/green]")
                    self.results["passed"] += 1
                    return True
                else:
                    console.print(f"[red]✗ Handling Times failed: {response.status_code}[/red]")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"Handling Times: {response.text}")
                    return False
        except Exception as e:
            console.print(f"[red]✗ Handling Times error: {str(e)}[/red]")
            self.results["failed"] += 1
            self.results["errors"].append(f"Handling Times: {str(e)}")
            return False

    async def test_categories(self) -> bool:
        """Test categories endpoint"""
        console.print("\n[bold blue]📁 Testing Categories Endpoint...[/bold blue]")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/publishing/categories?current_page=1&items_per_page=5&account_type=main",
                    headers=self.get_headers(),
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("data", {}).get("results", [])
                    console.print(f"[green]✓ Categories: {len(results)} categories retrieved[/green]")

                    # Display first few categories
                    if results:
                        table = Table(title="Sample Categories")
                        table.add_column("ID", style="cyan")
                        table.add_column("Name", style="green")
                        table.add_column("Allowed", style="yellow")

                        for cat in results[:3]:
                            table.add_row(
                                str(cat.get("id", "N/A")),
                                cat.get("name", "N/A"),
                                "✓" if cat.get("is_allowed") == 1 else "✗"
                            )
                        console.print(table)

                    self.results["passed"] += 1
                    return True
                else:
                    console.print(f"[red]✗ Categories failed: {response.status_code}[/red]")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"Categories: {response.text}")
                    return False
        except Exception as e:
            console.print(f"[red]✗ Categories error: {str(e)}[/red]")
            self.results["failed"] += 1
            self.results["errors"].append(f"Categories: {str(e)}")
            return False

    async def test_allowed_categories(self) -> bool:
        """Test allowed categories endpoint"""
        console.print("\n[bold blue]✅ Testing Allowed Categories Endpoint...[/bold blue]")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/publishing/categories/allowed?account_type=main",
                    headers=self.get_headers(),
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    categories = data.get("data", {}).get("categories", [])
                    console.print(f"[green]✓ Allowed Categories: {len(categories)} categories[/green]")
                    self.results["passed"] += 1
                    return True
                else:
                    console.print(f"[red]✗ Allowed Categories failed: {response.status_code}[/red]")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"Allowed Categories: {response.text}")
                    return False
        except Exception as e:
            console.print(f"[red]✗ Allowed Categories error: {str(e)}[/red]")
            self.results["failed"] += 1
            self.results["errors"].append(f"Allowed Categories: {str(e)}")
            return False

    async def test_category_by_id(self) -> bool:
        """Test get category by ID endpoint"""
        console.print("\n[bold blue]🔍 Testing Get Category by ID Endpoint...[/bold blue]")

        # First get a category ID
        try:
            async with httpx.AsyncClient() as client:
                # Get categories list first
                response = await client.get(
                    f"{self.base_url}/api/v1/emag/publishing/categories?current_page=1&items_per_page=1&account_type=main",
                    headers=self.get_headers(),
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("data", {}).get("results", [])
                    if results:
                        category_id = results[0].get("id")

                        # Now get specific category
                        response = await client.get(
                            f"{self.base_url}/api/v1/emag/publishing/categories/{category_id}?account_type=main",
                            headers=self.get_headers(),
                            timeout=30.0
                        )

                        if response.status_code == 200:
                            data = response.json()
                            console.print(f"[green]✓ Category Details: Retrieved category {category_id}[/green]")
                            self.results["passed"] += 1
                            return True
                        else:
                            console.print(f"[red]✗ Category Details failed: {response.status_code}[/red]")
                            self.results["failed"] += 1
                            return False
                    else:
                        console.print("[yellow]⚠ No categories available to test[/yellow]")
                        return True
                else:
                    console.print(f"[red]✗ Category Details failed: {response.status_code}[/red]")
                    self.results["failed"] += 1
                    return False
        except Exception as e:
            console.print(f"[red]✗ Category Details error: {str(e)}[/red]")
            self.results["failed"] += 1
            self.results["errors"].append(f"Category Details: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all end-to-end tests"""
        console.print(Panel.fit(
            "[bold cyan]eMAG Product Publishing - End-to-End Tests[/bold cyan]\n"
            f"Testing against: {self.base_url}",
            border_style="cyan"
        ))

        # Authenticate first
        if not await self.authenticate():
            console.print("\n[bold red]❌ Authentication failed. Cannot proceed with tests.[/bold red]")
            return False

        # Run all tests
        await self.test_vat_rates()
        await self.test_handling_times()
        await self.test_categories()
        await self.test_allowed_categories()
        await self.test_category_by_id()

        # Display results
        self.display_results()

        return self.results["failed"] == 0

    def display_results(self):
        """Display test results summary"""
        console.print("\n" + "="*60)

        total = self.results["passed"] + self.results["failed"]
        pass_rate = (self.results["passed"] / total * 100) if total > 0 else 0

        results_table = Table(title="Test Results Summary", show_header=True)
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")

        results_table.add_row("Total Tests", str(total))
        results_table.add_row("Passed", f"[green]{self.results['passed']}[/green]")
        results_table.add_row("Failed", f"[red]{self.results['failed']}[/red]")
        results_table.add_row("Pass Rate", f"{pass_rate:.1f}%")

        console.print(results_table)

        if self.results["errors"]:
            console.print("\n[bold red]Errors:[/bold red]")
            for error in self.results["errors"]:
                console.print(f"  • {error}")

        if self.results["failed"] == 0:
            console.print("\n[bold green]✅ All tests passed![/bold green]")
        else:
            console.print(f"\n[bold red]❌ {self.results['failed']} test(s) failed[/bold red]")


async def main():
    """Main entry point"""
    tester = ProductPublishingE2ETest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {str(e)}[/bold red]")
        sys.exit(1)
