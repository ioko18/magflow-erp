#!/usr/bin/env python3
"""Test script for MagFlow API CRUD operations and search functionality"""

import time
from typing import Dict

import httpx

BASE_URL = "http://localhost:8010"


def measure_time(func):
    """Decorator to measure execution time"""

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"⏱️  {func.__name__} took {execution_time:.2f}ms")
        return result, execution_time

    return wrapper


@measure_time
def test_create_category(client: httpx.Client, name: str) -> Dict:
    """Test category creation"""
    response = client.post("/categories/", json={"name": name})
    print(f"✅ Created category: {response.status_code} - {response.json()}")
    return response.json()


@measure_time
def test_create_product(client: httpx.Client, name: str, price: float) -> Dict:
    """Test product creation"""
    response = client.post("/products/", json={"name": name, "price": price})
    print(f"✅ Created product: {response.status_code} - {response.json()}")
    return response.json()


@measure_time
def test_list_products(client: httpx.Client, limit: int = 10, offset: int = 0) -> Dict:
    """Test product listing"""
    response = client.get(f"/products/?limit={limit}&offset={offset}")
    result = response.json()
    print(
        f"📋 Listed products: {response.status_code} - Found {result['total']} products",
    )
    return result


@measure_time
def test_list_categories(
    client: httpx.Client,
    limit: int = 10,
    offset: int = 0,
) -> Dict:
    """Test category listing"""
    response = client.get(f"/categories/?limit={limit}&offset={offset}")
    result = response.json()
    print(
        f"📋 Listed categories: {response.status_code} - Found {result['total']} categories",
    )
    return result


@measure_time
def test_search_products(client: httpx.Client, query: str) -> Dict:
    """Test product search"""
    response = client.get(f"/products/?q={query}")
    result = response.json()
    print(
        f"🔍 Search '{query}': {response.status_code} - Found {result['total']} products",
    )
    for product in result["products"]:
        print(f"   - {product['name']} (${product['price']})")
    return result


@measure_time
def test_get_product(client: httpx.Client, product_id: int) -> Dict:
    """Test getting specific product"""
    response = client.get(f"/products/{product_id}")
    result = response.json()
    print(f"🔍 Get product {product_id}: {response.status_code} - {result['name']}")
    return result


@measure_time
def test_update_product(
    client: httpx.Client,
    product_id: int,
    name: str = None,
    price: float = None,
) -> Dict:
    """Test product update"""
    update_data = {}
    if name:
        update_data["name"] = name
    if price is not None:
        update_data["price"] = price

    response = client.put(f"/products/{product_id}", json=update_data)
    result = response.json()
    print(f"✏️  Updated product {product_id}: {response.status_code} - {result['name']}")
    return result


def main():
    """Main test function"""
    print("🚀 Starting MagFlow API Tests")
    print("=" * 50)

    times = []

    with httpx.Client(base_url=BASE_URL) as client:
        try:
            # Test health endpoint first
            health_response = client.get("/health")
            print(f"🏥 Health check: {health_response.status_code}")

            # Test Categories CRUD
            print("\n📁 Testing Categories CRUD:")
            category1, time1 = test_create_category(client, "Electronics")
            category2, time2 = test_create_category(client, "Books")
            category3, time3 = test_create_category(client, "Clothing")
            times.extend([time1, time2, time3])

            categories_list, time4 = test_list_categories(client)
            times.append(time4)

            # Test Products CRUD
            print("\n📦 Testing Products CRUD:")
            product1, time5 = test_create_product(client, "iPhone 15", 999.99)
            product2, time6 = test_create_product(client, "Samsung Galaxy", 899.99)
            product3, time7 = test_create_product(client, "iPad Pro", 1299.99)
            product4, time8 = test_create_product(client, "MacBook Air", 1199.99)
            product5, time9 = test_create_product(client, "iPhone 14", 799.99)
            times.extend([time5, time6, time7, time8, time9])

            products_list, time10 = test_list_products(client)
            times.append(time10)

            # Test individual product retrieval
            print("\n🔍 Testing Individual Product Retrieval:")
            product_detail, time11 = test_get_product(client, product1["id"])
            times.append(time11)

            # Test product updates
            print("\n✏️  Testing Product Updates:")
            updated_product, time12 = test_update_product(
                client,
                product1["id"],
                price=949.99,
            )
            times.append(time12)

            # Test Search Functionality
            print("\n🔍 Testing Search Functionality:")
            search1, time13 = test_search_products(client, "iphone")
            search2, time14 = test_search_products(client, "samsung")
            search3, time15 = test_search_products(client, "macbook")
            search4, time16 = test_search_products(client, "ipad")
            times.extend([time13, time14, time15, time16])

            # Test fuzzy search
            print("\n🔍 Testing Fuzzy Search:")
            fuzzy1, time17 = test_search_products(client, "iphon")  # Missing 'e'
            fuzzy2, time18 = test_search_products(client, "galxy")  # Missing 'a'
            times.extend([time17, time18])

            # Performance Report
            print("\n" + "=" * 50)
            print("📊 PERFORMANCE REPORT")
            print("=" * 50)
            print(f"Average response time: {sum(times) / len(times):.2f}ms")
            print(f"Fastest response: {min(times):.2f}ms")
            print(f"Slowest response: {max(times):.2f}ms")
            print(f"Total operations: {len(times)}")

            # Categorize times
            create_times = times[0:8]  # Category and product creation
            list_times = [times[3], times[9]]  # List operations
            search_times = times[12:18]  # Search operations

            print("\nOperation breakdown:")
            print(
                f"  Create operations avg: {sum(create_times) / len(create_times):.2f}ms",
            )
            print(f"  List operations avg: {sum(list_times) / len(list_times):.2f}ms")
            print(
                f"  Search operations avg: {sum(search_times) / len(search_times):.2f}ms",
            )

        except Exception as e:
            print(f"❌ Error during testing: {e}")
            return False

    print("\n✅ All tests completed successfully!")
    return True


if __name__ == "__main__":
    main()
