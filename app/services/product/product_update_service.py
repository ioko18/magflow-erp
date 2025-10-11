"""
Product Update Service for MagFlow ERP
Handles importing products from Google Sheets and updating the local Product database
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.product_mapping import ImportLog
from app.services.google_sheets_service import GoogleSheetsService, ProductFromSheet

logger = logging.getLogger(__name__)


class ProductUpdateService:
    """Service for importing and updating products from Google Sheets"""

    def __init__(self, db_session: AsyncSession):
        """Initialize update service"""
        self.db = db_session
        self.sheets_service = GoogleSheetsService()

    async def preview_import(self) -> dict[str, Any]:
        """
        Preview what changes would be made by importing from Google Sheets

        Returns:
            Dict with preview information including new, updated, and unchanged products
        """
        try:
            # Get products from Google Sheets
            sheet_products = self.sheets_service.get_all_products()

            preview = {
                "total_rows": len(sheet_products),
                "new_products": [],
                "updated_products": [],
                "unchanged_products": [],
                "errors": [],
            }

            for sheet_product in sheet_products:
                if not sheet_product.sku:
                    preview["errors"].append(
                        {"row": sheet_product.row_number, "error": "Missing SKU"}
                    )
                    continue

                # Validate name length
                product_name = sheet_product.romanian_name
                if len(product_name) > 255:
                    preview["errors"].append(
                        {
                            "row": sheet_product.row_number,
                            "error": f"Product name too long ({len(product_name)} chars, max 255). Will be truncated.",
                            "sku": sheet_product.sku,
                        }
                    )
                    product_name = product_name[:252] + "..."

                # Check if product exists
                stmt = select(Product).where(Product.sku == sheet_product.sku)
                result = await self.db.execute(stmt)
                existing_product = result.scalar_one_or_none()

                if existing_product:
                    # Check if there are changes
                    changes = self._detect_changes(existing_product, sheet_product)
                    if changes:
                        preview["updated_products"].append(
                            {
                                "sku": sheet_product.sku,
                                "name": product_name,
                                "changes": changes,
                            }
                        )
                    else:
                        preview["unchanged_products"].append(
                            {"sku": sheet_product.sku, "name": product_name}
                        )
                else:
                    preview["new_products"].append(
                        {
                            "sku": sheet_product.sku,
                            "name": product_name,
                            "price": sheet_product.emag_fbe_ro_price_ron,
                        }
                    )

            return preview

        except Exception as e:
            logger.error(f"Preview failed: {e}")
            raise

    def _detect_changes(
        self, product: Product, sheet_product: ProductFromSheet
    ) -> list[dict[str, Any]]:
        """Detect changes between existing product and sheet data"""
        changes = []

        # Truncate name if needed (same logic as create/update)
        new_name = sheet_product.romanian_name
        if len(new_name) > 255:
            new_name = new_name[:252] + "..."

        # Check name
        if product.name != new_name:
            changes.append(
                {"field": "name", "old_value": product.name, "new_value": new_name}
            )

        # Check price
        new_price = sheet_product.emag_fbe_ro_price_ron
        if new_price and product.base_price != new_price:
            changes.append(
                {
                    "field": "base_price",
                    "old_value": str(product.base_price),
                    "new_value": str(new_price),
                }
            )

        # Check display_order
        new_display_order = sheet_product.sort_product
        if new_display_order is not None and product.display_order != new_display_order:
            changes.append(
                {
                    "field": "display_order",
                    "old_value": str(product.display_order)
                    if product.display_order is not None
                    else "None",
                    "new_value": str(new_display_order),
                }
            )

        # Check image_url
        new_image_url = sheet_product.image_url
        if new_image_url != product.image_url:
            old_url_display = (
                product.image_url[:50] + "..."
                if product.image_url and len(product.image_url) > 50
                else (product.image_url or "None")
            )
            new_url_display = (
                new_image_url[:50] + "..."
                if new_image_url and len(new_image_url) > 50
                else (new_image_url or "None")
            )
            changes.append(
                {
                    "field": "image_url",
                    "old_value": old_url_display,
                    "new_value": new_url_display,
                }
            )

        # Check brand
        new_brand = sheet_product.brand
        if new_brand != product.brand:
            changes.append(
                {
                    "field": "brand",
                    "old_value": product.brand or "None",
                    "new_value": new_brand or "None",
                }
            )

        # Check EAN
        new_ean = sheet_product.ean
        if new_ean != product.ean:
            changes.append(
                {
                    "field": "ean",
                    "old_value": product.ean or "None",
                    "new_value": new_ean or "None",
                }
            )

        # Check weight_kg
        new_weight = sheet_product.weight_kg
        if new_weight != product.weight_kg:
            old_weight_display = (
                f"{product.weight_kg} kg" if product.weight_kg is not None else "None"
            )
            new_weight_display = (
                f"{new_weight} kg" if new_weight is not None else "None"
            )
            changes.append(
                {
                    "field": "weight_kg",
                    "old_value": old_weight_display,
                    "new_value": new_weight_display,
                }
            )

        return changes

    async def import_and_update_products(
        self,
        user_email: str | None = None,
        update_existing: bool = True,
        create_new: bool = True,
    ) -> ImportLog:
        """
        Import products from Google Sheets and update local Product database

        Args:
            user_email: Email of user initiating import
            update_existing: Whether to update existing products
            create_new: Whether to create new products

        Returns:
            ImportLog: Log of the import operation
        """
        # Create import log
        import_log = ImportLog(
            import_type="product_update",
            source_name=self.sheets_service.config.sheet_name,
            status="in_progress",
            initiated_by=user_email,
            started_at=datetime.now(UTC),
        )
        self.db.add(import_log)
        await self.db.flush()

        try:
            # Get products from Google Sheets
            logger.info("Fetching products from Google Sheets...")
            sheet_products = self.sheets_service.get_all_products()
            import_log.total_rows = len(sheet_products)

            logger.info(f"Found {len(sheet_products)} products in Google Sheets")

            processed_skus = set()
            products_created = 0
            products_updated = 0

            # Process each product
            for sheet_product in sheet_products:
                sku = sheet_product.sku
                if not sku:
                    logger.warning("Skipping product without SKU: %s", sheet_product)
                    import_log.skipped_rows += 1
                    continue

                if sku in processed_skus:
                    logger.debug("Duplicate SKU '%s' detected in sheet. Skipping.", sku)
                    import_log.skipped_rows += 1
                    continue

                processed_skus.add(sku)

                try:
                    # Check if product exists
                    stmt = select(Product).where(Product.sku == sku)
                    result = await self.db.execute(stmt)
                    existing_product = result.scalar_one_or_none()

                    if existing_product:
                        if update_existing:
                            await self._update_product(existing_product, sheet_product)
                            products_updated += 1
                            import_log.successful_imports += 1
                        else:
                            import_log.skipped_rows += 1
                    else:
                        if create_new:
                            await self._create_product(sheet_product)
                            products_created += 1
                            import_log.successful_imports += 1
                        else:
                            import_log.skipped_rows += 1

                    # Commit after each successful product to avoid rollback issues
                    await self.db.commit()

                except Exception as e:
                    logger.error(f"Failed to process product {sku}: {e}")
                    import_log.failed_imports += 1
                    # Rollback only this product's transaction
                    await self.db.rollback()
                    # Re-add import_log to session after rollback
                    self.db.add(import_log)

            # Complete import
            import_log.status = "completed"
            import_log.completed_at = datetime.now(UTC)
            import_log.duration_seconds = (
                import_log.completed_at - import_log.started_at
            ).total_seconds()

            # Store additional stats in auto_mapped fields (repurposing for our use)
            import_log.auto_mapped_main = products_created
            import_log.auto_mapped_fbe = products_updated

            await self.db.commit()

            logger.info(
                f"Import completed: {products_created} created, "
                f"{products_updated} updated, {import_log.failed_imports} failed"
            )

            return import_log

        except Exception as e:
            logger.error(f"Import failed: {e}")
            import_log.status = "failed"
            import_log.error_message = str(e)
            import_log.completed_at = datetime.now(UTC)
            await self.db.commit()
            raise

    async def _create_product(self, sheet_product: ProductFromSheet) -> Product:
        """Create a new product from Google Sheets data"""
        # Truncate name to fit database constraints (max 255 chars)
        product_name = sheet_product.romanian_name
        if len(product_name) > 255:
            logger.warning(
                f"Product name too long ({len(product_name)} chars), truncating to 255: {sheet_product.sku}"
            )
            product_name = product_name[:252] + "..."  # Truncate and add ellipsis

        product = Product(
            sku=sheet_product.sku,
            name=product_name,
            base_price=sheet_product.emag_fbe_ro_price_ron or 0.0,
            currency="RON",
            is_active=True,
            display_order=sheet_product.sort_product,
            image_url=sheet_product.image_url,
            brand=sheet_product.brand,
            ean=sheet_product.ean,
            weight_kg=sheet_product.weight_kg,
        )

        self.db.add(product)
        await self.db.flush()

        logger.info(f"Created new product: {product.sku} - {product.name[:50]}...")
        return product

    async def _update_product(
        self, product: Product, sheet_product: ProductFromSheet
    ) -> Product:
        """Update existing product with Google Sheets data"""
        # Truncate name to fit database constraints (max 255 chars)
        new_name = sheet_product.romanian_name
        if len(new_name) > 255:
            logger.warning(
                f"Product name too long ({len(new_name)} chars), truncating to 255: {sheet_product.sku}"
            )
            new_name = new_name[:252] + "..."  # Truncate and add ellipsis

        # Update name if changed
        if product.name != new_name:
            logger.info(
                f"Updating name for {product.sku}: {product.name[:50]}... -> {new_name[:50]}..."
            )
            product.name = new_name

        # Update price if changed and valid
        new_price = sheet_product.emag_fbe_ro_price_ron
        if new_price and product.base_price != new_price:
            logger.info(
                f"Updating price for {product.sku}: {product.base_price} -> {new_price}"
            )
            product.base_price = new_price

        # Update display_order if changed
        new_display_order = sheet_product.sort_product
        if new_display_order is not None and product.display_order != new_display_order:
            logger.info(
                f"Updating display_order for {product.sku}: {product.display_order} -> {new_display_order}"
            )
            product.display_order = new_display_order
        elif new_display_order is None and product.display_order is not None:
            # If sort_product is removed from sheet, keep existing display_order
            logger.debug(
                f"Keeping existing display_order for {product.sku}: {product.display_order}"
            )

        # Update image_url if changed
        new_image_url = sheet_product.image_url
        if new_image_url != product.image_url:
            if new_image_url:
                logger.info(
                    f"Updating image_url for {product.sku}: {product.image_url} -> {new_image_url[:50]}..."
                )
            else:
                logger.info(f"Removing image_url for {product.sku}")
            product.image_url = new_image_url

        # Update brand if changed
        new_brand = sheet_product.brand
        if new_brand != product.brand:
            if new_brand:
                logger.info(
                    f"Updating brand for {product.sku}: {product.brand} -> {new_brand}"
                )
            else:
                logger.info(f"Removing brand for {product.sku}")
            product.brand = new_brand

        # Update EAN if changed
        new_ean = sheet_product.ean
        if new_ean != product.ean:
            if new_ean:
                logger.info(
                    f"Updating EAN for {product.sku}: {product.ean} -> {new_ean}"
                )
            else:
                logger.info(f"Removing EAN for {product.sku}")
            product.ean = new_ean

        # Update weight_kg if changed
        new_weight = sheet_product.weight_kg
        if new_weight != product.weight_kg:
            if new_weight is not None:
                logger.info(
                    f"Updating weight for {product.sku}: {product.weight_kg} kg -> {new_weight} kg"
                )
            else:
                logger.info(f"Removing weight for {product.sku}")
            product.weight_kg = new_weight

        await self.db.flush()
        return product

    async def get_product_statistics(self) -> dict[str, Any]:
        """Get statistics about products in the database"""
        # Total products
        total_stmt = select(func.count(Product.id))
        total_result = await self.db.execute(total_stmt)
        total_products = total_result.scalar() or 0

        # Active products
        active_stmt = select(func.count(Product.id)).where(Product.is_active)
        active_result = await self.db.execute(active_stmt)
        active_products = active_result.scalar() or 0

        # Inactive products
        inactive_products = total_products - active_products

        # Products with prices
        priced_stmt = select(func.count(Product.id)).where(Product.base_price > 0)
        priced_result = await self.db.execute(priced_stmt)
        priced_products = priced_result.scalar() or 0

        return {
            "total_products": total_products,
            "active_products": active_products,
            "inactive_products": inactive_products,
            "priced_products": priced_products,
            "unpriced_products": total_products - priced_products,
        }

    async def get_all_products(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        active_only: bool = False,
    ) -> tuple[list[Product], int]:
        """
        Get all products with pagination and filtering

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search term for SKU or name
            active_only: Only return active products

        Returns:
            Tuple of (list of products, total count)
        """
        # Build base query
        stmt = select(Product)

        # Apply filters
        if active_only:
            stmt = stmt.where(Product.is_active)

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                (Product.sku.ilike(search_term)) | (Product.name.ilike(search_term))
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.order_by(Product.sku).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        return list(products), total

    async def get_import_history(self, limit: int = 10) -> list[ImportLog]:
        """Get recent import history for product updates"""
        stmt = (
            select(ImportLog)
            .where(ImportLog.import_type == "product_update")
            .order_by(ImportLog.started_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
