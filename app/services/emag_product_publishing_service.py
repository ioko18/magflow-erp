"""
eMAG Product Publishing Service - v4.4.9

Handles publishing new products and offers to eMAG marketplace.
Supports draft products, complete products, and offer attachments.
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
import time

from app.core.logging import get_logger
from app.core.exceptions import ServiceError
from app.services.emag_api_client import EmagApiClient, EmagApiError
from app.config.emag_config import get_emag_config
from app.core.emag_validator import validate_emag_response
from app.core.emag_monitoring import get_monitor

logger = get_logger(__name__)
monitor = get_monitor()


class EmagProductPublishingService:
    """
    Service for publishing products to eMAG marketplace.
    
    Supports:
    - Draft product creation (minimal fields)
    - Complete product creation (full documentation)
    - Offer attachment to existing products
    - Product updates (if ownership = 1)
    """

    def __init__(self, account_type: str = "main"):
        """
        Initialize Product Publishing Service.
        
        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
        """
        self.account_type = account_type
        self.config = get_emag_config(account_type)
        self.client = EmagApiClient(
            username=self.config.api_username,
            password=self.config.api_password,
            base_url=self.config.base_url,
            timeout=self.config.api_timeout,
            max_retries=self.config.max_retries
        )

        logger.info(
            "Initialized EmagProductPublishingService for %s account",
            account_type
        )

    async def initialize(self):
        """Initialize the service."""
        await self.client.start()

    async def close(self):
        """Close the service and cleanup resources."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def create_draft_product(
        self,
        product_id: int,
        name: str,
        brand: str,
        part_number: str,
        category_id: Optional[int] = None,
        ean: Optional[List[str]] = None,
        source_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a draft product with minimal information.
        
        Draft products are not sent to eMAG validation until complete.
        
        Args:
            product_id: Seller internal product ID
            name: Product name
            brand: Brand name
            part_number: Manufacturer part number
            category_id: Optional eMAG category ID
            ean: Optional list of EAN codes
            source_language: Optional source language code
            
        Returns:
            API response dictionary
            
        Raises:
            ServiceError: If creation fails
        """
        payload = {
            "id": product_id,
            "name": name,
            "brand": brand,
            "part_number": part_number
        }

        if category_id:
            payload["category_id"] = category_id

        if ean:
            payload["ean"] = ean

        if source_language:
            payload["source_language"] = source_language

        try:
            logger.info(
                "Creating draft product %d: %s",
                product_id,
                name
            )

            start_time = time.time()
            response = await self.client._request("POST", "product_offer/save", json=payload)
            response_time_ms = (time.time() - start_time) * 1000

            # Record monitoring metrics
            monitor.record_request(
                endpoint="product_offer/save",
                method="POST",
                status_code=200,
                response_time_ms=response_time_ms,
                account_type=self.account_type,
                success=not response.get('isError', False),
                error_message=str(response.get('messages')) if response.get('isError') else None,
                error_code=response.get('error_code')
            )

            validate_emag_response(response, "product_offer/save", "publish_product")

            logger.info("Draft product %d created successfully", product_id)
            return response

        except EmagApiError as e:
            logger.error("Failed to create draft product %d: %s", product_id, str(e))
            raise ServiceError(f"Draft product creation failed: {str(e)}")

    async def create_complete_product(
        self,
        product_id: int,
        category_id: int,
        name: str,
        part_number: str,
        brand: str,
        description: str,
        images: List[Dict[str, Any]],
        characteristics: List[Dict[str, Any]],
        sale_price: Decimal,
        vat_id: int,
        stock: List[Dict[str, int]],
        handling_time: List[Dict[str, int]],
        ean: Optional[List[str]] = None,
        warranty: Optional[int] = None,
        url: Optional[str] = None,
        source_language: Optional[str] = None,
        family: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        min_sale_price: Optional[Decimal] = None,
        max_sale_price: Optional[Decimal] = None,
        recommended_price: Optional[Decimal] = None,
        currency_type: Optional[str] = None,
        force_images_download: bool = False,
        images_overwrite: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a complete product with full documentation and offer.
        
        This will be sent to eMAG for validation.
        
        Args:
            product_id: Seller internal product ID
            category_id: eMAG category ID
            name: Product name
            part_number: Manufacturer part number
            brand: Brand name
            description: Product description (HTML allowed)
            images: List of image objects
            characteristics: List of characteristic objects
            sale_price: Sale price without VAT
            vat_id: VAT rate ID
            stock: List of stock objects per warehouse
            handling_time: List of handling time objects per warehouse
            ean: Optional list of EAN codes
            warranty: Optional warranty in months
            url: Optional product URL on seller website
            source_language: Optional source language
            family: Optional family object
            attachments: Optional list of attachments
            min_sale_price: Minimum sale price (required on first save)
            max_sale_price: Maximum sale price (required on first save)
            recommended_price: Optional recommended retail price
            currency_type: Optional currency (EUR or PLN)
            force_images_download: Force image redownload
            images_overwrite: Image overwrite mode
            
        Returns:
            API response dictionary
            
        Raises:
            ServiceError: If creation fails
        """
        payload = {
            "id": product_id,
            "category_id": category_id,
            "name": name,
            "part_number": part_number,
            "brand": brand,
            "description": description,
            "images": images,
            "characteristics": characteristics,
            "status": 1,  # Active
            "sale_price": float(sale_price),
            "vat_id": vat_id,
            "stock": stock,
            "handling_time": handling_time
        }

        # Add optional product fields
        if ean:
            payload["ean"] = ean

        if warranty is not None:
            payload["warranty"] = warranty

        if url:
            payload["url"] = url

        if source_language:
            payload["source_language"] = source_language

        if family:
            payload["family"] = family

        if attachments:
            payload["attachments"] = attachments

        if force_images_download:
            payload["force_images_download"] = 1

        if images_overwrite is not None:
            payload["images_overwrite"] = images_overwrite

        # Add optional offer fields
        if min_sale_price is not None:
            payload["min_sale_price"] = float(min_sale_price)

        if max_sale_price is not None:
            payload["max_sale_price"] = float(max_sale_price)

        if recommended_price is not None:
            payload["recommended_price"] = float(recommended_price)

        if currency_type:
            payload["currency_type"] = currency_type

        try:
            logger.info(
                "Creating complete product %d: %s",
                product_id,
                name
            )

            response = await self.client._request("POST", "product_offer/save", json=payload)

            validate_emag_response(response, "product_offer/save", "publish_product")

            logger.info("Complete product %d created successfully", product_id)
            return response

        except EmagApiError as e:
            logger.error("Failed to create complete product %d: %s", product_id, str(e))
            raise ServiceError(f"Complete product creation failed: {str(e)}")

    async def attach_offer_to_existing_product(
        self,
        product_id: int,
        part_number_key: str,
        sale_price: Decimal,
        vat_id: int,
        stock: List[Dict[str, int]],
        handling_time: List[Dict[str, int]],
        status: int = 1,
        min_sale_price: Optional[Decimal] = None,
        max_sale_price: Optional[Decimal] = None,
        recommended_price: Optional[Decimal] = None,
        warranty: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Attach an offer to an existing eMAG product using part_number_key.
        
        Use this when the product already exists on eMAG (created by eMAG or other sellers).
        
        Args:
            product_id: Seller internal product ID
            part_number_key: eMAG part number key (from product URL)
            sale_price: Sale price without VAT
            vat_id: VAT rate ID
            stock: List of stock objects per warehouse
            handling_time: List of handling time objects per warehouse
            status: Offer status (0=inactive, 1=active)
            min_sale_price: Optional minimum sale price
            max_sale_price: Optional maximum sale price
            recommended_price: Optional recommended retail price
            warranty: Optional warranty in months
            
        Returns:
            API response dictionary
            
        Raises:
            ServiceError: If attachment fails
        """
        payload = {
            "id": product_id,
            "part_number_key": part_number_key,
            "status": status,
            "sale_price": float(sale_price),
            "vat_id": vat_id,
            "stock": stock,
            "handling_time": handling_time
        }

        if min_sale_price is not None:
            payload["min_sale_price"] = float(min_sale_price)

        if max_sale_price is not None:
            payload["max_sale_price"] = float(max_sale_price)

        if recommended_price is not None:
            payload["recommended_price"] = float(recommended_price)

        if warranty is not None:
            payload["warranty"] = warranty

        try:
            logger.info(
                "Attaching offer %d to product %s",
                product_id,
                part_number_key
            )

            response = await self.client._request("POST", "product_offer/save", json=payload)

            validate_emag_response(response, "product_offer/save", "publish_product")

            logger.info("Offer %d attached successfully to %s", product_id, part_number_key)
            return response

        except EmagApiError as e:
            logger.error("Failed to attach offer %d: %s", product_id, str(e))
            raise ServiceError(f"Offer attachment failed: {str(e)}")

    async def attach_offer_by_ean(
        self,
        product_id: int,
        ean: List[str],
        sale_price: Decimal,
        vat_id: int,
        stock: List[Dict[str, int]],
        handling_time: List[Dict[str, int]],
        status: int = 1,
        min_sale_price: Optional[Decimal] = None,
        max_sale_price: Optional[Decimal] = None,
        recommended_price: Optional[Decimal] = None,
        warranty: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Attach an offer to an existing eMAG product using EAN.
        
        If the EAN matches an existing product, the offer is automatically attached.
        
        Args:
            product_id: Seller internal product ID
            ean: List of EAN codes
            sale_price: Sale price without VAT
            vat_id: VAT rate ID
            stock: List of stock objects per warehouse
            handling_time: List of handling time objects per warehouse
            status: Offer status (0=inactive, 1=active)
            min_sale_price: Optional minimum sale price
            max_sale_price: Optional maximum sale price
            recommended_price: Optional recommended retail price
            warranty: Optional warranty in months
            
        Returns:
            API response dictionary
            
        Raises:
            ServiceError: If attachment fails
        """
        payload = {
            "id": product_id,
            "ean": ean,
            "status": status,
            "sale_price": float(sale_price),
            "vat_id": vat_id,
            "stock": stock,
            "handling_time": handling_time
        }

        if min_sale_price is not None:
            payload["min_sale_price"] = float(min_sale_price)

        if max_sale_price is not None:
            payload["max_sale_price"] = float(max_sale_price)

        if recommended_price is not None:
            payload["recommended_price"] = float(recommended_price)

        if warranty is not None:
            payload["warranty"] = warranty

        try:
            logger.info(
                "Attaching offer %d by EAN: %s",
                product_id,
                ", ".join(ean)
            )

            response = await self.client._request("POST", "product_offer/save", json=payload)

            validate_emag_response(response, "product_offer/save", "publish_product")

            logger.info("Offer %d attached successfully by EAN", product_id)
            return response

        except EmagApiError as e:
            logger.error("Failed to attach offer %d by EAN: %s", product_id, str(e))
            raise ServiceError(f"Offer attachment by EAN failed: {str(e)}")

    async def update_product(
        self,
        product_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing product (requires ownership = 1).
        
        Args:
            product_id: Seller internal product ID
            updates: Dictionary of fields to update
            
        Returns:
            API response dictionary
            
        Raises:
            ServiceError: If update fails
        """
        payload = {"id": product_id, **updates}

        try:
            logger.info("Updating product %d", product_id)

            response = await self.client._request("POST", "product_offer/save", json=payload)

            validate_emag_response(response, "product_offer/save", "publish_product")

            logger.info("Product %d updated successfully", product_id)
            return response

        except EmagApiError as e:
            logger.error("Failed to update product %d: %s", product_id, str(e))
            raise ServiceError(f"Product update failed: {str(e)}")
