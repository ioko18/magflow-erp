"""
Enhanced eMAG Integration Service for MagFlow ERP.

This service provides comprehensive eMAG marketplace integration with full
product synchronization, order management, and real-time monitoring according
to eMAG API v4.4.8 specifications.
"""

import asyncio
import time
import random
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.core.exceptions import ServiceError
from app.services.emag_api_client import EmagApiClient, EmagApiError
from app.config.emag_config import get_emag_config, EmagApiConfig
from app.models.emag_models import EmagProductV2, EmagSyncLog
from app.core.database import get_async_session

logger = get_logger(__name__)
class EnhancedEmagRateLimiter:
    """Enhanced rate limiter for eMAG API with per-second and per-minute limits."""
    
    def __init__(self, config: EmagApiConfig):
        self.config = config
        self.rate_limits = config.rate_limits
        self._locks: Dict[str, asyncio.Lock] = {}
        self._request_windows: Dict[str, Dict[str, deque]] = {}
        
    async def acquire(self, resource_type: str = "other"):
        """Acquire permission to make a request respecting eMAG API limits."""
        per_second_limit = (
            self.rate_limits.orders_rps if resource_type == "orders" 
            else self.rate_limits.other_rps
        )
        per_minute_limit = (
            self.rate_limits.orders_rpm if resource_type == "orders" 
            else self.rate_limits.other_rpm
        )
        
        lock = self._locks.setdefault(resource_type, asyncio.Lock())
        windows = self._request_windows.setdefault(
            resource_type, {"second": deque(), "minute": deque()}
        )
        
        second_window = windows["second"]
        minute_window = windows["minute"]
        
        while True:
            async with lock:
                now = time.monotonic()
                
                # Clear expired entries
                while second_window and now - second_window[0] >= 1.0:
                    second_window.popleft()
                while minute_window and now - minute_window[0] >= 60.0:
                    minute_window.popleft()
                
                if (len(second_window) < per_second_limit and 
                    len(minute_window) < per_minute_limit):
                    # Approved; register request timestamp
                    second_window.append(now)
                    minute_window.append(now)
                    return
                
                # Determine wait time
                wait_times = []
                if len(second_window) >= per_second_limit:
                    wait_times.append(1.0 - (now - second_window[0]))
                if len(minute_window) >= per_minute_limit:
                    wait_times.append(60.0 - (now - minute_window[0]))
                
                wait_time = max(0.0, min(wait_times) if wait_times else 0.0)
            
            # Apply jitter to avoid thundering herd
            jitter = random.uniform(0, self.rate_limits.jitter_max)
            await asyncio.sleep(max(0.001, wait_time) + jitter)


class EnhancedEmagIntegrationService:
    """Enhanced eMAG integration service with full synchronization capabilities."""
    
    def __init__(self, account_type: str = "main", db_session: Optional[AsyncSession] = None):
        """Initialize the enhanced eMAG integration service.
        
        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
            db_session: Optional database session
        """
        self.account_type = account_type.lower()
        self.config = get_emag_config(self.account_type)
        self.client: Optional[EmagApiClient] = None
        self.rate_limiter = EnhancedEmagRateLimiter(self.config)
        self.db_session = db_session
        self._sync_tasks: Dict[str, asyncio.Task] = {}
        self._metrics = {
            "requests_made": 0,
            "rate_limit_hits": 0,
            "errors": 0,
            "products_synced": 0,
            "offers_synced": 0,
            "orders_synced": 0,
        }
        self._mock_data = False  # Use real eMAG API data
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def initialize(self):
        """Initialize the eMAG API client and database connection."""
        if not self.client:
            self.client = EmagApiClient(
                username=self.config.api_username,
                password=self.config.api_password,
                base_url=self.config.base_url,
                timeout=self.config.api_timeout,
                max_retries=self.config.max_retries,
            )
            await self.client.start()
            
        if not self.db_session:
            # Get async session for database operations
            async for session in get_async_session():
                self.db_session = session
                break
            
        logger.info(
            "Initialized enhanced eMAG service for %s account (environment: %s)",
            self.account_type, self.config.environment.value
        )
    
    async def close(self):
        """Close the eMAG API client and clean up resources."""
        if self.client:
            await self.client.close()
            self.client = None
            
        # Cancel any running sync tasks
        for task_id, task in self._sync_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info("Cancelled sync task: %s", task_id)
        
        logger.info("Closed enhanced eMAG service for %s account", self.account_type)
    
    async def sync_all_products_from_both_accounts(
        self,
        max_pages_per_account: int = 100,
        delay_between_requests: float = 1.2,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """Synchronize all products from both MAIN and FBE accounts.
        
        Args:
            max_pages_per_account: Maximum pages to process per account
            delay_between_requests: Delay between API requests
            include_inactive: Whether to include inactive products
            
        Returns:
            Dict with synchronization results from both accounts
        """
        logger.info("Starting full product sync from both accounts")
        
        # Create sync log
        sync_log = EmagSyncLog(
            sync_type="products",
            account_type="both",
            operation="full_sync",
            sync_params={
                "max_pages_per_account": max_pages_per_account,
                "delay_between_requests": delay_between_requests,
                "include_inactive": include_inactive,
            },
            status="running",
            triggered_by="api",
            sync_version="v4.4.8",
        )
        self.db_session.add(sync_log)
        await self.db_session.commit()
        
        try:
            # Sync from both accounts
            results = {}
            
            # MAIN account
            if self.account_type == "main" or self.account_type == "both":
                main_service = EnhancedEmagIntegrationService("main", self.db_session)
                await main_service.initialize()
                try:
                    results["main_account"] = await main_service._sync_products_from_account(
                        max_pages_per_account, delay_between_requests, include_inactive
                    )
                finally:
                    await main_service.close()
            
            # FBE account
            fbe_service = EnhancedEmagIntegrationService("fbe", self.db_session)
            await fbe_service.initialize()
            try:
                results["fbe_account"] = await fbe_service._sync_products_from_account(
                    max_pages_per_account, delay_between_requests, include_inactive
                )
            finally:
                await fbe_service.close()
            
            # Combine and deduplicate results
            combined_results = self._combine_and_deduplicate_products(
                results.get("main_account", {}),
                results.get("fbe_account", {})
            )
            results["combined"] = combined_results
            
            # Update sync log
            sync_log.status = "completed"
            sync_log.completed_at = datetime.utcnow()
            sync_log.total_items = combined_results.get("total_products_processed", 0)
            sync_log.processed_items = combined_results.get("products_count", 0)
            sync_log.duration_seconds = (
                sync_log.completed_at - sync_log.started_at
            ).total_seconds()
            
            await self.db_session.commit()
            
            logger.info("Completed full product sync from both accounts")
            return results
            
        except Exception as e:
            sync_log.status = "failed"
            sync_log.completed_at = datetime.utcnow()
            sync_log.errors = [{"error": str(e), "timestamp": datetime.utcnow().isoformat()}]
            await self.db_session.commit()
            logger.error("Failed full product sync: %s", str(e), exc_info=True)
            raise ServiceError(f"Failed to sync products from both accounts: {str(e)}")
    
    async def _sync_products_from_account(
        self,
        max_pages: int,
        delay_between_requests: float,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """Sync products from a specific account with pagination."""
        logger.info("Syncing products from %s account", self.account_type)
        
        products = []
        page = 1
        total_pages = None
        
        while page <= max_pages:
            try:
                # Apply rate limiting
                await self.rate_limiter.acquire("other")
                
                # Get products page
                response = await self.client.get_products(
                    page=page,
                    items_per_page=self.config.items_per_page,
                    filters={"status": "all" if include_inactive else "active"}
                )
                
                self._metrics["requests_made"] += 1
                
                if not response or "results" not in response:
                    logger.warning("No results in response for page %d", page)
                    break
                
                page_products = response["results"]
                products.extend(page_products)
                
                # Update pagination info
                pagination = response.get("pagination", {})
                if total_pages is None:
                    total_pages = pagination.get("totalPages", max_pages)
                
                logger.info(
                    "Processed page %d/%s: %d products (Total: %d)",
                    page, total_pages or "?", len(page_products), len(products)
                )
                
                # Check if we have more pages
                if page >= pagination.get("totalPages", 0):
                    break
                
                page += 1
                
                # Delay between requests
                if delay_between_requests > 0:
                    await asyncio.sleep(delay_between_requests)
                    
            except EmagApiError as e:
                if e.status_code == 429:  # Rate limit
                    self._metrics["rate_limit_hits"] += 1
                    wait_time = 2 ** min(self._metrics["rate_limit_hits"], 6)  # Max 64s
                    logger.warning("Rate limited, waiting %ds", wait_time)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error("API error on page %d: %s", page, str(e))
                    self._metrics["errors"] += 1
                    break
            except Exception as e:
                logger.error("Unexpected error on page %d: %s", page, str(e), exc_info=True)
                self._metrics["errors"] += 1
                break
        
        # Process and save products to database
        processed_products = await self._process_and_save_products(products)
        
        return {
            "products_count": len(processed_products),
            "pages_processed": page - 1,
            "products": processed_products,
            "account_type": self.account_type,
            "sync_timestamp": datetime.utcnow().isoformat(),
        }
    
    async def _process_and_save_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and save products to database using async session."""
        processed_products = []
        
        for product_data in products:
            try:
                # Extract product information
                sku = product_data.get("part_number") or product_data.get("sku")
                if not sku:
                    logger.warning("Product missing SKU, skipping: %s", product_data.get("id"))
                    continue
                
                # Check if product exists using async session
                stmt = select(EmagProductV2).where(
                    and_(
                        EmagProductV2.sku == sku,
                        EmagProductV2.account_type == self.account_type
                    )
                )
                result = await self.db_session.execute(stmt)
                existing_product = result.scalar_one_or_none()
                
                product_instance: EmagProductV2
                if existing_product:
                    # Update existing product
                    self._update_product_from_emag_data(existing_product, product_data)
                    existing_product.last_synced_at = datetime.utcnow()
                    existing_product.sync_status = "synced"
                    existing_product.sync_attempts += 1
                    product_instance = existing_product
                else:
                    # Create new product
                    new_product = self._create_product_from_emag_data(product_data)
                    self.db_session.add(new_product)
                    await self.db_session.flush()
                    product_instance = new_product
                
                await self._upsert_offer_from_product_data(product_instance, product_data)
                
                processed_products.append({
                    "sku": sku,
                    "name": product_data.get("name", ""),
                    "status": "processed",
                    "action": "updated" if existing_product else "created"
                })
                
                self._metrics["products_synced"] += 1
                
            except Exception as e:
                logger.error("Error processing product %s: %s", sku, str(e), exc_info=True)
                processed_products.append({
                    "sku": sku,
                    "status": "error",
                    "error": str(e)
                })
        
        # Commit changes using async session
        try:
            await self.db_session.commit()
            logger.info("Successfully saved %d products to database", len(processed_products))
        except Exception as e:
            await self.db_session.rollback()
            logger.error("Failed to save products to database: %s", str(e))
            raise ServiceError(f"Failed to save products: {str(e)}")
        
        return processed_products
    
    def _create_product_from_emag_data(self, product_data: Dict[str, Any]) -> EmagProductV2:
        """Create EmagProductV2 from eMAG API data with improved field mapping."""
        
        # Extract stock from complex structure
        stock_quantity = 0
        if "stock" in product_data:
            stock_data = product_data["stock"]
            if isinstance(stock_data, list) and stock_data:
                stock_quantity = self._safe_int(stock_data[0].get("value", 0))
            elif isinstance(stock_data, dict):
                stock_quantity = self._safe_int(stock_data.get("value", 0))
            else:
                stock_quantity = self._safe_int(stock_data)
        elif "general_stock" in product_data:
            stock_quantity = self._safe_int(product_data.get("general_stock", 0))
        
        # Extract supply lead time from offer_details
        supply_lead_time = None
        if "offer_details" in product_data and isinstance(product_data["offer_details"], dict):
            supply_lead_time = self._safe_int(product_data["offer_details"].get("supply_lead_time"))
        elif "supply_lead_time" in product_data:
            supply_lead_time = self._safe_int(product_data.get("supply_lead_time"))
        
        # Process characteristics - convert from list to dict for easier access
        characteristics = {}
        if "characteristics" in product_data and isinstance(product_data["characteristics"], list):
            for char in product_data["characteristics"]:
                if isinstance(char, dict) and "id" in char and "value" in char:
                    characteristics[str(char["id"])] = {
                        "id": char["id"],
                        "value": char["value"],
                        "tag": char.get("tag")
                    }
        elif isinstance(product_data.get("characteristics"), dict):
            characteristics = product_data["characteristics"]
        
        # Build comprehensive attributes dictionary
        attributes = {
            "ean_codes": product_data.get("ean", []) if isinstance(product_data.get("ean"), list) else [],
            "vat_id": self._safe_int(product_data.get("vat_id")),
            "min_sale_price": self._safe_float(product_data.get("min_sale_price")),
            "max_sale_price": self._safe_float(product_data.get("max_sale_price")),
            "recommended_price": self._safe_float(product_data.get("recommended_price")),
            "best_offer_sale_price": self._safe_float(product_data.get("best_offer_sale_price")),
            "part_number_key": self._safe_str(product_data.get("part_number_key")),
            "vendor_category_id": self._safe_str(product_data.get("vendor_category_id")),
            "estimated_stock": self._safe_int(product_data.get("estimated_stock")),
            "ownership": product_data.get("ownership", False),
            "genius_eligibility": self._safe_int(product_data.get("genius_eligibility")),
        }
        
        # Extract availability and handling time from arrays
        if "availability" in product_data and isinstance(product_data["availability"], list) and product_data["availability"]:
            attributes["availability"] = self._safe_int(product_data["availability"][0].get("value"))
        
        if "handling_time" in product_data and isinstance(product_data["handling_time"], list) and product_data["handling_time"]:
            attributes["handling_time"] = self._safe_int(product_data["handling_time"][0].get("value"))
        
        # Extract warranty from offer_details
        if "offer_details" in product_data and isinstance(product_data["offer_details"], dict):
            attributes["warranty_type"] = self._safe_int(product_data["offer_details"].get("warranty_type"))
            attributes["emag_club"] = self._safe_int(product_data["offer_details"].get("emag_club"))
        elif "warranty" in product_data:
            attributes["warranty_type"] = self._safe_int(product_data.get("warranty"))
        
        # Clean up None values from attributes
        attributes = {k: v for k, v in attributes.items() if v is not None and v != ""}

        return EmagProductV2(
            emag_id=self._safe_str(product_data.get("id")),
            sku=self._safe_str(product_data.get("part_number") or product_data.get("sku")),
            name=self._safe_str(product_data.get("name")),
            account_type=self.account_type,
            description=self._safe_str(product_data.get("description")),
            brand=self._safe_str(product_data.get("brand") or product_data.get("brand_name")),
            manufacturer=self._safe_str(product_data.get("manufacturer")),
            price=self._safe_float(product_data.get("sale_price") or product_data.get("price")),
            currency=self._safe_str(product_data.get("currency"), "RON"),
            stock_quantity=stock_quantity,
            category_id=self._safe_str(product_data.get("category_id")),
            emag_category_id=self._safe_str(product_data.get("category_id")),
            emag_category_name=self._safe_str(product_data.get("category_name")),
            is_active=product_data.get("status") == 1 or product_data.get("status") == "1" or product_data.get("status") == "active",
            status=self._safe_str(product_data.get("status")),
            images=product_data.get("images", []) if isinstance(product_data.get("images"), list) else [],
            green_tax=self._safe_float(product_data.get("green_tax")) if product_data.get("green_tax") else None,
            supply_lead_time=supply_lead_time,
            safety_information=self._safe_str(product_data.get("safety_information")) if product_data.get("safety_information") else None,
            manufacturer_info=product_data.get("manufacturer_info", []) if isinstance(product_data.get("manufacturer_info"), list) else [],
            eu_representative=product_data.get("eu_representative", []) if isinstance(product_data.get("eu_representative"), list) else [],
            emag_characteristics=characteristics,
            attributes=attributes,
            specifications=product_data.get("specifications", {}) if isinstance(product_data.get("specifications"), dict) else {},
            sync_status="synced",
            last_synced_at=datetime.utcnow(),
            sync_attempts=1,
            emag_created_at=self._parse_datetime(product_data.get("created")),
            emag_modified_at=self._parse_datetime(product_data.get("modified")),
            raw_emag_data=product_data,
        )
    
    def _update_product_from_emag_data(self, product: EmagProductV2, product_data: Dict[str, Any]):
        """Update existing EmagProductV2 with eMAG API data using improved field mapping."""
        
        # Extract stock from complex structure
        stock_quantity = product.stock_quantity or 0
        if "stock" in product_data:
            stock_data = product_data["stock"]
            if isinstance(stock_data, list) and stock_data:
                stock_quantity = self._safe_int(stock_data[0].get("value", 0))
            elif isinstance(stock_data, dict):
                stock_quantity = self._safe_int(stock_data.get("value", 0))
            else:
                stock_quantity = self._safe_int(stock_data)
        elif "general_stock" in product_data:
            stock_quantity = self._safe_int(product_data.get("general_stock", 0))
        
        # Extract supply lead time from offer_details
        supply_lead_time = product.supply_lead_time
        if "offer_details" in product_data and isinstance(product_data["offer_details"], dict):
            supply_lead_time = self._safe_int(product_data["offer_details"].get("supply_lead_time"))
        elif "supply_lead_time" in product_data:
            supply_lead_time = self._safe_int(product_data.get("supply_lead_time"))
        
        # Process characteristics - convert from list to dict for easier access
        characteristics = product.emag_characteristics or {}
        if "characteristics" in product_data and isinstance(product_data["characteristics"], list):
            characteristics = {}
            for char in product_data["characteristics"]:
                if isinstance(char, dict) and "id" in char and "value" in char:
                    characteristics[str(char["id"])] = {
                        "id": char["id"],
                        "value": char["value"],
                        "tag": char.get("tag")
                    }
        elif isinstance(product_data.get("characteristics"), dict):
            characteristics = product_data["characteristics"]
        
        # Update attributes with new data
        attributes = product.attributes or {}
        new_attributes = {
            "ean_codes": product_data.get("ean", []) if isinstance(product_data.get("ean"), list) else [],
            "vat_id": self._safe_int(product_data.get("vat_id")),
            "min_sale_price": self._safe_float(product_data.get("min_sale_price")),
            "max_sale_price": self._safe_float(product_data.get("max_sale_price")),
            "recommended_price": self._safe_float(product_data.get("recommended_price")),
            "best_offer_sale_price": self._safe_float(product_data.get("best_offer_sale_price")),
            "part_number_key": self._safe_str(product_data.get("part_number_key")),
            "vendor_category_id": self._safe_str(product_data.get("vendor_category_id")),
            "estimated_stock": self._safe_int(product_data.get("estimated_stock")),
            "ownership": product_data.get("ownership", False),
            "genius_eligibility": self._safe_int(product_data.get("genius_eligibility")),
            "green_tax": self._safe_float(product_data.get("green_tax")),
            "shipping_weight": self._safe_float(product_data.get("shipping_weight")),
            "shipping_size": product_data.get("shipping_size", {}) if isinstance(product_data.get("shipping_size"), dict) else {},
            "marketplace_status": self._safe_str(product_data.get("marketplace_status")),
            "visibility": self._safe_str(product_data.get("visibility")),
            "original_price": self._safe_float(product_data.get("original_price")),
        }
        
        # Extract availability and handling time from arrays
        if "availability" in product_data and isinstance(product_data["availability"], list) and product_data["availability"]:
            new_attributes["availability"] = self._safe_int(product_data["availability"][0].get("value"))
        
        if "handling_time" in product_data and isinstance(product_data["handling_time"], list) and product_data["handling_time"]:
            new_attributes["handling_time"] = self._safe_int(product_data["handling_time"][0].get("value"))
        
        # Extract warranty from offer_details
        if "offer_details" in product_data and isinstance(product_data["offer_details"], dict):
            new_attributes["warranty_type"] = self._safe_int(product_data["offer_details"].get("warranty_type"))
            new_attributes["emag_club"] = self._safe_int(product_data["offer_details"].get("emag_club"))
        elif "warranty" in product_data:
            new_attributes["warranty_type"] = self._safe_int(product_data.get("warranty"))
        
        # Clean up None values and merge with existing attributes
        new_attributes = {k: v for k, v in new_attributes.items() if v is not None and v != ""}
        attributes.update(new_attributes)
        
        # Update all fields
        product.name = self._safe_str(product_data.get("name"), product.name)
        product.description = self._safe_str(product_data.get("description"), product.description or "")
        product.brand = self._safe_str(product_data.get("brand") or product_data.get("brand_name"), product.brand or "")
        product.manufacturer = self._safe_str(product_data.get("manufacturer"), product.manufacturer or "")
        product.price = self._safe_float(product_data.get("sale_price") or product_data.get("price"), product.price or 0.0)
        product.currency = self._safe_str(product_data.get("currency"), product.currency or "RON")
        product.stock_quantity = stock_quantity
        product.category_id = self._safe_str(product_data.get("category_id"), product.category_id or "")
        product.emag_category_id = self._safe_str(product_data.get("category_id"), product.emag_category_id or "")
        product.emag_category_name = self._safe_str(product_data.get("category_name"), product.emag_category_name or "")
        product.is_active = product_data.get("status") == 1 or product_data.get("status") == "1" or product_data.get("status") == "active"
        product.status = self._safe_str(product_data.get("status"), product.status or "")
        product.images = product_data.get("images", []) if isinstance(product_data.get("images"), list) else []
        product.supply_lead_time = supply_lead_time
        product.green_tax = self._safe_float(product_data.get("green_tax"))
        product.safety_information = self._safe_str(product_data.get("safety_information"), product.safety_information or "")
        product.manufacturer_info = product_data.get("manufacturer_info", []) if isinstance(product_data.get("manufacturer_info"), list) else []
        product.eu_representative = product_data.get("eu_representative", []) if isinstance(product_data.get("eu_representative"), list) else []
        product.emag_characteristics = characteristics
        product.attributes = attributes
        product.specifications = product_data.get("specifications", {}) if isinstance(product_data.get("specifications"), dict) else {}
        product.emag_modified_at = self._parse_datetime(product_data.get("modified"))
        product.raw_emag_data = product_data
        product.updated_at = datetime.utcnow()
        product.sync_status = "synced"
        product.last_synced_at = datetime.utcnow()
    
    def _combine_and_deduplicate_products(
        self, 
        main_results: Dict[str, Any], 
        fbe_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine and deduplicate products from both accounts."""
        main_products = main_results.get("products", [])
        fbe_products = fbe_results.get("products", [])
        
        # Create SKU-based deduplication
        unique_skus = set()
        combined_products = []
        
        # Add MAIN products first (priority)
        for product in main_products:
            sku = product.get("sku")
            if sku and sku not in unique_skus:
                unique_skus.add(sku)
                product["source_account"] = "main"
                combined_products.append(product)
        
        # Add FBE products (only if SKU not already exists)
        for product in fbe_products:
            sku = product.get("sku")
            if sku and sku not in unique_skus:
                unique_skus.add(sku)
                product["source_account"] = "fbe"
                combined_products.append(product)
        
        return {
            "products_count": len(combined_products),
            "unique_skus": len(unique_skus),
            "main_products": len(main_products),
            "fbe_products": len(fbe_products),
            "products": combined_products,
            "deduplication_stats": {
                "total_before": len(main_products) + len(fbe_products),
                "total_after": len(combined_products),
                "duplicates_removed": len(main_products) + len(fbe_products) - len(combined_products)
            }
        }
    
    async def sync_all_offers_from_both_accounts(
        self,
        max_pages_per_account: int = 50,
        delay_between_requests: float = 1.2
    ) -> Dict[str, Any]:
        """Synchronize offer data by reusing the product sync pipeline for both accounts."""

        logger.info("Starting offer synchronization leveraging product payload metadata")

        product_sync_results = await self.sync_all_products_from_both_accounts(
            max_pages_per_account=max_pages_per_account,
            delay_between_requests=delay_between_requests,
            include_inactive=True
        )

        return {
            "status": "completed",
            "message": "Offer data refreshed based on latest product payloads",
            "products": product_sync_results,
        }

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return default
        if isinstance(value, list) and value:
            return EnhancedEmagIntegrationService._safe_int(value[0], default)
        return default

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        if isinstance(value, list) and value:
            return EnhancedEmagIntegrationService._safe_float(value[0], default)
        return default

    @staticmethod
    def _safe_str(value, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list) and value:
            return str(value[0])
        return str(value) if value else default
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from eMAG API."""
        if not date_str:
            return None
        
        try:
            # eMAG format: "YYYY-mm-dd HH:ii:ss"
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            logger.warning("Failed to parse datetime: %s", date_str)
            return None
    
    def get_sync_metrics(self) -> Dict[str, Any]:
        """Get current synchronization metrics."""
        return {
            "account_type": self.account_type,
            "metrics": self._metrics.copy(),
            "config": {
                "max_pages_per_sync": self.config.max_pages_per_sync,
                "items_per_page": self.config.items_per_page,
                "delay_between_requests": self.config.delay_between_requests,
                "rate_limits": {
                    "orders_rps": self.config.rate_limits.orders_rps,
                    "other_rps": self.config.rate_limits.other_rps,
                }
            }
        }
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status."""
        if self._mock_data:
            # Return mock data for now
            return {
                "account_type": self.account_type,
                "latest_sync": {
                    "id": "mock-sync-001",
                    "status": "completed",
                    "started_at": "2024-09-29T10:00:00Z",
                    "completed_at": "2024-09-29T10:05:30Z",
                    "duration_seconds": 330,
                    "total_items": 150,
                    "processed_items": 150,
                },
                "active_progress": None,
                "metrics": self.get_sync_metrics()
            }
        
        # TODO: Implement real database queries when async session is properly configured
        return {
            "account_type": self.account_type,
            "latest_sync": {
                "id": None,
                "status": "never_run",
                "started_at": None,
                "completed_at": None,
                "duration_seconds": None,
                "total_items": 0,
                "processed_items": 0,
            },
            "active_progress": None,
            "metrics": self.get_sync_metrics()
        }
