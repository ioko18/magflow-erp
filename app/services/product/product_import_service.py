"""
Product Import Service for MagFlow ERP
Handles importing products from Google Sheets and mapping to eMAG accounts
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models.emag_models import EmagProductV2
from app.models.product_history import ProductSKUHistory
from app.models.product_mapping import GoogleSheetsProductMapping, ImportLog
from app.models.product_supplier_sheet import ProductSupplierSheet
from app.models.supplier import Supplier
from app.services.google_sheets_service import GoogleSheetsService, ProductFromSheet

logger = logging.getLogger(__name__)


class ProductImportService:
    """Service for importing products from Google Sheets and mapping to eMAG"""

    def __init__(self, db_session: AsyncSession):
        """Initialize import service"""
        self.db = db_session
        self.sheets_service = GoogleSheetsService()

    async def import_from_google_sheets(
        self,
        user_email: str | None = None,
        auto_map: bool = True,
        import_suppliers: bool = True,
    ) -> ImportLog:
        """
        Import products from Google Sheets and optionally auto-map to eMAG

        Args:
            user_email: Email of user initiating import
            auto_map: Whether to automatically map products to eMAG accounts
            import_suppliers: Whether to import supplier data from Product_Suppliers tab

        Returns:
            ImportLog: Log of the import operation
        """
        # Create import log
        import_log = ImportLog(
            import_type="google_sheets",
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
                    logger.debug(
                        "Duplicate SKU '%s' detected in sheet. Skipping subsequent occurrence.",
                        sku,
                    )
                    import_log.skipped_rows += 1
                    continue

                processed_skus.add(sku)

                # Use nested transaction (savepoint) to handle individual product errors
                async with self.db.begin_nested():
                    try:
                        created, updated = await self._import_single_product(
                            sheet_product, import_log, auto_map
                        )
                        if created:
                            products_created += 1
                        if updated:
                            products_updated += 1
                        import_log.successful_imports += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to import product {sheet_product.sku}: {e}",
                            exc_info=True,
                        )
                        import_log.failed_imports += 1
                        # Rollback will happen automatically when exiting the nested context
                        # but import_log remains in the parent transaction

            # Import suppliers if requested
            if import_suppliers:
                try:
                    await self._import_suppliers(user_email)
                except Exception as e:
                    logger.error(f"Failed to import suppliers: {e}")
                    # Don't fail the entire import if suppliers fail

            # Complete import
            import_log.status = "completed"
            import_log.completed_at = datetime.now(UTC)
            import_log.duration_seconds = (
                import_log.completed_at - import_log.started_at
            ).total_seconds()

            # Store products created/updated in auto_mapped fields (repurposed)
            import_log.auto_mapped_main = products_created
            import_log.auto_mapped_fbe = products_updated

            await self.db.commit()

            logger.info(
                f"Import completed: {import_log.successful_imports} successful, "
                f"{import_log.failed_imports} failed, "
                f"{products_created} created, {products_updated} updated"
            )

            return import_log

        except Exception as e:
            logger.error(f"Import failed: {e}")
            import_log.status = "failed"
            import_log.error_message = str(e)
            import_log.completed_at = datetime.now(UTC)
            await self.db.commit()
            raise

    async def _import_single_product(
        self, sheet_product: ProductFromSheet, import_log: ImportLog, auto_map: bool
    ) -> tuple[bool, bool]:
        """
        Import a single product and create/update mapping

        Args:
            sheet_product: Product data from Google Sheets
            import_log: Import log to update statistics
            auto_map: Whether to automatically map to eMAG

        Returns:
            tuple[bool, bool]: (product_created, product_updated)
        """
        # First, ensure the product exists in the products table
        from app.models.product import Product

        product_stmt = select(Product).where(Product.sku == sheet_product.sku)
        product_result = await self.db.execute(product_stmt)
        product = product_result.scalar_one_or_none()

        product_created = False
        product_updated = False

        if not product:
            # Create new product in products table
            product = Product(
                sku=sheet_product.sku,
                name=sheet_product.romanian_name,
                base_price=sheet_product.emag_fbe_ro_price_ron or 0.0,
                currency="RON",
                is_active=True,
                image_url=sheet_product.image_url,
                brand=sheet_product.brand,
                ean=sheet_product.ean,
                weight_kg=sheet_product.weight_kg,
                display_order=sheet_product.sort_product,
                invoice_name_ro=sheet_product.invoice_name_ro,
                invoice_name_en=sheet_product.invoice_name_en,
            )
            self.db.add(product)
            # Flush will happen at the end to get product.id for SKU history
            product_created = True
            logger.info(f"Created new product: {sheet_product.sku}")
        else:
            # Update existing product
            product.name = sheet_product.romanian_name
            if sheet_product.emag_fbe_ro_price_ron:
                product.base_price = sheet_product.emag_fbe_ro_price_ron
            # Update additional fields from Google Sheets
            product.image_url = sheet_product.image_url
            product.brand = sheet_product.brand
            product.ean = sheet_product.ean
            product.weight_kg = sheet_product.weight_kg
            if sheet_product.sort_product is not None:
                product.display_order = sheet_product.sort_product
            # Update invoice names for customs documentation
            product.invoice_name_ro = sheet_product.invoice_name_ro
            product.invoice_name_en = sheet_product.invoice_name_en
            product_updated = True
            logger.debug(f"Updated existing product: {sheet_product.sku}")

        # Check if mapping already exists
        stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.local_sku == sheet_product.sku
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if mapping:
            # Update existing mapping
            mapping.local_product_name = sheet_product.romanian_name
            mapping.local_price = sheet_product.emag_fbe_ro_price_ron
            mapping.google_sheet_row = sheet_product.row_number
            mapping.google_sheet_data = json.dumps(sheet_product.raw_data)
            mapping.last_imported_at = datetime.now(UTC)
            mapping.import_source = "google_sheets"
        else:
            # Create new mapping
            mapping = GoogleSheetsProductMapping(
                local_sku=sheet_product.sku,
                local_product_name=sheet_product.romanian_name,
                local_price=sheet_product.emag_fbe_ro_price_ron,
                google_sheet_row=sheet_product.row_number,
                google_sheet_data=json.dumps(sheet_product.raw_data),
                last_imported_at=datetime.now(UTC),
                import_source="google_sheets",
                is_active=True,
            )
            self.db.add(mapping)

        # Flush to get product.id before importing SKU history
        await self.db.flush()

        # Import SKU history if available (needs product.id)
        if sheet_product.sku_history:
            await self._import_sku_history(product, sheet_product.sku_history)

        # Auto-map to eMAG if requested
        if auto_map:
            await self._auto_map_to_emag(mapping, import_log)

        return product_created, product_updated

    async def _import_sku_history(
        self, product, old_skus: list[str]
    ) -> None:
        """
        Import historical SKUs from Google Sheets

        Args:
            product: Product instance
            old_skus: List of old SKUs from SKU_History column
        """
        for old_sku in old_skus:
            # Check if this SKU history entry already exists
            existing_query = select(ProductSKUHistory).where(
                ProductSKUHistory.product_id == product.id,
                ProductSKUHistory.old_sku == old_sku,
                ProductSKUHistory.new_sku == product.sku,
            )
            result = await self.db.execute(existing_query)
            existing = result.scalar_one_or_none()

            if not existing:
                # Create new SKU history entry
                # Note: changed_at must be timezone-naive to match DB column type
                sku_history = ProductSKUHistory(
                    product_id=product.id,
                    old_sku=old_sku,
                    new_sku=product.sku,
                    changed_at=datetime.now(UTC).replace(tzinfo=None),
                    changed_by_id=None,  # System import, no user
                    change_reason="Imported from Google Sheets SKU_History column",
                    ip_address=None,
                    user_agent="Google Sheets Import Service",
                )
                self.db.add(sku_history)
                logger.debug(
                    f"Added SKU history for {product.sku}: {old_sku} -> {product.sku}"
                )

    async def _auto_map_to_emag(
        self, mapping: GoogleSheetsProductMapping, import_log: ImportLog
    ) -> None:
        """
        Automatically map product to eMAG MAIN and FBE accounts

        Args:
            mapping: Product mapping to update
            import_log: Import log to update statistics
        """
        sku = mapping.local_sku

        # Search for MAIN account product
        main_product = await self._find_emag_product(sku, "main")
        if main_product:
            mapping.emag_main_id = main_product.id
            mapping.emag_main_part_number = main_product.sku
            mapping.emag_main_status = "mapped"
            mapping.mapping_method = "exact_sku"
            mapping.mapping_confidence = 1.0
            import_log.auto_mapped_main += 1
            logger.info(f"Mapped {sku} to MAIN account (ID: {main_product.id})")
        else:
            mapping.emag_main_status = "not_found"
            logger.debug(f"No MAIN account product found for SKU: {sku}")

        # Search for FBE account product
        fbe_product = await self._find_emag_product(sku, "fbe")
        if fbe_product:
            mapping.emag_fbe_id = fbe_product.id
            mapping.emag_fbe_part_number = fbe_product.sku
            mapping.emag_fbe_status = "mapped"
            mapping.mapping_method = "exact_sku"
            mapping.mapping_confidence = 1.0
            import_log.auto_mapped_fbe += 1
            logger.info(f"Mapped {sku} to FBE account (ID: {fbe_product.id})")
        else:
            mapping.emag_fbe_status = "not_found"
            logger.debug(f"No FBE account product found for SKU: {sku}")

        # Update unmapped count
        if not main_product and not fbe_product:
            import_log.unmapped_products += 1

    async def _find_emag_product(
        self, sku: str, account_type: str
    ) -> EmagProductV2 | None:
        """
        Find eMAG product by SKU and account type

        Args:
            sku: Product SKU to search for
            account_type: Account type ('main' or 'fbe')

        Returns:
            Optional[EmagProductV2]: Found product or None
        """
        stmt = (
            select(EmagProductV2)
            .options(
                load_only(
                    EmagProductV2.id,
                    EmagProductV2.sku,
                    EmagProductV2.name,
                    EmagProductV2.account_type,
                    EmagProductV2.part_number_key,
                    EmagProductV2.status,
                )
            )
            .where(
                EmagProductV2.sku == sku,
                EmagProductV2.account_type == account_type,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_emag_matches_by_sku(
        self, sku: str
    ) -> dict[str, dict[str, Any] | None]:
        """Get eMAG product matches for the given SKU across MAIN and FBE accounts."""

        if not sku:
            return {"main": None, "fbe": None}

        matches: dict[str, dict[str, Any] | None] = {"main": None, "fbe": None}

        for account in ("main", "fbe"):
            product = await self._find_emag_product(sku, account)
            if product:
                matches[account] = {
                    "id": str(product.id),
                    "part_number": product.sku,
                    "part_number_key": product.part_number_key,
                    "name": product.name,
                    "account_type": product.account_type,
                    "status": product.status,
                }

        return matches

    async def get_mapping_statistics(self) -> dict:
        """Get statistics about product mappings"""
        # Count total mappings
        total_stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.is_active
        )
        total_result = await self.db.execute(total_stmt)
        total_mappings = len(total_result.scalars().all())

        # Count fully mapped (both MAIN and FBE)
        fully_mapped_stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.is_active,
            GoogleSheetsProductMapping.emag_main_status == "mapped",
            GoogleSheetsProductMapping.emag_fbe_status == "mapped",
        )
        fully_mapped_result = await self.db.execute(fully_mapped_stmt)
        fully_mapped = len(fully_mapped_result.scalars().all())

        # Count MAIN only
        main_only_stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.is_active,
            GoogleSheetsProductMapping.emag_main_status == "mapped",
            GoogleSheetsProductMapping.emag_fbe_status != "mapped",
        )
        main_only_result = await self.db.execute(main_only_stmt)
        main_only = len(main_only_result.scalars().all())

        # Count FBE only
        fbe_only_stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.is_active,
            GoogleSheetsProductMapping.emag_fbe_status == "mapped",
            GoogleSheetsProductMapping.emag_main_status != "mapped",
        )
        fbe_only_result = await self.db.execute(fbe_only_stmt)
        fbe_only = len(fbe_only_result.scalars().all())

        # Count unmapped
        unmapped_stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.is_active,
            GoogleSheetsProductMapping.emag_main_status != "mapped",
            GoogleSheetsProductMapping.emag_fbe_status != "mapped",
        )
        unmapped_result = await self.db.execute(unmapped_stmt)
        unmapped = len(unmapped_result.scalars().all())

        return {
            "total_products": total_mappings,
            "fully_mapped": fully_mapped,
            "main_only": main_only,
            "fbe_only": fbe_only,
            "unmapped": unmapped,
            "mapping_percentage": (
                (fully_mapped / total_mappings * 100) if total_mappings > 0 else 0
            ),
        }

    async def remap_unmapped_products(
        self,
        limit: int = 100,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Attempt to remap unmapped products using SKU lookups."""

        base_unmapped_stmt = (
            select(GoogleSheetsProductMapping)
            .where(GoogleSheetsProductMapping.is_active)
            .where(
                or_(
                    GoogleSheetsProductMapping.emag_main_status != "mapped",
                    GoogleSheetsProductMapping.emag_fbe_status != "mapped",
                )
            )
        )
        base_unmapped_result = await self.db.execute(base_unmapped_stmt)
        unmapped_before = list(base_unmapped_result.scalars().all())

        candidates = unmapped_before[:limit]

        summary = {
            "processed": len(candidates),
            "updated": 0,
            "mapped_main": 0,
            "mapped_fbe": 0,
            "still_unmapped": 0,
        }

        if not candidates:
            summary["still_unmapped"] = len(unmapped_before)
            return summary

        remaining_after_processed = 0

        for mapping in candidates:
            sku = mapping.local_sku
            current_main_status = mapping.emag_main_status
            current_fbe_status = mapping.emag_fbe_status

            main_product = await self._find_emag_product(sku, "main")
            fbe_product = await self._find_emag_product(sku, "fbe")

            main_match = main_product is not None
            fbe_match = fbe_product is not None

            if main_match:
                summary["mapped_main"] += 1
            if fbe_match:
                summary["mapped_fbe"] += 1

            would_main_status = "mapped" if main_match else "not_found"
            would_fbe_status = "mapped" if fbe_match else "not_found"

            will_change = (
                (current_main_status or "") != would_main_status
                or (current_fbe_status or "") != would_fbe_status
                or (not main_match and mapping.emag_main_id is not None)
                or (main_match and mapping.emag_main_id != main_product.id)
                or (not fbe_match and mapping.emag_fbe_id is not None)
                or (fbe_match and mapping.emag_fbe_id != fbe_product.id)
                or (main_match and mapping.emag_main_part_number != main_product.sku)
                or (fbe_match and mapping.emag_fbe_part_number != fbe_product.sku)
            )

            if will_change:
                summary["updated"] += 1

            if not dry_run:
                if main_match:
                    mapping.emag_main_id = main_product.id
                    mapping.emag_main_part_number = main_product.sku
                    mapping.emag_main_status = "mapped"
                else:
                    mapping.emag_main_id = None
                    mapping.emag_main_part_number = None
                    mapping.emag_main_status = "not_found"

                if fbe_match:
                    mapping.emag_fbe_id = fbe_product.id
                    mapping.emag_fbe_part_number = fbe_product.sku
                    mapping.emag_fbe_status = "mapped"
                else:
                    mapping.emag_fbe_id = None
                    mapping.emag_fbe_part_number = None
                    mapping.emag_fbe_status = "not_found"

                mapping.mapping_method = "auto_remap"
                mapping.is_verified = False

            if not (main_match and fbe_match):
                remaining_after_processed += 1

        if not dry_run:
            await self.db.commit()
            remaining_result = await self.db.execute(base_unmapped_stmt)
            summary["still_unmapped"] = len(remaining_result.scalars().all())
        else:
            other_unmapped = max(len(unmapped_before) - len(candidates), 0)
            summary["still_unmapped"] = remaining_after_processed + other_unmapped

        return summary

    async def get_all_mappings(
        self, skip: int = 0, limit: int = 100, filter_status: str | None = None
    ) -> tuple[list[GoogleSheetsProductMapping], int]:
        """
        Get all product mappings with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filter_status: Filter by mapping status
                (fully_mapped, partially_mapped, unmapped, conflict)

        Returns:
            Tuple of (list of mappings, total count)
        """
        # Build base query
        stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.is_active
        )

        # Apply filters
        if filter_status == "fully_mapped":
            stmt = stmt.where(
                GoogleSheetsProductMapping.emag_main_status == "mapped",
                GoogleSheetsProductMapping.emag_fbe_status == "mapped",
            )
        elif filter_status == "partially_mapped":
            stmt = stmt.where(
                (GoogleSheetsProductMapping.emag_main_status == "mapped")
                | (GoogleSheetsProductMapping.emag_fbe_status == "mapped")
            ).where(
                ~(
                    (GoogleSheetsProductMapping.emag_main_status == "mapped")
                    & (GoogleSheetsProductMapping.emag_fbe_status == "mapped")
                )
            )
        elif filter_status == "unmapped":
            stmt = stmt.where(
                GoogleSheetsProductMapping.emag_main_status != "mapped",
                GoogleSheetsProductMapping.emag_fbe_status != "mapped",
            )
        elif filter_status == "conflict":
            stmt = stmt.where(GoogleSheetsProductMapping.has_conflicts)

        # Get total count
        count_result = await self.db.execute(stmt)
        total = len(count_result.scalars().all())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        mappings = result.scalars().all()

        return list(mappings), total

    async def manual_map_product(
        self,
        local_sku: str,
        emag_main_id: int | None = None,
        emag_fbe_id: int | None = None,
        notes: str | None = None,
    ) -> GoogleSheetsProductMapping:
        """
        Manually map a product to eMAG accounts

        Args:
            local_sku: Local product SKU
            emag_main_id: eMAG MAIN product ID
            emag_fbe_id: eMAG FBE product ID
            notes: Optional notes about the mapping

        Returns:
            GoogleSheetsProductMapping: Updated mapping
        """
        # Get mapping
        stmt = select(GoogleSheetsProductMapping).where(
            GoogleSheetsProductMapping.local_sku == local_sku
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if not mapping:
            raise ValueError(f"No mapping found for SKU: {local_sku}")

        # Update MAIN mapping
        if emag_main_id:
            main_product = await self.db.get(EmagProductV2, emag_main_id)
            if main_product and main_product.account_type == "main":
                mapping.emag_main_id = emag_main_id
                mapping.emag_main_part_number = main_product.sku
                mapping.emag_main_status = "mapped"
            else:
                raise ValueError(f"Invalid MAIN product ID: {emag_main_id}")

        # Update FBE mapping
        if emag_fbe_id:
            fbe_product = await self.db.get(EmagProductV2, emag_fbe_id)
            if fbe_product and fbe_product.account_type == "fbe":
                mapping.emag_fbe_id = emag_fbe_id
                mapping.emag_fbe_part_number = fbe_product.sku
                mapping.emag_fbe_status = "mapped"
            else:
                raise ValueError(f"Invalid FBE product ID: {emag_fbe_id}")

        # Update metadata
        mapping.mapping_method = "manual"
        mapping.is_verified = True
        if notes:
            mapping.notes = notes

        await self.db.commit()
        await self.db.refresh(mapping)

        return mapping

    async def _import_suppliers(
        self, user_email: str | None = None
    ) -> dict[str, int]:
        """
        Import suppliers from Google Sheets Product_Suppliers tab

        Args:
            user_email: Email of user initiating import

        Returns:
            Dict with import statistics
        """
        logger.info("Fetching suppliers from Google Sheets Product_Suppliers tab...")
        sheet_suppliers = self.sheets_service.get_all_suppliers()

        stats = {
            "total_suppliers": len(sheet_suppliers),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "suppliers_created_in_db": 0,
        }

        logger.info(f"Found {len(sheet_suppliers)} supplier entries in Google Sheets")

        # Get current exchange rate (CNY to RON) - you can make this configurable
        # For now, using a reasonable default rate
        exchange_rate_cny_ron = 0.65  # 1 CNY = ~0.65 RON (update as needed)

        for sheet_supplier in sheet_suppliers:
            # Use nested transaction (savepoint) for each supplier
            async with self.db.begin_nested():
                try:
                    # First, ensure the supplier exists in the suppliers table
                    await self._ensure_supplier_exists(
                        supplier_name=sheet_supplier.supplier_name,
                        supplier_contact=sheet_supplier.supplier_contact,
                        supplier_url=sheet_supplier.supplier_url,
                        stats=stats,
                    )

                    # Use upsert (ON CONFLICT UPDATE) for better performance and avoid duplicates
                    from sqlalchemy.dialects.postgresql import insert

                    # Get current time as timezone-naive (matching database schema)
                    now_naive = datetime.now(UTC).replace(tzinfo=None)

                    values = {
                        "sku": sheet_supplier.sku,
                        "supplier_name": sheet_supplier.supplier_name,
                        "price_cny": sheet_supplier.price_cny,
                        "supplier_contact": sheet_supplier.supplier_contact,
                        "supplier_url": sheet_supplier.supplier_url,
                        "supplier_notes": sheet_supplier.supplier_notes,
                        "supplier_product_chinese_name": (
                            sheet_supplier.supplier_product_chinese_name
                        ),
                        "supplier_product_specification": (
                            sheet_supplier.supplier_product_specification
                        ),
                        "google_sheet_row": sheet_supplier.row_number,
                        "last_imported_at": datetime.now(UTC),
                        "import_source": "google_sheets",
                        "exchange_rate_cny_ron": exchange_rate_cny_ron,
                        "calculated_price_ron": sheet_supplier.price_cny
                        * exchange_rate_cny_ron,
                        "is_active": True,
                        "created_at": now_naive,
                        "updated_at": now_naive,
                    }

                    # Check if exists first (for stats tracking)
                    check_stmt = select(ProductSupplierSheet.id).where(
                        ProductSupplierSheet.sku == sheet_supplier.sku,
                        ProductSupplierSheet.supplier_name == sheet_supplier.supplier_name,
                    )
                    check_result = await self.db.execute(check_stmt)
                    exists = check_result.scalar_one_or_none() is not None

                    # Insert with ON CONFLICT UPDATE (upsert)
                    insert_stmt = insert(ProductSupplierSheet).values(**values)
                    upsert_stmt = insert_stmt.on_conflict_do_update(
                        constraint="uq_product_supplier_sku_name",
                        set_={
                            "price_cny": insert_stmt.excluded.price_cny,
                            "supplier_contact": insert_stmt.excluded.supplier_contact,
                            "supplier_url": insert_stmt.excluded.supplier_url,
                            "supplier_notes": insert_stmt.excluded.supplier_notes,
                            "supplier_product_chinese_name": (
                                insert_stmt.excluded.supplier_product_chinese_name
                            ),
                            "supplier_product_specification": (
                                insert_stmt.excluded.supplier_product_specification
                            ),
                            "google_sheet_row": insert_stmt.excluded.google_sheet_row,
                            "last_imported_at": insert_stmt.excluded.last_imported_at,
                            "exchange_rate_cny_ron": insert_stmt.excluded.exchange_rate_cny_ron,
                            "calculated_price_ron": insert_stmt.excluded.calculated_price_ron,
                            "updated_at": insert_stmt.excluded.updated_at,
                        },
                    )

                    await self.db.execute(upsert_stmt)

                    # Update stats based on whether it existed
                    if exists:
                        stats["updated"] += 1
                        logger.debug(
                            f"Updated supplier {sheet_supplier.supplier_name} "
                            f"for SKU {sheet_supplier.sku}"
                        )
                    else:
                        stats["created"] += 1
                        logger.debug(
                            f"Created supplier {sheet_supplier.supplier_name} "
                            f"for SKU {sheet_supplier.sku}"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to import supplier {sheet_supplier.supplier_name} "
                        f"for SKU {sheet_supplier.sku}: {e}",
                        exc_info=True,
                    )
                    stats["skipped"] += 1
                    # Rollback happens automatically when exiting nested context
                    continue

        await self.db.flush()

        logger.info("=" * 80)
        logger.info("Supplier Import Summary:")
        logger.info(f"  Total supplier entries: {stats['total_suppliers']}")
        logger.info(f"  Created in product_supplier_sheets: {stats['created']}")
        logger.info(f"  Updated in product_supplier_sheets: {stats['updated']}")
        logger.info(f"  Skipped (errors): {stats['skipped']}")
        logger.info(
            f"  New suppliers created in suppliers table: {stats['suppliers_created_in_db']}"
        )
        logger.info(f"  Exchange rate used: 1 CNY = {exchange_rate_cny_ron} RON")

        if stats["suppliers_created_in_db"] > 0:
            logger.info(
                f"  ✓ {stats['suppliers_created_in_db']} new suppliers added to database"
            )

        logger.info("=" * 80)

        # Migrate to supplier_products table using dedicated service
        logger.info("Migrating to supplier_products table...")
        from app.services.suppliers.supplier_migration_service import (
            SupplierMigrationService,
        )

        migration_service = SupplierMigrationService(self.db)
        migration_stats = await migration_service.migrate_all()
        logger.info(f"  Migrated: {migration_stats['migrated']} products")
        logger.info(
            f"  Skipped: {migration_stats['skipped']} (already exist or no product match)"
        )
        logger.info("=" * 80)

        return stats

    async def _ensure_supplier_exists(
        self,
        supplier_name: str,
        supplier_contact: str | None = None,
        supplier_url: str | None = None,
        stats: dict[str, int] | None = None,
    ) -> Supplier:
        """
        Ensure supplier exists in suppliers table, create if not exists

        Args:
            supplier_name: Name of the supplier
            supplier_contact: Contact information
            supplier_url: Supplier website/product URL
            stats: Statistics dict to update

        Returns:
            Supplier: The supplier record
        """
        # Check if supplier exists
        stmt = select(Supplier).where(Supplier.name == supplier_name)
        result = await self.db.execute(stmt)
        supplier = result.scalar_one_or_none()

        if not supplier:
            # Create new supplier
            logger.info(f"Creating new supplier: {supplier_name}")

            # Truncate URL if too long (max 500 chars for website column)
            truncated_url = (
                supplier_url[:500]
                if supplier_url and len(supplier_url) > 500
                else supplier_url
            )
            if supplier_url and len(supplier_url) > 500:
                logger.warning(
                    f"Truncated URL for supplier {supplier_name}: {len(supplier_url)} -> 500 chars"
                )

            supplier = Supplier(
                name=supplier_name,
                country="China",  # Default for Google Sheets suppliers
                email=supplier_contact
                if supplier_contact and "@" in supplier_contact
                else None,
                phone=supplier_contact
                if supplier_contact and "@" not in supplier_contact
                else None,
                website=truncated_url,
                currency="CNY",
                is_active=True,
                rating=5.0,
                quality_score=5.0,
            )
            self.db.add(supplier)
            await self.db.flush()

            if stats:
                stats["suppliers_created_in_db"] += 1

            logger.info(
                f"✓ Successfully created supplier: {supplier_name} (ID: {supplier.id})"
            )
        else:
            logger.debug(
                f"Supplier already exists: {supplier_name} (ID: {supplier.id})"
            )

        return supplier

    async def get_suppliers_for_sku(self, sku: str) -> list[ProductSupplierSheet]:
        """
        Get all suppliers for a specific SKU

        Args:
            sku: Product SKU

        Returns:
            List of suppliers for the SKU
        """
        stmt = (
            select(ProductSupplierSheet)
            .where(ProductSupplierSheet.sku == sku, ProductSupplierSheet.is_active)
            .order_by(
                ProductSupplierSheet.is_preferred.desc(),
                ProductSupplierSheet.price_cny.asc(),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_supplier_statistics(self) -> dict[str, Any]:
        """
        Get statistics about imported suppliers

        Returns:
            Dict with supplier statistics
        """
        # Count total suppliers
        total_stmt = select(ProductSupplierSheet).where(ProductSupplierSheet.is_active)
        total_result = await self.db.execute(total_stmt)
        total_suppliers = len(total_result.scalars().all())

        # Count unique SKUs with suppliers
        unique_skus_stmt = (
            select(ProductSupplierSheet.sku)
            .distinct()
            .where(ProductSupplierSheet.is_active)
        )
        unique_skus_result = await self.db.execute(unique_skus_stmt)
        unique_skus = len(unique_skus_result.scalars().all())

        # Count unique supplier names
        unique_names_stmt = (
            select(ProductSupplierSheet.supplier_name)
            .distinct()
            .where(ProductSupplierSheet.is_active)
        )
        unique_names_result = await self.db.execute(unique_names_stmt)
        unique_supplier_names = len(unique_names_result.scalars().all())

        # Calculate average suppliers per SKU
        avg_suppliers = total_suppliers / unique_skus if unique_skus > 0 else 0

        return {
            "total_supplier_entries": total_suppliers,
            "unique_skus_with_suppliers": unique_skus,
            "unique_supplier_names": unique_supplier_names,
            "avg_suppliers_per_sku": round(avg_suppliers, 2),
        }

    async def get_all_supplier_products(
        self,
        skip: int = 0,
        limit: int = 100,
        sku: str | None = None,
        supplier_name: str | None = None,
    ) -> list[ProductSupplierSheet]:
        """
        Get all supplier products with pagination and filters

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            sku: Optional SKU filter
            supplier_name: Optional supplier name filter

        Returns:
            List of ProductSupplierSheet records
        """
        stmt = select(ProductSupplierSheet).where(ProductSupplierSheet.is_active)

        if sku:
            stmt = stmt.where(ProductSupplierSheet.sku.ilike(f"%{sku}%"))

        if supplier_name:
            stmt = stmt.where(
                ProductSupplierSheet.supplier_name.ilike(f"%{supplier_name}%")
            )

        stmt = (
            stmt.order_by(ProductSupplierSheet.sku, ProductSupplierSheet.price_cny)
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_supplier_products(
        self, sku: str | None = None, supplier_name: str | None = None
    ) -> int:
        """
        Count supplier products with filters

        Args:
            sku: Optional SKU filter
            supplier_name: Optional supplier name filter

        Returns:
            Total count of matching records
        """
        from sqlalchemy import func

        stmt = select(func.count(ProductSupplierSheet.id)).where(
            ProductSupplierSheet.is_active
        )

        if sku:
            stmt = stmt.where(ProductSupplierSheet.sku.ilike(f"%{sku}%"))

        if supplier_name:
            stmt = stmt.where(
                ProductSupplierSheet.supplier_name.ilike(f"%{supplier_name}%")
            )

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_import_history(self, limit: int = 10) -> list[ImportLog]:
        """
        Get recent import history

        Args:
            limit: Maximum number of records to return

        Returns:
            List of import logs
        """
        stmt = select(ImportLog).order_by(ImportLog.started_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
