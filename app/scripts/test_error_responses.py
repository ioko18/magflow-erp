#!/usr/bin/env python3
"""
Test script to verify RFC 9457 Problem Details error responses.

This script makes requests to the API and verifies that error responses
follow the Problem Details for HTTP APIs specification (RFC 9457).
"""
import json
import sys
import uuid
from typing import Dict, Any, Optional

import httpx
from rich.console import Console
from rich.table import Table

# Configuration
BASE_URL = "http://localhost:8000"  # Update if your API is running on a different URL
API_PREFIX = "/api/v1"

console = Console()

def print_test_result(name: str, passed: bool, details: str = "") -> None:
    """Print a formatted test result."""
    status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
    console.print(f"{status} {name}")
    if details and not passed:
        console.print(f"  Details: {details}", style="dim")

def test_validation_error() -> bool:
    """Test validation error response."""
    try:
        response = httpx.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"username": "", "password": ""},
            timeout=10.0
        )
        
        if response.status_code != 422:
            print_test_result(
                "Validation Error - Status Code",
                False,
                f"Expected 422, got {response.status_code}"
            )
            return False
            
        content_type = response.headers.get("content-type", "")
        if "application/problem+json" not in content_type:
            print_test_result(
                "Validation Error - Content Type",
                False,
                f"Expected application/problem+json, got {content_type}"
            )
            return False
            
        data = response.json()
        required_fields = ["type", "title", "status", "detail", "errors"]
        missing = [field for field in required_fields if field not in data]
        
        if missing:
            print_test_result(
                "Validation Error - Missing Fields",
                False,
                f"Missing required fields: {', '.join(missing)}"
            )
            return False
            
        print_test_result("Validation Error", True)
        return True
        
    except Exception as e:
        print_test_result("Validation Error - Exception", False, str(e))
        return False

def test_not_found() -> bool:
    """Test not found error response."""
    try:
        non_existent_id = str(uuid.uuid4())
        response = httpx.get(
            f"{BASE_URL}{API_PREFIX}/products/{non_existent_id}",
            timeout=10.0
        )
        
        if response.status_code != 404:
            print_test_result(
                "Not Found - Status Code",
                False,
                f"Expected 404, got {response.status_code}"
            )
            return False
            
        content_type = response.headers.get("content-type", "")
        if "application/problem+json" not in content_type:
            print_test_result(
                "Not Found - Content Type",
                False,
                f"Expected application/problem+json, got {content_type}"
            )
            return False
            
        data = response.json()
        required_fields = ["type", "title", "status", "detail", "instance"]
        missing = [field for field in required_fields if field not in data]
        
        if missing:
            print_test_result(
                "Not Found - Missing Fields",
                False,
                f"Missing required fields: {', '.join(missing)}"
            )
            return False
            
        print_test_result("Not Found", True)
        return True
        
    except Exception as e:
        print_test_result("Not Found - Exception", False, str(e))
        return False

def test_unauthorized() -> bool:
    """Test unauthorized error response."""
    try:
        response = httpx.get(
            f"{BASE_URL}{API_PREFIX}/users/me",
            timeout=10.0
        )
        
        if response.status_code != 401:
            print_test_result(
                "Unauthorized - Status Code",
                False,
                f"Expected 401, got {response.status_code}"
            )
            return False
            
        if "www-authenticate" not in response.headers:
            print_test_result(
                "Unauthorized - Missing WWW-Authenticate Header",
                False,
                "WWW-Authenticate header is missing"
            )
            return False
            
        content_type = response.headers.get("content-type", "")
        if "application/problem+json" not in content_type:
            print_test_result(
                "Unauthorized - Content Type",
                False,
                f"Expected application/problem+json, got {content_type}"
            )
            return False
            
        data = response.json()
        required_fields = ["type", "title", "status", "detail"]
        missing = [field for field in required_fields if field not in data]
        
        if missing:
            print_test_result(
                "Unauthorized - Missing Fields",
                False,
                f"Missing required fields: {', '.join(missing)}"
            )
            return False
            
        print_test_result("Unauthorized", True)
        return True
        
    except Exception as e:
        print_test_result("Unauthorized - Exception", False, str(e))
        return False

def run_tests():
    """Run all tests and display results."""
    console.rule("Testing Error Responses")
    
    tests = [
        ("Validation Error", test_validation_error),
        ("Not Found", test_not_found),
        ("Unauthorized", test_unauthorized),
    ]
    
    results = {}
    for name, test_func in tests:
        results[name] = test_func()
    
    # Print summary
    console.rule("Test Summary")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Test", style="cyan")
    table.add_column("Result", justify="right")
    
    for name, result in results.items():
        status = "[green]PASS[/green]" if result else "[red]FAIL[/red]"
        table.add_row(name, status)
    
    console.print(table)
    console.print(f"\n[bold]Results:[/bold] {passed} passed, {total - passed} failed")
    
    # Return non-zero exit code if any test failed
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    run_tests()
