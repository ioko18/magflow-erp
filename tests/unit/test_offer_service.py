"""Test script for the eMAG Offer Service."""

import asyncio
import os
import sys
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the offer service and models
from app.integrations.emag.models.requests.offer import (
    OfferStatus,
    ProductOfferBulkUpdate,
    ProductOfferCreate,
    ProductOfferFilter,
    ProductOfferUpdate,
)
from app.integrations.emag.services.offer_service import OfferService


# Mock HTTP client for testing
class MockHttpClient:
    """Mock HTTP client for testing the offer service."""

    def __init__(self):
        """Initialize the mock HTTP client with test data."""
        self.offers = {}
        self.next_id = 1000

        # Add some test data
        self._add_test_data()

    def _add_test_data(self):
        """Add some test data."""
        test_offers = [
            {
                "product_id": "TEST-001",
                "product_name": "Test Product 1",
                "part_number": "TP001",
                "brand_id": 1,
                "brand_name": "Test Brand",
                "category_id": 100,
                "price": 100.0,
                "sale_price": 89.99,
                "vat_rate": 19.0,
                "stock": 50,
                "status": "active",
                "handling_time": 2,
                "warranty": 24,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
            },
            {
                "product_id": "TEST-002",
                "product_name": "Test Product 2",
                "part_number": "TP002",
                "brand_id": 2,
                "brand_name": "Another Brand",
                "category_id": 101,
                "price": 199.99,
                "vat_rate": 9.0,
                "stock": 25,
                "status": "active",
                "handling_time": 3,
                "warranty": 12,
                "created_at": "2023-01-02T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
            },
            {
                "product_id": "TEST-003",
                "product_name": "Test Product 3",
                "part_number": "TP003",
                "brand_id": 1,
                "brand_name": "Test Brand",
                "category_id": 100,
                "price": 49.99,
                "vat_rate": 19.0,
                "stock": 0,
                "status": "out_of_stock",
                "handling_time": 5,
                "warranty": 6,
                "created_at": "2023-01-03T00:00:00Z",
                "updated_at": "2023-01-03T00:00:00Z",
            },
        ]

        for offer in test_offers:
            self._create_offer(offer)

    def _build_price(
        self,
        price: float,
        vat_rate: float | None,
        sale_price: float | None = None,
        currency: str = "RON",
    ) -> dict[str, Any]:
        """Create a structured price payload compatible with the response model."""

        vat = float(vat_rate) if vat_rate is not None else 0.0
        base_price = float(price)
        current_price = float(sale_price) if sale_price is not None else base_price

        return {
            "current": current_price,
            "initial": base_price,
            "currency": currency,
            "vat_rate": vat,
            "vat_amount": current_price * vat / 100,
        }

    def _build_stock(self, quantity: int | None) -> dict[str, Any]:
        """Create a structured stock payload compatible with the response model."""

        qty = int(quantity) if quantity is not None else 0
        return {
            "available_quantity": qty,
            "initial_quantity": max(qty, 0),
            "reserved_quantity": 0,
            "sold_quantity": 0,
        }

    def _update_price_fields(self, product_id: str, updates: dict[str, Any]) -> None:
        """Update price-related fields for an offer."""

        if not {"price", "sale_price", "vat_rate"}.intersection(updates.keys()):
            return

        offer = self.offers[product_id]
        existing_price = offer["price"]
        base_price = float(updates.get("price", existing_price["initial"]))
        vat_rate = float(updates.get("vat_rate", existing_price["vat_rate"]))

        existing_sale_price = (
            existing_price["current"]
            if existing_price["current"] != existing_price["initial"]
            else None
        )
        sale_price = updates.get("sale_price", existing_sale_price)
        if sale_price is not None and sale_price == base_price:
            sale_price = None

        offer["price"] = self._build_price(
            price=base_price,
            vat_rate=vat_rate,
            sale_price=sale_price,
            currency=existing_price.get("currency", "RON"),
        )

    def _apply_offer_updates(
        self, product_id: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply update payload to an existing offer."""

        offer = self.offers[product_id]

        if "product_name" in updates:
            offer["name"] = updates["product_name"]
        if "part_number" in updates:
            offer["part_number"] = updates["part_number"]

        self._update_price_fields(product_id, updates)

        if "stock" in updates:
            stock_qty = int(updates["stock"])
            offer_stock = offer.setdefault("stock", self._build_stock(stock_qty))
            offer_stock["available_quantity"] = stock_qty
            offer_stock["initial_quantity"] = max(
                offer_stock.get("initial_quantity", stock_qty),
                stock_qty,
            )

        if "status" in updates and updates["status"] is not None:
            offer["status"] = updates["status"]

        if "handling_time" in updates and updates["handling_time"] is not None:
            offer["handling_time"] = updates["handling_time"]

        if "warranty" in updates and updates["warranty"] is not None:
            offer["warranty"] = updates["warranty"]

        offer["updated_at"] = datetime.now(UTC).isoformat()
        return offer

    def _create_offer(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new offer in the mock database."""
        emag_id = self.next_id
        self.next_id += 1

        created_at = data.get("created_at", datetime.now(UTC).isoformat())
        updated_at = (
            data.get("updated_at", created_at) or datetime.now(UTC).isoformat()
        )
        vat_rate = data.get("vat_rate", 0.0)
        sale_price = data.get("sale_price")
        stock_qty = data.get("stock", 0)

        offer = {
            "id": emag_id,
            "emag_id": emag_id,
            "product_id": data["product_id"],
            "part_number": data.get("part_number"),
            "name": data.get("product_name", data["product_id"]),
            "category_id": data["category_id"],
            "brand_id": data["brand_id"],
            "brand_name": data["brand_name"],
            "price": self._build_price(
                price=data["price"],
                vat_rate=vat_rate,
                sale_price=sale_price,
            ),
            "stock": self._build_stock(stock_qty),
            "status": data.get("status", OfferStatus.ACTIVE.value),
            "images": data.get("images", []),
            "characteristics": data.get("characteristics", []),
            "url": f"https://www.emag.ro/test-product-{emag_id}",
            "created_at": created_at,
            "updated_at": updated_at,
            "handling_time": data.get("handling_time"),
            "warranty": data.get("warranty"),
            "description": data.get("description"),
        }

        self.offers[data["product_id"]] = offer
        return offer

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> Any:
        """Mock GET request."""
        # Reduced delay for testing
        await asyncio.sleep(0.001)

        if endpoint == "product_offer/read":
            if "product_id" in params:
                # Get single offer
                product_id = params["product_id"]
                if product_id in self.offers:
                    offer = self.offers[product_id]
                    payload = {
                        "isError": False,
                        "messages": [],
                        "results": [offer],
                        "currentPage": 1,
                        "itemsPerPage": 1,
                        "totalItems": 1,
                        "totalPages": 1,
                    }
                    return self._to_response_model(payload, response_model)
                return self._error_response("Product not found", 404)
            # List offers with optional filtering
            page = int(params.get("page", 1))
            per_page = min(100, int(params.get("per_page", 50)))

            # Apply filters
            filtered = list(self.offers.values())

            if "status" in params:
                filtered = [o for o in filtered if o["status"] == params["status"]]
            if "category_id" in params:
                filtered = [
                    o for o in filtered if o["category_id"] == params["category_id"]
                ]
            if "brand_id" in params:
                filtered = [o for o in filtered if o["brand_id"] == params["brand_id"]]
            if "in_stock" in params:
                in_stock = params["in_stock"]
                if in_stock:
                    filtered = [o for o in filtered if o["stock"] > 0]
                else:
                    filtered = [o for o in filtered if o["stock"] <= 0]

            # Paginate
            total = len(filtered)
            start = (page - 1) * per_page
            end = start + per_page
            paginated = filtered[start:end]

            return self._to_response_model(
                {
                    "isError": False,
                    "messages": [],
                    "results": paginated,
                    "currentPage": page,
                    "itemsPerPage": per_page,
                    "totalItems": total,
                    "totalPages": (total + per_page - 1) // per_page,
                },
                response_model,
            )

        return self._error_response(f"Unknown endpoint: {endpoint}", 404)

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> Any:
        """Mock POST request."""
        # Reduced delay for testing
        await asyncio.sleep(0.001)

        if endpoint == "product_offer/save":
            if "offers" in data:
                # Bulk update
                results = []
                for offer_data in data["offers"]:
                    try:
                        product_id = offer_data["product_id"]
                        if product_id in self.offers:
                            # Update existing
                            updated_offer = self._apply_offer_updates(
                                product_id,
                                offer_data,
                            )
                            result = {
                                "product_id": product_id,
                                "success": True,
                                "message": "Updated successfully",
                                "emag_id": updated_offer["emag_id"],
                            }
                        else:
                            # Create new
                            offer = self._create_offer(offer_data)
                            result = {
                                "product_id": product_id,
                                "success": True,
                                "message": "Created successfully",
                                "emag_id": offer["emag_id"],
                            }
                        results.append(result)
                    except Exception as e:
                        results.append(
                            {
                                "product_id": offer_data.get("product_id", "unknown"),
                                "success": False,
                                "message": str(e),
                                "errors": [
                                    {"code": "processing_error", "message": str(e)},
                                ],
                            },
                        )

                return self._to_response_model(
                    {"isError": False, "messages": [], "results": results},
                    response_model,
                )
            # Single offer create/update
            product_id = data.get("product_id")
            if not product_id:
                return self._error_response("product_id is required", 400)

            if product_id in self.offers:
                # Update existing
                updated_offer = self._apply_offer_updates(product_id, data)
                result = [updated_offer]
            else:
                # Create new
                result = [self._create_offer(data)]

            return self._to_response_model(
                {
                    "isError": False,
                    "messages": [],
                    "results": result,
                    "currentPage": 1,
                    "itemsPerPage": 1,
                    "totalItems": 1,
                    "totalPages": 1,
                },
                response_model,
            )

        return self._error_response(f"Unknown endpoint: {endpoint}", 404)

    async def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> Any:
        """Mock PUT request."""
        # For testing, we'll treat PUT the same as POST
        return await self.post(endpoint, data, response_model)

    async def delete(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> Any:
        """Mock DELETE request."""
        # Reduced delay for testing
        await asyncio.sleep(0.001)

        if endpoint == "product_offer/delete":
            product_id = data.get("product_id")
            if not product_id:
                return self._error_response("product_id is required", 400)

            if product_id in self.offers:
                del self.offers[product_id]
                return {"success": True}
            return self._error_response("Product not found", 404)

        return self._error_response(f"Unknown endpoint: {endpoint}", 404)

    def _error_response(self, message: str, status_code: int) -> dict[str, Any]:
        """Create an error response."""
        return {
            "isError": True,
            "messages": [{"message": message}],
            "status_code": status_code,
        }

    def _to_response_model(self, data: dict[str, Any], response_model: Any) -> Any:
        """Convert data to the specified response model."""
        if response_model is None:
            return data

        if hasattr(response_model, "__origin__") and response_model.__origin__ is list:
            # Handle List[Model] case
            item_model = response_model.__args__[0]
            return [item_model(**item) for item in data]

        return response_model(**data)


# Mock rate limiter for testing
class MockRateLimiter:
    """Mock rate limiter for testing."""

    async def wait_for_capacity(self, is_order_endpoint: bool = False):
        """Simulate rate limiting with minimal delay."""
        await asyncio.sleep(0.0001)  # Minimal delay for testing


@pytest.mark.asyncio
async def test_offer_service():
    """Test the offer service with mock data."""
    # Create mock dependencies
    http_client = MockHttpClient()
    rate_limiter = MockRateLimiter()

    # Create the service with patched rate limiter to avoid sleeps in tests
    with patch(
        "app.integrations.emag.services.offer_service.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        service = OfferService(http_client, rate_limiter)
        mock_sleep.return_value = None  # Skip sleeps in the actual service

    try:
        # Test 1: Get all offers
        print("1. Testing list_offers()...")
        offers = await service.list_offers()
        print(f"   Found {len(offers.results)} offers")
        for i, offer in enumerate(offers.results[:3], 1):
            print(
                f"   {i}. {offer.product_name} (ID: {offer.product_id}, "
                f"Price: {offer.price.current})",
            )

        # Test 2: Get a single offer
        print("\n2. Testing get_offer()...")
        if offers.results:
            product_id = offers.results[0].product_id
            offer = await service.get_offer(product_id)
            print(f"   Found offer: {offer.product_name} (Status: {offer.status})")
            print(
                f"   Price: {offer.price.current} {offer.price.currency} "
                f"(VAT: {offer.price.vat_rate}%)",
            )
            print(f"   Stock: {offer.stock.available_quantity} available")

        # Test 3: Create a new offer
        print("\n3. Testing create_offer()...")
        new_offer = ProductOfferCreate(
            product_id="TEST-NEW-001",
            product_name="New Test Product",
            part_number="NTP001",
            brand_id=3,
            brand_name="New Brand",
            category_id=200,
            price=149.99,
            vat_rate=19.0,
            stock=100,
            handling_time=2,
            warranty=24,
        )
        created_offer = await service.create_offer(new_offer)
        print(
            f"   Created offer: {created_offer.product_name} (ID: {created_offer.product_id})",
        )
        print(f"   eMAG ID: {created_offer.emag_id}, URL: {created_offer.url}")

        # Test 4: Update an offer
        print("\n4. Testing update_offer()...")
        update_data = {"price": 159.99, "sale_price": 139.99, "stock": 95}
        updated_offer = await service.update_offer(
            product_id=created_offer.product_id,
            update_data=ProductOfferUpdate(**update_data),
        )
        print(f"   Updated offer: {updated_offer.product_name}")
        print(
            f"   New price: {updated_offer.price.current} (was: {created_offer.price.current})",
        )
        print(
            f"   New stock: {updated_offer.stock.available_quantity} "
            f"(was: {created_offer.stock.available_quantity})",
        )

        # Test 5: Bulk update offers
        print("\n5. Testing bulk_update_offers()...")
        bulk_updates = ProductOfferBulkUpdate(
            offers=[
                {"product_id": "TEST-001", "stock": 45},
                {"product_id": "TEST-002", "price": 189.99},
                {"product_id": "NON-EXISTENT", "price": 9.99},  # This should fail
            ],
        )
        bulk_result = await service.bulk_update_offers(bulk_updates)
        success_count = sum(1 for r in bulk_result.results if r.success)
        failure_count = sum(1 for r in bulk_result.results if not r.success)
        print(
            f"   Bulk update results: {success_count} succeeded, "
            f"{failure_count} failed",
        )

        # Test 6: Filter offers
        print("\n6. Testing offer filtering...")
        filter_active = ProductOfferFilter(status=OfferStatus.ACTIVE)
        active_offers = await service.list_offers(filters=filter_active)
        print(f"   Found {active_offers.total_items} active offers")

        filter_brand = ProductOfferFilter(brand_id=1)
        brand_offers = await service.list_offers(filters=filter_brand)
        print(f"   Found {brand_offers.total_items} offers from brand ID 1")

        # Test 7: Delete an offer
        print("\n7. Testing delete_offer()...")
        if created_offer:
            result = await service.delete_offer(created_offer.product_id)
            print(f"   Delete {'succeeded' if result else 'failed'}")

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e!s}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(test_offer_service())
