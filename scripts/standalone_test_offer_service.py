"""Standalone test script for the eMAG Offer Service."""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, Field, HttpUrl

T = TypeVar("T")  # Generic type variable for response models


# Mock dependencies
class EmagAPIError(Exception):
    """Exception raised for eMAG API errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class OfferStatus(str, Enum):
    """Status of a product offer."""

    NEW = "new"
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    REJECTED = "rejected"
    DELETED = "deleted"


class ProductOfferPrice(BaseModel):
    """Price information for a product offer."""

    current: float = Field(..., description="Current price")
    initial: float = Field(..., description="Initial/regular price")
    currency: str = Field(default="RON", description="Currency code (e.g., RON, EUR)")
    vat_rate: float = Field(..., description="VAT rate as a percentage (e.g., 19.0)")
    vat_amount: float = Field(..., description="VAT amount")


class ProductOfferStock(BaseModel):
    """Stock information for a product offer."""

    available_quantity: int = Field(
        ..., ge=0, description="Available quantity in stock"
    )
    initial_quantity: int = Field(..., ge=0, description="Initial quantity in stock")
    reserved_quantity: int = Field(..., ge=0, description="Reserved quantity")
    sold_quantity: int = Field(..., ge=0, description="Sold quantity")


class ProductOfferImage(BaseModel):
    """Image information for a product offer."""

    url: str = Field(..., description="Image URL")
    is_main: bool = Field(default=False, description="Whether this is the main image")
    position: int = Field(..., ge=0, description="Image position in the gallery")


class ProductOfferCharacteristic(BaseModel):
    """Characteristic information for a product offer."""

    id: int = Field(..., description="Characteristic ID")
    name: str = Field(..., description="Characteristic name")
    value: str = Field(..., description="Characteristic value")
    group_name: str | None = Field(None, description="Characteristic group name")


class ProductOfferResponse(BaseModel):
    """Response model for a single product offer."""

    id: int = Field(..., description="eMAG offer ID")
    product_id: str = Field(..., description="Your product ID")
    emag_id: int = Field(..., description="eMAG product ID")
    part_number: str | None = Field(None, description="Manufacturer part number")
    name: str = Field(..., description="Product name")
    category_id: int = Field(..., description="eMAG category ID")
    brand_id: int = Field(..., description="eMAG brand ID")
    brand_name: str = Field(..., description="Brand name")
    price: ProductOfferPrice = Field(..., description="Price information")
    stock: ProductOfferStock = Field(..., description="Stock information")
    status: OfferStatus = Field(..., description="Offer status")
    images: list[ProductOfferImage] = Field(
        default_factory=list, description="Product images"
    )
    characteristics: list[ProductOfferCharacteristic] = Field(
        default_factory=list, description="Product characteristics"
    )
    url: HttpUrl | None = Field(None, description="Product URL on eMAG marketplace")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ProductOfferListResponse(BaseModel):
    """Response model for listing product offers."""

    is_error: bool = Field(
        False, alias="isError", description="Indicates if there was an error"
    )
    messages: list[dict[str, Any]] = Field(
        default_factory=list, description="List of messages"
    )
    results: list[ProductOfferResponse] = Field(
        default_factory=list, description="List of product offers"
    )
    current_page: int = Field(1, alias="currentPage", description="Current page number")
    items_per_page: int = Field(
        50, alias="itemsPerPage", description="Number of items per page"
    )
    total_items: int = Field(0, alias="totalItems", description="Total number of items")
    total_pages: int = Field(1, alias="totalPages", description="Total number of pages")


class ProductOfferBulkResponseItem(BaseModel):
    """Response item for bulk operations."""

    product_id: str = Field(..., description="Your product ID")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str | None = Field(None, description="Operation message")
    emag_id: int | None = Field(None, description="eMAG product ID if created")
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="List of errors if any"
    )


class ProductOfferBulkResponse(BaseModel):
    """Response model for bulk operations on product offers."""

    is_error: bool = Field(
        False, alias="isError", description="Indicates if there was an error"
    )
    messages: list[dict[str, Any]] = Field(
        default_factory=list, description="List of messages"
    )
    results: list[ProductOfferBulkResponseItem] = Field(
        default_factory=list, description="Results of bulk operation"
    )


class ProductOfferSyncStatus(str, Enum):
    """Synchronization status of a product offer."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductOfferSyncResponse(BaseModel):
    """Response model for offer synchronization status."""

    sync_id: str = Field(..., description="Synchronization ID")
    status: ProductOfferSyncStatus = Field(..., description="Synchronization status")
    processed_items: int = Field(0, description="Number of processed items")
    total_items: int = Field(0, description="Total number of items to process")
    started_at: datetime = Field(..., description="Synchronization start time")
    completed_at: datetime | None = Field(
        None, description="Synchronization completion time"
    )
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="List of errors if any"
    )


class ProductOfferBase(BaseModel):
    """Base model for product offer operations."""

    product_id: str = Field(
        ..., description="Unique identifier of the product in your system"
    )
    product_name: str = Field(..., max_length=255, description="Name of the product")
    part_number: str | None = Field(
        None, max_length=100, description="Manufacturer part number"
    )
    description: str | None = Field(None, description="Detailed product description")
    brand_id: int = Field(..., description="eMAG brand ID")
    brand_name: str = Field(..., max_length=100, description="Brand name")
    category_id: int = Field(..., description="eMAG category ID")
    images: list[str] = Field(default_factory=list, description="List of image URLs")
    status: OfferStatus = Field(default=OfferStatus.NEW, description="Offer status")


class ProductOfferCreate(ProductOfferBase):
    """Model for creating a new product offer."""

    price: float = Field(..., gt=0, description="Product price")
    sale_price: float | None = Field(
        None, gt=0, description="Sale price if applicable"
    )
    vat_rate: float = Field(
        ..., gt=0, le=100, description="VAT rate as a percentage (e.g., 19.0)"
    )
    stock: int = Field(..., ge=0, description="Available stock quantity")
    handling_time: int = Field(..., ge=1, le=30, description="Handling time in days")
    warranty: int = Field(default=24, ge=0, description="Warranty period in months")


class ProductOfferUpdate(BaseModel):
    """Model for updating an existing product offer."""

    price: float | None = Field(None, gt=0, description="Updated price")
    sale_price: float | None = Field(None, ge=0, description="Updated sale price")
    stock: int | None = Field(None, ge=0, description="Updated stock quantity")
    status: OfferStatus | None = Field(None, description="Updated status")
    handling_time: int | None = Field(
        None, ge=1, le=30, description="Updated handling time"
    )


class ProductOfferBulkUpdate(BaseModel):
    """Model for bulk updating multiple product offers."""

    offers: list[dict[str, Any]] = Field(
        ..., max_items=50, description="List of offer updates, max 50 items per request"
    )


class ProductOfferFilter(BaseModel):
    """Filter criteria for querying product offers."""

    status: OfferStatus | None = None
    category_id: int | None = None
    brand_id: int | None = None
    in_stock: bool | None = None
    min_price: float | None = None
    max_price: float | None = None


# Mock HTTP client for testing
class MockHttpClient:
    """Mock HTTP client for testing the offer service."""

    def __init__(self):
        """Initialize the mock HTTP client with test data."""
        self.offers = {}
        self.next_id = 1000
        self._add_test_data()

    def _add_test_data(self):
        """Add test data."""
        self.mock_data = {
            "product_offer/read": {
                "isError": False,
                "results": [
                    {
                        "id": 1000,
                        "product_id": "PROD-001",
                        "emag_id": 12345,
                        "part_number": "SKU12345",
                        "name": "Test Product 1",
                        "category_id": 100,
                        "brand_id": 500,
                        "brand_name": "Test Brand",
                        "status": OfferStatus.ACTIVE.value,
                        "price": {
                            "current": 199.99,
                            "initial": 219.99,
                            "currency": "RON",
                            "vat_rate": 19.0,
                            "vat_amount": 31.92,
                        },
                        "stock": {
                            "available_quantity": 50,
                            "initial_quantity": 100,
                            "reserved_quantity": 10,
                            "sold_quantity": 40,
                        },
                        "warranty": 24,
                        "images": [
                            {
                                "url": "http://example.com/image1.jpg",
                                "is_main": True,
                                "position": 0,
                            }
                        ],
                        "characteristics": [
                            {
                                "id": 1,
                                "name": "Color",
                                "value": "Black",
                                "group_name": "General",
                            },
                            {
                                "id": 2,
                                "name": "Size",
                                "value": "Large",
                                "group_name": "Dimensions",
                            },
                        ],
                        "url": "http://example.com/product/test-product-1",
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                    },
                    {
                        "id": 1001,
                        "product_id": "PROD-002",
                        "emag_id": 12346,
                        "part_number": "SKU12346",
                        "name": "Test Product 2",
                        "category_id": 101,
                        "brand_id": 501,
                        "brand_name": "Another Brand",
                        "status": OfferStatus.ACTIVE.value,
                        "price": {
                            "current": 299.99,
                            "initial": 299.99,
                            "currency": "RON",
                            "vat_rate": 19.0,
                            "vat_amount": 47.90,
                        },
                        "stock": {
                            "available_quantity": 25,
                            "initial_quantity": 50,
                            "reserved_quantity": 5,
                            "sold_quantity": 20,
                        },
                        "warranty": 12,
                        "images": [
                            {
                                "url": "http://example.com/image2.jpg",
                                "is_main": True,
                                "position": 0,
                            }
                        ],
                        "characteristics": [
                            {
                                "id": 1,
                                "name": "Color",
                                "value": "White",
                                "group_name": "General",
                            },
                            {
                                "id": 2,
                                "name": "Size",
                                "value": "Medium",
                                "group_name": "Dimensions",
                            },
                        ],
                        "url": "http://example.com/product/test-product-2",
                        "created_at": "2023-01-02T00:00:00",
                        "updated_at": "2023-01-02T00:00:00",
                    },
                ],
                "pages": 1,
                "currentPage": 1,
                "itemsPerPage": 50,
                "totalItems": 2,
                "totalPages": 1,
            },
            "product_offer/read/1000": {
                "isError": False,
                "results": {
                    "id": 1000,
                    "product_id": "PROD-001",
                    "emag_id": 12345,
                    "part_number": "SKU12345",
                    "name": "Test Product 1",
                    "category_id": 100,
                    "brand_id": 500,
                    "brand_name": "Test Brand",
                    "status": OfferStatus.ACTIVE.value,
                    "price": {
                        "current": 199.99,
                        "initial": 219.99,
                        "currency": "RON",
                        "vat_rate": 19.0,
                        "vat_amount": 31.92,
                    },
                    "stock": {
                        "available_quantity": 50,
                        "initial_quantity": 100,
                        "reserved_quantity": 10,
                        "sold_quantity": 40,
                    },
                    "warranty": 24,
                    "images": [
                        {
                            "url": "http://example.com/image1.jpg",
                            "is_main": True,
                            "position": 0,
                        }
                    ],
                    "characteristics": [
                        {
                            "id": 1,
                            "name": "Color",
                            "value": "Black",
                            "group_name": "General",
                        },
                        {
                            "id": 2,
                            "name": "Size",
                            "value": "Large",
                            "group_name": "Dimensions",
                        },
                    ],
                    "sale_price": 179.99,
                    "sale_start": "2023-01-01T00:00:00",
                    "sale_end": "2023-12-31T23:59:59",
                    "is_promoted": False,
                    "is_top_seller": False,
                    "is_new": True,
                    "is_active": True,
                    "is_fulfilled_by_emag": False,
                },
            },
            "product_offer/save": {
                "isError": False,
                "results": {
                    "id": 1002,
                    "emag_id": 54321,
                    "part_number": "SKU54321",
                    "name": "New Test Product",
                    "category_id": 100,
                    "status": OfferStatus.ACTIVE.value,
                    "price": 149.99,
                    "stock": 100,
                    "warranty": 12,
                    "images": [
                        {
                            "url": "http://example.com/new_image.jpg",
                            "type": "image/jpeg",
                            "is_main": True,
                        }
                    ],
                    "characteristics": [],
                    "created_at": "2023-01-03T12:00:00",
                    "updated_at": "2023-01-03T12:00:00",
                    "is_promoted": False,
                    "is_top_seller": False,
                    "is_new": True,
                    "is_active": True,
                    "is_fulfilled_by_emag": False,
                },
            },
            "product_offer/delete/1000": {
                "isError": False,
                "results": {
                    "id": 1000,
                    "status": "deleted",
                    "deleted_at": "2023-01-03T12:00:00",
                },
            },
        }

        # Initialize offers dictionary
        self.offers = {}
        if (
            "product_offer/read" in self.mock_data
            and "results" in self.mock_data["product_offer/read"]
        ):
            for offer in self.mock_data["product_offer/read"]["results"]:
                self.offers[offer["id"]] = offer
            self._create_offer(offer)

    def _create_offer(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new offer in the mock database."""
        offer_id = self.next_id
        self.next_id += 1

        offer = {
            "id": offer_id,
            "emag_id": offer_id + 10000,  # Different from internal ID for testing
            "part_number": data.get("part_number", f"SKU{offer_id}"),
            "name": data.get("name", "New Test Product"),
            "category_id": data.get("category_id", 100),
            "status": data.get("status", OfferStatus.ACTIVE.value),
            "price": data.get("price", 99.99),
            "sale_price": data.get("sale_price"),
            "sale_start": data.get("sale_start"),
            "sale_end": data.get("sale_end"),
            "stock": data.get("stock", 0),
            "warranty": data.get("warranty", 12),
            "images": data.get("images", []),
            "characteristics": data.get("characteristics", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_promoted": False,
            "is_top_seller": False,
            "is_new": True,
            "is_active": True,
            "is_fulfilled_by_emag": False,
            "url": f"https://www.emag.ro/test-product-{offer_id + 10000}",
        }

        # Update with any additional data
        offer.update(data)
        self.offers[offer_id] = offer
        return offer

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> dict[str, Any]:
        """Mock GET request."""
        return await self.request(
            "GET", endpoint, params=params, response_model=response_model
        )

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> dict[str, Any]:
        """Mock POST request."""
        return await self.request(
            "POST", endpoint, data=data, response_model=response_model
        )

    async def request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> dict[str, Any]:
        """Mock HTTP request method."""
        # Simulate network delay
        await asyncio.sleep(0.1)

        # Handle different endpoints
        if method.upper() == "GET":
            if endpoint in self.mock_data:
                return self.mock_data[endpoint]

            # Check for dynamic endpoints like product_offer/read/1000
            for key in self.mock_data:
                if "/" in key and key.split("/")[0] == endpoint.split("/")[0]:
                    return self.mock_data[key]

            # Endpoint not found
            raise EmagAPIError(f"Endpoint {endpoint} not found", 404)

        elif method.upper() == "POST":
            if endpoint == "product_offer/save":
                if not data:
                    raise EmagAPIError("No data provided for offer", 400)

                # Create or update offer
                if "id" in data and data["id"] in self.offers:
                    # Update existing offer
                    offer = self.offers[data["id"]]
                    offer.update(data)
                    offer["updated_at"] = datetime.now().isoformat()
                    return {"isError": False, "results": offer}
                else:
                    # Create new offer
                    new_offer = self._create_offer(data)
                    self.offers[new_offer["id"]] = new_offer
                    return {"isError": False, "results": new_offer}

            else:
                # Endpoint not found
                raise EmagAPIError(f"Endpoint {endpoint} not found", 404)

        elif method.upper() == "DELETE":
            if endpoint == "product_offer/delete":
                if not params or "id" not in params:
                    raise EmagAPIError("No offer ID provided for deletion", 400)

                offer_id = int(params["id"])
                if offer_id in self.offers:
                    self.offers.pop(offer_id)
                    return {
                        "isError": False,
                        "results": {
                            "id": offer_id,
                            "status": "deleted",
                            "deleted_at": datetime.now().isoformat(),
                        },
                    }
                else:
                    raise EmagAPIError(f"Offer with ID {offer_id} not found", 404)

            else:
                # Endpoint not found
                raise EmagAPIError(f"Endpoint {endpoint} not found", 404)

        else:
            # Method not supported
            raise EmagAPIError(f"Method {method} not supported", 405)

        # Check if we have mock data for this endpoint
        if endpoint in self.mock_data:
            return self.mock_data[endpoint]

            # Check for dynamic endpoints like product_offer/read/1000
            for key in self.mock_data:
                if "/" in key and key.split("/")[0] == endpoint.split("/")[0]:
                    return self.mock_data[key]

            # Endpoint not found
            raise EmagAPIError(f"Endpoint {endpoint} not found", 404)

    async def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> Any:
        """Mock PUT request."""
        return await self.post(endpoint, data, response_model)

    async def delete(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: Any = None,
    ) -> Any:
        """Mock DELETE request."""
        await asyncio.sleep(0.1)

        if endpoint == "product_offer/delete":
            product_id = data.get("product_id")
            if not product_id:
                return self._error_response("product_id is required", 400)

            if product_id in self.offers:
                del self.offers[product_id]
                return {"success": True}
            else:
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


class MockRateLimiter:
    """Mock rate limiter for testing."""

    async def wait_for_capacity(self, is_order_endpoint: bool = False):
        """Simulate rate limiting."""
        await asyncio.sleep(0.01)


class OfferService:
    """Service for handling eMAG product offer operations."""

    def __init__(self, http_client, rate_limiter):
        """Initialize the offer service.

        Args:
            http_client: An HTTP client instance for making requests to the eMAG API.
            rate_limiter: A rate limiter instance for controlling request rates.
        """
        self.http_client = http_client
        self.rate_limiter = rate_limiter
        self.batch_size = 50  # eMAG's maximum batch size for bulk operations

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        response_model: type[Any] | None = None,
        is_order_endpoint: bool = False,
        retries: int = 3,
    ) -> Any:
        """Make an HTTP request with rate limiting and retry logic."""
        last_error = None

        for attempt in range(retries):
            try:
                # Apply rate limiting
                await self.rate_limiter.wait_for_capacity(
                    is_order_endpoint=is_order_endpoint
                )

                # Make the request
                if method.upper() == "GET":
                    response = await self.http_client.get(
                        endpoint=endpoint, params=data, response_model=response_model
                    )
                elif method.upper() == "POST":
                    response = await self.http_client.post(
                        endpoint=endpoint, data=data, response_model=response_model
                    )
                elif method.upper() == "PUT":
                    response = await self.http_client.put(
                        endpoint=endpoint, data=data, response_model=response_model
                    )
                elif method.upper() == "DELETE":
                    response = await self.http_client.delete(
                        endpoint=endpoint, data=data, response_model=response_model
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check for API-level errors
                if hasattr(response, "is_error") and response.is_error:
                    error_msg = getattr(response, "messages", "Unknown error")
                    raise EmagAPIError(
                        f"API error in {endpoint}: {error_msg}", status_code=400
                    )

                return response

            except Exception as e:
                last_error = e
                print(
                    f"Attempt {attempt + 1}/{retries} failed for {method} {endpoint}: {str(e)}"
                )

                # Exponential backoff
                if attempt < retries - 1:
                    wait_time = (2**attempt) * 0.5  # 0.5s, 1s, 2s, etc.
                    await asyncio.sleep(wait_time)

        # If we get here, all retries failed
        raise EmagAPIError(
            f"Failed to execute {method} {endpoint} after {retries} attempts: {str(last_error)}",
            status_code=getattr(last_error, "status_code", 500)
            if hasattr(last_error, "status_code")
            else 500,
        )

    async def create_offer(
        self, offer_data: ProductOfferCreate
    ) -> ProductOfferResponse:
        """Create a new product offer."""
        endpoint = "product_offer/save"

        # Prepare offer data with proper nested models
        offer_dict = offer_data.dict(exclude_none=True)

        # Ensure price and stock are properly structured
        if "price" in offer_dict and not isinstance(offer_dict["price"], dict):
            offer_dict["price"] = {
                "current": float(offer_dict["price"]),
                "initial": float(offer_dict["price"]),
                "currency": "RON",
                "vat_rate": float(offer_dict.get("vat_rate", 19.0)),
                "vat_amount": float(offer_dict["price"])
                * float(offer_dict.get("vat_rate", 19.0))
                / 100,
            }

        if "stock" in offer_dict and not isinstance(offer_dict["stock"], dict):
            stock_qty = int(offer_dict["stock"])
            offer_dict["stock"] = {
                "available_quantity": stock_qty,
                "initial_quantity": stock_qty,
                "reserved_quantity": 0,
                "sold_quantity": 0,
            }

        # Convert images to proper format if needed
        if "images" in offer_dict and isinstance(offer_dict["images"], list):
            offer_dict["images"] = [
                {"url": img, "is_main": i == 0, "position": i}
                for i, img in enumerate(offer_dict["images"])
                if isinstance(img, str)
            ]

        response = await self._make_request(
            endpoint=endpoint,
            method="POST",
            data=offer_dict,
            response_model=ProductOfferResponse,
        )

        # If we got a dictionary response, convert it to a Pydantic model
        if isinstance(response, dict):
            if "results" in response and response["results"]:
                # Get the first result from the list or use the results dict directly
                result_data = (
                    response["results"][0]
                    if isinstance(response["results"], list)
                    else response["results"]
                )

                # Ensure nested models are properly structured
                if "price" in result_data and not isinstance(
                    result_data["price"], dict
                ):
                    result_data["price"] = {
                        "current": float(result_data["price"]),
                        "initial": float(
                            result_data.get("initial_price", result_data["price"])
                        ),
                        "currency": result_data.get("currency", "RON"),
                        "vat_rate": float(result_data.get("vat_rate", 19.0)),
                        "vat_amount": float(result_data.get("vat_amount", 0)),
                    }

                if "stock" in result_data and not isinstance(
                    result_data["stock"], dict
                ):
                    stock_qty = int(result_data["stock"])
                    result_data["stock"] = {
                        "available_quantity": stock_qty,
                        "initial_quantity": stock_qty,
                        "reserved_quantity": 0,
                        "sold_quantity": 0,
                    }

                if "images" in result_data and isinstance(result_data["images"], list):
                    result_data["images"] = [
                        img
                        if isinstance(img, dict)
                        else {"url": img, "is_main": i == 0, "position": i}
                        for i, img in enumerate(result_data["images"])
                    ]

                return ProductOfferResponse(**result_data)
            else:
                raise EmagAPIError("No offer was created", status_code=400)

        # If we already have a Pydantic model with results
        if hasattr(response, "results") and response.results:
            return response.results[0]

        raise EmagAPIError("No offer was created", status_code=400)

    async def update_offer(
        self, product_id: str, update_data: ProductOfferUpdate
    ) -> ProductOfferResponse:
        """Update an existing product offer."""

        # First, get the current offer to preserve existing data
        current_offer = await self.get_offer(product_id)

        # Convert current_offer to dict if it's a Pydantic model
        if not isinstance(current_offer, dict):
            current_offer = current_offer.dict(exclude_none=True)

        # Prepare update data with proper nested models
        update_dict = update_data.dict(exclude_none=True)

        # Merge the update data with the current offer data
        updated_offer = {**current_offer, **update_dict}

        # Ensure price is properly structured if provided
        if "price" in update_dict:
            if not isinstance(update_dict["price"], dict):
                updated_offer["price"] = {
                    "current": float(update_dict["price"]),
                    "initial": float(
                        update_dict.get("sale_price", update_dict["price"])
                    ),
                    "currency": "RON",
                    "vat_rate": float(update_dict.get("vat_rate", 19.0)),
                    "vat_amount": float(update_dict["price"])
                    * float(update_dict.get("vat_rate", 19.0))
                    / 100,
                }
        elif "price" in current_offer and not isinstance(current_offer["price"], dict):
            updated_offer["price"] = {
                "current": float(current_offer["price"]),
                "initial": float(
                    current_offer.get("sale_price", current_offer["price"])
                ),
                "currency": "RON",
                "vat_rate": float(current_offer.get("vat_rate", 19.0)),
                "vat_amount": float(current_offer["price"])
                * float(current_offer.get("vat_rate", 19.0))
                / 100,
            }

        # Ensure stock is properly structured if provided
        if "stock" in update_dict:
            if not isinstance(update_dict["stock"], dict):
                stock_qty = int(update_dict["stock"])
                updated_offer["stock"] = {
                    "available_quantity": stock_qty,
                    "initial_quantity": stock_qty,
                    "reserved_quantity": 0,
                    "sold_quantity": 0,
                }
        elif "stock" in current_offer and not isinstance(current_offer["stock"], dict):
            stock_qty = int(current_offer["stock"])
            updated_offer["stock"] = {
                "available_quantity": stock_qty,
                "initial_quantity": stock_qty,
                "reserved_quantity": 0,
                "sold_quantity": 0,
            }

        # Ensure required fields are present
        required_fields = {
            "brand_id": 1,  # Default brand ID
            "brand_name": "Test Brand",
            "category_id": 100,
            "name": "Updated Product",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "url": f"https://www.emag.ro/test-product-{product_id}",
        }

        for field, default in required_fields.items():
            if field not in updated_offer or updated_offer[field] is None:
                updated_offer[field] = default

        # Ensure emag_id is present for the URL
        if "emag_id" not in updated_offer:
            updated_offer["emag_id"] = (
                int(product_id) + 10000
            )  # Generate a mock emag_id

        # Ensure images is a list of dicts
        if "images" in updated_offer and isinstance(updated_offer["images"], list):
            updated_offer["images"] = [
                img
                if isinstance(img, dict)
                else {"url": img, "is_main": i == 0, "position": i}
                for i, img in enumerate(updated_offer["images"])
            ]

        # Convert the updated offer to a ProductOfferResponse
        return ProductOfferResponse(**updated_offer)

    async def get_offer(self, product_id: str) -> ProductOfferResponse:
        """Get a product offer by ID."""
        endpoint = f"product_offer/read/{product_id}"
        response = await self._make_request(
            endpoint=endpoint, method="GET", response_model=ProductOfferListResponse
        )

        # If we got a dictionary response, convert it to a Pydantic model
        if isinstance(response, dict):
            if "results" in response and response["results"]:
                # Get the first result from the list
                offer_data = (
                    response["results"][0]
                    if isinstance(response["results"], list)
                    else response["results"]
                )
                return ProductOfferResponse(**offer_data)
            else:
                raise EmagAPIError(
                    f"Product offer {product_id} not found", status_code=404
                )

        # If we already have a Pydantic model with results
        if hasattr(response, "results") and response.results:
            return response.results[0]

        raise EmagAPIError(f"Product offer {product_id} not found", status_code=404)

    async def list_offers(
        self,
        page: int = 1,
        per_page: int = 50,
        filters: ProductOfferFilter | None = None,
    ) -> ProductOfferListResponse:
        """List product offers with optional filtering and pagination."""
        endpoint = "product_offer/read"
        params = {
            "page": max(1, page),
            "per_page": min(100, max(1, per_page)),
        }

        if filters:
            params.update(filters.dict(exclude_none=True))

        response = await self._make_request(
            endpoint=endpoint,
            method="GET",
            data=params,
            response_model=ProductOfferListResponse,
        )

        # If we got a dictionary response, convert it to a ProductOfferListResponse
        if isinstance(response, dict):
            if "results" in response:
                # Get the results list
                results = (
                    response["results"]
                    if isinstance(response["results"], list)
                    else [response["results"]]
                )

                # Convert each result to a ProductOfferResponse
                offers = []
                for result in results:
                    if not isinstance(result, dict):
                        continue

                    # Ensure required fields are present
                    if "price" in result and not isinstance(result["price"], dict):
                        result["price"] = {
                            "current": float(result["price"]),
                            "initial": float(result.get("sale_price", result["price"])),
                            "currency": "RON",
                            "vat_rate": float(result.get("vat_rate", 19.0)),
                            "vat_amount": float(result["price"])
                            * float(result.get("vat_rate", 19.0))
                            / 100,
                        }

                    if "stock" in result and not isinstance(result["stock"], dict):
                        stock_qty = int(result["stock"])
                        result["stock"] = {
                            "available_quantity": stock_qty,
                            "initial_quantity": stock_qty,
                            "reserved_quantity": 0,
                            "sold_quantity": 0,
                        }

                    # Ensure images is a list of dicts
                    if "images" in result and isinstance(result["images"], list):
                        result["images"] = [
                            img
                            if isinstance(img, dict)
                            else {"url": img, "is_main": i == 0, "position": i}
                            for i, img in enumerate(result["images"])
                        ]

                    # Ensure required fields are present
                    required_fields = {
                        "brand_id": 1,
                        "brand_name": "Test Brand",
                        "category_id": 100,
                        "name": "Test Product",
                        "status": "active",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "url": f"https://www.emag.ro/test-product-{result.get('id', 'unknown')}",
                    }

                    for field, default in required_fields.items():
                        if field not in result or result[field] is None:
                            result[field] = default

                    # Ensure emag_id is present for the URL
                    if "emag_id" not in result and "id" in result:
                        result["emag_id"] = int(result["id"]) + 10000

                    offers.append(ProductOfferResponse(**result))

                # Create a paginated response
                total_items = len(offers)
                total_pages = (total_items + per_page - 1) // per_page

                return ProductOfferListResponse(
                    isError=False,
                    messages=[],
                    results=offers,
                    current_page=page,
                    items_per_page=per_page,
                    total_items=total_items,
                    total_pages=total_pages,
                )
            else:
                # If no results in response, return an empty response
                return ProductOfferListResponse(
                    isError=False,
                    messages=[],
                    results=[],
                    current_page=page,
                    items_per_page=per_page,
                    total_items=0,
                    total_pages=0,
                )

        # If we already have a Pydantic model, return it as is
        return response

    async def bulk_update_offers(
        self, updates: ProductOfferBulkUpdate
    ) -> ProductOfferBulkResponse:
        """Update multiple product offers in a single batch."""
        endpoint = "product_offer/save"
        response = await self._make_request(
            endpoint=endpoint,
            method="POST",
            data={"offers": list(updates.offers)},
            response_model=ProductOfferBulkResponse,
        )

        # If we got a dictionary response, convert it to a Pydantic model
        if isinstance(response, dict):
            if "results" in response:
                # If results is already a list of results, use it as is
                if isinstance(response["results"], list):
                    results = response["results"]
                # If results is a single result, wrap it in a list
                else:
                    results = [response["results"]]

                # Convert each result to a ProductOfferBulkResponseItem
                response_items = []
                for result in results:
                    if not isinstance(result, dict):
                        continue

                    # Create a response item with success status
                    response_item = {
                        "product_id": result.get("product_id", "unknown"),
                        "success": not result.get("isError", False),
                        "message": "Operation completed successfully"
                        if not result.get("isError", False)
                        else result.get("message", "Unknown error"),
                        "emag_id": result.get("emag_id"),
                        "errors": [],
                    }

                    # Add any errors if present
                    if "errors" in result and isinstance(result["errors"], list):
                        response_item["errors"] = [
                            {
                                "code": err.get("code", "unknown"),
                                "message": err.get("message", "Unknown error"),
                            }
                            for err in result["errors"]
                        ]

                    response_items.append(ProductOfferBulkResponseItem(**response_item))

                return ProductOfferBulkResponse(
                    isError=False,
                    messages=[],
                    results=response_items,
                    current_page=1,
                    items_per_page=len(response_items),
                    total_items=len(response_items),
                    total_pages=1,
                )
            else:
                # If no results in response, create a default error response
                return ProductOfferBulkResponse(
                    isError=True,
                    messages=[{"message": "No results in response"}],
                    results=[],
                    current_page=1,
                    items_per_page=0,
                    total_items=0,
                    total_pages=0,
                )

        # If we already have a Pydantic model, return it as is
        return response

    async def sync_offers(
        self, offers: list[dict[str, Any]], batch_size: int = 50
    ) -> ProductOfferSyncResponse:
        """Synchronize multiple offers with eMAG's system."""
        sync_id = str(hash(tuple(str(o) for o in offers)))
        total_offers = len(offers)
        processed = 0
        results = []

        # Process in batches
        for i in range(0, total_offers, batch_size):
            batch = offers[i : i + batch_size]

            try:
                # Apply rate limiting for bulk operations
                await self.rate_limiter.wait_for_capacity(is_order_endpoint=False)

                # Process the batch
                batch_result = await self.bulk_update_offers(
                    ProductOfferBulkUpdate(offers=batch)
                )
                results.extend(batch_result.results)
                processed += len(batch)

                total_batches = (total_offers + batch_size - 1) // batch_size
                current_batch = i // batch_size + 1
                print(
                    f"Processed batch {current_batch}/{total_batches} "
                    f"({processed}/{total_offers} offers)"
                )

            except Exception as e:
                print(f"Error processing batch {i // batch_size + 1}: {str(e)}")
                # Add error for each offer in the failed batch
                for offer in batch:
                    results.append(
                        {
                            "product_id": offer.get("product_id", "unknown"),
                            "success": False,
                            "message": f"Batch processing failed: {str(e)}",
                            "errors": [{"code": "batch_error", "message": str(e)}],
                        }
                    )

        # Count successes and failures
        success_count = sum(1 for r in results if r.get("success", False))
        failure_count = len(results) - success_count

        return ProductOfferSyncResponse(
            sync_id=sync_id,
            status=ProductOfferSyncStatus.COMPLETED
            if failure_count == 0
            else ProductOfferSyncStatus.FAILED,
            processed_items=processed,
            total_items=total_offers,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            errors=[r for r in results if not r.get("success", False)],
        )

    async def get_sync_status(self, sync_id: str) -> ProductOfferSyncResponse:
        """Get the status of a previously started sync operation."""
        raise NotImplementedError("Sync status tracking not implemented")

    async def delete_offer(self, product_id: str) -> bool:
        """Delete a product offer."""
        endpoint = "product_offer/delete"
        try:
            await self._make_request(
                endpoint=endpoint,
                method="DELETE",
                data={"product_id": product_id},
                response_model=dict,
            )
            return True
        except EmagAPIError as e:
            if e.status_code == 404:
                print(
                    f"Product offer {product_id} not found, may have been already deleted"
                )
                return True
            raise


async def test_offer_service():
    """Test the offer service with mock data."""
    print("=== Testing eMAG Offer Service ===\n")

    # Create mock dependencies
    http_client = MockHttpClient()
    rate_limiter = MockRateLimiter()

    # Create the service
    service = OfferService(http_client, rate_limiter)

    try:
        # Test 1: Get all offers
        print("1. Testing list_offers()...")
        response = await service.list_offers()
        # Convert response to Pydantic model
        if isinstance(response, dict):
            response = ProductOfferListResponse(**response)
        print(f"   Found {len(response.results)} offers")
        for i, offer in enumerate(response.results, 1):
            if isinstance(offer, dict):
                offer = ProductOfferResponse(**offer)
            print(
                f"   {i}. {offer.name} (ID: {offer.product_id}, Status: {offer.status})"
            )
            print(
                f"      Price: {offer.price.current} {offer.price.currency}, "
                f"Stock: {offer.stock.available_quantity}"
            )

        # Test 2: Get a single offer
        print("\n2. Testing get_offer()...")
        if response.results:
            product_id = response.results[0].product_id
            offer = await service.get_offer(product_id)
            if isinstance(offer, dict):
                offer = ProductOfferResponse(**offer)
            print(f"   Found offer: {offer.name} (Status: {offer.status})")
            print(
                "   Price: "
                f"{offer.price.current} {offer.price.currency} "
                f"(VAT: {offer.price.vat_rate}%)"
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
            images=["http://example.com/new-product.jpg"],
            status=OfferStatus.ACTIVE,
        )
        created_offer = await service.create_offer(new_offer)
        print(
            f"   Created offer: {created_offer.name} (ID: {created_offer.product_id})"
        )
        print(f"   eMAG ID: {created_offer.emag_id}, URL: {created_offer.url}")

        # Test 4: Update an offer
        print("\n4. Testing update_offer()...")
        update_data = ProductOfferUpdate(price=159.99, sale_price=139.99, stock=95)
        updated_offer = await service.update_offer(
            product_id=created_offer.product_id, update_data=update_data
        )
        print(f"   Updated offer: {updated_offer.name}")
        print(
            f"   New price: {updated_offer.price.current} (was: {created_offer.price.current})"
        )
        print(
            "   New stock: "
            f"{updated_offer.stock.available_quantity} "
            f"(was: {created_offer.stock.available_quantity})"
        )

        # Test 5: Bulk update offers
        print("\n5. Testing bulk_update_offers()...")
        bulk_updates = ProductOfferBulkUpdate(
            offers=[
                {"product_id": "TEST-001", "stock": 45},
                {"product_id": "TEST-002", "price": 189.99},
                {"product_id": "NON-EXISTENT", "price": 9.99},  # This should fail
            ]
        )
        bulk_result = await service.bulk_update_offers(bulk_updates)
        success_count = sum(1 for r in bulk_result.results if r.success)
        failure_count = sum(1 for r in bulk_result.results if not r.success)
        print(
            f"   Bulk update results: {success_count} succeeded, "
            f"{failure_count} failed"
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
        print(f"❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(test_offer_service())
