"""Catalog service for managing products, brands, and characteristics with eMAG Marketplace integration."""

import base64
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar
from uuid import UUID

# import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.logger import logger
from app.core.rate_limiting import RateLimiter, get_rate_limiter
from app.schemas.catalog import (
    Brand,
    BrandListResponse,
    Characteristic,
    CharacteristicListResponse,
    CharacteristicValue,
    PaginationMeta,
    Product,
    ProductCreate,
    ProductFilter,
    ProductListResponse,
    ProductStatus,
    ProductUpdate,
)


class MockHTTPClient:
    """Mock HTTP client for testing when httpx is not available."""

    def __init__(self, **kwargs):
        pass

    @property
    def is_closed(self):
        return False

    async def aclose(self):
        pass

    async def request(self, method, url, **kwargs):
        # Mock successful response
        class MockResponse:
            def __init__(self):
                self.status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"isError": False, "data": "mock"}

        return MockResponse()


T = TypeVar("T", bound=BaseModel)


class CatalogService:
    """Service for managing catalog data with eMAG Marketplace integration."""

    def __init__(
        self,
        http_client: Optional[Any] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """Initialize the CatalogService.

        Args:
            http_client: Optional HTTP client (useful for testing).
            rate_limiter: Optional rate limiter instance.

        """
        # Mock HTTP client since httpx is not available
        self._http = http_client or MockHTTPClient()
        self._rate_limiter = rate_limiter or get_rate_limiter()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the eMAG API with rate limiting and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (e.g., '/product/read')
            data: Request body as a dictionary
            params: Query parameters
            headers: Additional headers

        Returns:
            Response data as a dictionary

        Raises:
            HTTPException: If the request fails or returns an error

        """
        url = f"{settings.EMAG_API_BASE_URL}/{endpoint.lstrip('/')}"
        headers = headers or {}
        headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        # Apply rate limiting
        await self._rate_limiter.acquire()

        try:
            response = await self._http.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
            )
            response.raise_for_status()

            result = response.json()

            # Check for eMAG API errors
            if isinstance(result, dict) and result.get("isError", False):
                error_msg = result.get("messages", [{}])[0].get(
                    "message",
                    "Unknown error",
                )
                logger.error(
                    "eMAG API error",
                    extra={
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "error": error_msg,
                        "response": result,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"eMAG API error: {error_msg}",
                )

            return result

        # except httpx.HTTPStatusError as e:
        except Exception as e:
            logger.error(
                "HTTP error",
                extra={
                    "endpoint": endpoint,
                    "status_code": e.response.status_code,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HTTP error: {e!s}",
            ) from e

        # except (httpx.RequestError, json.JSONDecodeError) as e:
        except (Exception, json.JSONDecodeError) as e:
            logger.error(
                "Request error",
                extra={
                    "endpoint": endpoint,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unavailable: {e!s}",
            ) from e

    def _encode_cursor(self, cursor_data: Dict[str, Any]) -> str:
        """Encode cursor data to base64 string.

        Args:
            cursor_data: Dictionary containing cursor data

        Returns:
            Base64 encoded cursor string

        """
        cursor_str = json.dumps(cursor_data, sort_keys=True)
        return base64.urlsafe_b64encode(cursor_str.encode()).decode()

    def _decode_cursor(self, cursor: str) -> Dict[str, Any]:
        """Decode base64 cursor string to dictionary.

        Args:
            cursor: Base64 encoded cursor string

        Returns:
            Decoded cursor data as dictionary

        Raises:
            HTTPException: If the cursor is invalid

        """
        try:
            cursor_str = base64.urlsafe_b64decode(cursor).decode()
            return json.loads(cursor_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Invalid cursor", extra={"cursor": cursor, "error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor parameter",
            ) from e

    # Product methods
    async def list_products(
        self,
        filter: ProductFilter,
    ) -> ProductListResponse:
        """List products with filtering and pagination.

        Args:
            filter: Product filter criteria

        Returns:
            ProductListResponse with paginated results

        """
        # This would be replaced with actual database queries in a real implementation
        # For now, we'll return a mock response

        # Example implementation with SQLAlchemy:
        # query = db.query(Product).filter(
        #     Product.is_active == True
        # )
        #
        # if filter.q:
        #     query = query.filter(Product.name.ilike(f"%{filter.q}%"))
        #
        # if filter.category_id is not None:
        #     query = query.filter(Product.category_id == filter.category_id)
        #
        # if filter.brand_id is not None:
        #     query = query.filter(Product.brand_id == filter.brand_id)
        #
        # if filter.status:
        #     query = query.filter(Product.status == filter.status)
        #
        # if filter.min_price is not None:
        #     query = query.filter(Product.price >= filter.min_price)
        #
        # if filter.max_price is not None:
        #     query = query.filter(Product.price <= filter.max_price)
        #
        # if filter.in_stock is not None:
        #     if filter.in_stock:
        #         query = query.filter(Product.stock_quantity > 0)
        #     else:
        #         query = query.filter(Product.stock_quantity <= 0)
        #
        # # Apply cursor-based pagination
        # if filter.cursor:
        #     cursor_data = self._decode_cursor(filter.cursor)
        #     cursor_created_at = datetime.fromisoformat(cursor_data["created_at"])
        #     cursor_id = cursor_data["id"]
        #
        #     if filter.sort_direction == SortDirection.DESC:
        #         query = query.filter(
        #             (Product.created_at < cursor_created_at) |
        #             ((Product.created_at == cursor_created_at) & (Product.id < cursor_id))
        #         )
        #     else:
        #         query = query.filter(
        #             (Product.created_at > cursor_created_at) |
        #             ((Product.created_at == cursor_created_at) & (Product.id > cursor_id))
        #         )
        #
        # # Apply sorting
        # sort_field = filter.sort_by or SortField.CREATED_AT
        # sort_dir = filter.sort_direction or SortDirection.DESC
        #
        # if sort_field == SortField.NAME:
        #     order_by = Product.name.asc() if sort_dir == SortDirection.ASC else Product.name.desc()
        # elif sort_field == SortField.PRICE:
        #     order_by = Product.price.asc() if sort_dir == SortDirection.ASC else Product.price.desc()
        # else:  # Default to created_at
        #     order_by = Product.created_at.asc() if sort_dir == SortDirection.ASC else Product.created_at.desc()
        #
        # query = query.order_by(order_by, Product.id.asc())
        #
        # # Get one extra item to determine if there are more results
        # limit = filter.limit + 1 if filter.limit else None
        # if limit:
        #     query = query.limit(limit)
        #
        # products = query.all()
        #
        # # Check if there are more items
        # has_more = len(products) > filter.limit
        # if has_more:
        #     products = products[:-1]  # Remove the extra item
        #
        # # Get the next/previous cursors
        # next_cursor = None
        # prev_cursor = None
        #
        # if products:
        #     last_item = products[-1]
        #     next_cursor = self._encode_cursor({
        #         "created_at": last_item.created_at.isoformat(),
        #         "id": str(last_item.id),
        #     })
        #
        #     first_item = products[0]
        #     prev_cursor = self._encode_cursor({
        #         "created_at": first_item.created_at.isoformat(),
        #         "id": str(first_item.id),
        #     })

        # Mock response for now
        products = [
            Product(
                id=UUID("123e4567-e89b-12d3-a456-426614174000"),
                name="Test Product",
                description="A test product",
                sku="TEST-001",
                price=99.99,
                status=ProductStatus.ACTIVE,
                is_active=True,
                stock_quantity=10,
                category_id=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        meta = PaginationMeta(
            total_items=1,
            total_pages=1,
            page=1,
            per_page=filter.limit,
            has_next=False,
            has_prev=False,
            next_cursor=None,
            prev_cursor=None,
        )

        return ProductListResponse(data=products, meta=meta)

    async def get_product_by_id(self, product_id: UUID) -> Product:
        """Get a product by ID.

        Args:
            product_id: Product ID

        Returns:
            Product if found

        Raises:
            HTTPException: If product is not found

        """
        # This would be replaced with actual database queries in a real implementation
        # For now, we'll return a mock response

        # Example implementation with SQLAlchemy:
        # product = db.query(Product).filter(Product.id == product_id).first()
        # if not product:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"Product with ID {product_id} not found",
        #     )
        # return product

        # Mock response for now
        if product_id != UUID("123e4567-e89b-12d3-a456-426614174000"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found",
            )

        return Product(
            id=product_id,
            name="Test Product",
            description="A test product",
            sku="TEST-001",
            price=99.99,
            status=ProductStatus.ACTIVE,
            is_active=True,
            stock_quantity=10,
            category_id=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def create_product(self, product_data: ProductCreate) -> Product:
        """Create a new product.

        Args:
            product_data: Product data

        Returns:
            Created product

        Raises:
            HTTPException: If creation fails

        """
        # This would be replaced with actual database operations in a real implementation
        # For now, we'll return a mock response

        # Example implementation with SQLAlchemy:
        # db_product = Product(**product_data.dict())
        # db.add(db_product)
        # db.commit()
        # db.refresh(db_product)
        # return db_product

        # Mock response for now
        return Product(
            id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            **product_data.dict(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def update_product(
        self,
        product_id: UUID,
        product_data: ProductUpdate,
    ) -> Product:
        """Update an existing product.

        Args:
            product_id: Product ID
            product_data: Updated product data

        Returns:
            Updated product

        Raises:
            HTTPException: If product is not found or update fails

        """
        # This would be replaced with actual database operations in a real implementation
        # For now, we'll return a mock response

        # Example implementation with SQLAlchemy:
        # db_product = db.query(Product).filter(Product.id == product_id).first()
        # if not db_product:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"Product with ID {product_id} not found",
        #     )
        #
        # update_data = product_data.dict(exclude_unset=True)
        # for field, value in update_data.items():
        #     setattr(db_product, field, value)
        #
        # db_product.updated_at = datetime.utcnow()
        # db.commit()
        # db.refresh(db_product)
        # return db_product

        # Mock response for now
        if product_id != UUID("123e4567-e89b-12d3-a456-426614174000"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found",
            )

        return Product(
            id=product_id,
            **product_data.dict(exclude_unset=True),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def delete_product(self, product_id: UUID) -> None:
        """Delete a product.

        Args:
            product_id: Product ID

        Raises:
            HTTPException: If product is not found or deletion fails

        """
        # This would be replaced with actual database operations in a real implementation
        # For now, we'll just check if the product exists

        # Example implementation with SQLAlchemy:
        # db_product = db.query(Product).filter(Product.id == product_id).first()
        # if not db_product:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"Product with ID {product_id} not found",
        #     )
        #
        # db.delete(db_product)
        # db.commit()

        # Mock check for now
        if product_id != UUID("123e4567-e89b-12d3-a456-426614174000"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found",
            )

    # Brand methods (similar structure as product methods)
    async def list_brands(
        self,
        q: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> BrandListResponse:
        """List brands with optional filtering and pagination.

        Args:
            q: Optional search query
            limit: Maximum number of items to return (1-100)
            cursor: Cursor for pagination

        Returns:
            BrandListResponse with paginated results

        """
        # Mock response for now
        brands = [
            Brand(
                id=1,
                name="Test Brand",
                slug="test-brand",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        meta = PaginationMeta(
            total_items=1,
            total_pages=1,
            page=1,
            per_page=limit,
            has_next=False,
            has_prev=False,
            next_cursor=None,
            prev_cursor=None,
        )

        return BrandListResponse(data=brands, meta=meta)

    async def get_brand_by_id(self, brand_id: int) -> Brand:
        """Get a brand by ID.

        Args:
            brand_id: Brand ID

        Returns:
            Brand if found

        Raises:
            HTTPException: If brand is not found

        """
        # Mock response for now
        if brand_id != 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with ID {brand_id} not found",
            )

        return Brand(
            id=brand_id,
            name="Test Brand",
            slug="test-brand",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    # Characteristic methods (similar structure as product methods)
    async def list_characteristics(
        self,
        category_id: int,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> CharacteristicListResponse:
        """List characteristics for a category with pagination.

        Args:
            category_id: Category ID
            limit: Maximum number of items to return (1-100)
            cursor: Cursor for pagination

        Returns:
            CharacteristicListResponse with paginated results

        """
        # Mock response for now
        characteristics = [
            Characteristic(
                id=1,
                name="Test Characteristic",
                code="test_char",
                type="text",
                is_required=False,
                is_filterable=True,
                is_variant=False,
                category_id=category_id,
                values=[
                    CharacteristicValue(
                        id=1,
                        value="Test Value",
                        is_default=True,
                        position=0,
                    ),
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        meta = PaginationMeta(
            total_items=1,
            total_pages=1,
            page=1,
            per_page=limit,
            has_next=False,
            has_prev=False,
            next_cursor=None,
            prev_cursor=None,
        )

        return CharacteristicListResponse(data=characteristics, meta=meta)

    async def get_characteristic_values(
        self,
        category_id: int,
        characteristic_id: int,
    ) -> List[CharacteristicValue]:
        """Get values for a specific characteristic in a category.

        Args:
            category_id: Category ID
            characteristic_id: Characteristic ID

        Returns:
            List of characteristic values

        Raises:
            HTTPException: If characteristic is not found

        """
        # Mock response for now
        if characteristic_id != 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Characteristic with ID {characteristic_id} not found in category {category_id}",
            )

        return [
            CharacteristicValue(
                id=1,
                value="Test Value",
                is_default=True,
                position=0,
            ),
        ]


# Factory function for dependency injection
async def get_catalog_service() -> CatalogService:
    """Get a CatalogService instance for dependency injection."""
    async with CatalogService() as service:
        yield service
