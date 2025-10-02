"""
Product Import Service for MagFlow ERP
Handles importing products from Google Sheets and mapping to eMAG accounts
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models.emag_models import EmagProductV2
from app.models.product_mapping import ImportLog, ProductMapping
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
        user_email: Optional[str] = None,
        auto_map: bool = True
    ) -> ImportLog:
        """
        Import products from Google Sheets and optionally auto-map to eMAG
        
        Args:
            user_email: Email of user initiating import
            auto_map: Whether to automatically map products to eMAG accounts
            
        Returns:
            ImportLog: Log of the import operation
        """
        # Create import log
        import_log = ImportLog(
            import_type="google_sheets",
            source_name=self.sheets_service.config.sheet_name,
            status="in_progress",
            initiated_by=user_email,
            started_at=datetime.utcnow()
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

            # Process each product
            for sheet_product in sheet_products:
                sku = sheet_product.sku
                if not sku:
                    logger.warning("Skipping product without SKU: %s", sheet_product)
                    import_log.skipped_rows += 1
                    continue

                if sku in processed_skus:
                    logger.debug("Duplicate SKU '%s' detected in sheet. Skipping subsequent occurrence.", sku)
                    import_log.skipped_rows += 1
                    continue

                processed_skus.add(sku)
                try:
                    await self._import_single_product(
                        sheet_product,
                        import_log,
                        auto_map
                    )
                    import_log.successful_imports += 1
                except Exception as e:
                    logger.error(f"Failed to import product {sheet_product.sku}: {e}")
                    import_log.failed_imports += 1
                    await self.db.rollback()
                    # Re-attach the import log to the session after rollback
                    self.db.add(import_log)
            
            # Complete import
            import_log.status = "completed"
            import_log.completed_at = datetime.utcnow()
            import_log.duration_seconds = (
                import_log.completed_at - import_log.started_at
            ).total_seconds()
            
            await self.db.commit()
            
            logger.info(
                f"Import completed: {import_log.successful_imports} successful, "
                f"{import_log.failed_imports} failed"
            )
            
            return import_log
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            import_log.status = "failed"
            import_log.error_message = str(e)
            import_log.completed_at = datetime.utcnow()
            await self.db.commit()
            raise
    
    async def _import_single_product(
        self,
        sheet_product: ProductFromSheet,
        import_log: ImportLog,
        auto_map: bool
    ) -> ProductMapping:
        """
        Import a single product and create/update mapping
        
        Args:
            sheet_product: Product data from Google Sheets
            import_log: Import log to update statistics
            auto_map: Whether to automatically map to eMAG
            
        Returns:
            ProductMapping: Created or updated mapping
        """
        # Check if mapping already exists
        stmt = select(ProductMapping).where(
            ProductMapping.local_sku == sheet_product.sku
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        
        if mapping:
            # Update existing mapping
            mapping.local_product_name = sheet_product.romanian_name
            mapping.local_price = sheet_product.emag_fbe_ro_price_ron
            mapping.google_sheet_row = sheet_product.row_number
            mapping.google_sheet_data = json.dumps(sheet_product.raw_data)
            mapping.last_imported_at = datetime.utcnow()
            mapping.import_source = "google_sheets"
        else:
            # Create new mapping
            mapping = ProductMapping(
                local_sku=sheet_product.sku,
                local_product_name=sheet_product.romanian_name,
                local_price=sheet_product.emag_fbe_ro_price_ron,
                google_sheet_row=sheet_product.row_number,
                google_sheet_data=json.dumps(sheet_product.raw_data),
                last_imported_at=datetime.utcnow(),
                import_source="google_sheets",
                is_active=True
            )
            self.db.add(mapping)
        
        # Auto-map to eMAG if requested
        if auto_map:
            await self._auto_map_to_emag(mapping, import_log)
        
        await self.db.flush()
        return mapping
    
    async def _auto_map_to_emag(
        self,
        mapping: ProductMapping,
        import_log: ImportLog
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
        self,
        sku: str,
        account_type: str
    ) -> Optional[EmagProductV2]:
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

    async def get_emag_matches_by_sku(self, sku: str) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get eMAG product matches for the given SKU across MAIN and FBE accounts."""

        if not sku:
            return {"main": None, "fbe": None}

        matches: Dict[str, Optional[Dict[str, Any]]] = {"main": None, "fbe": None}

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

    async def get_mapping_statistics(self) -> Dict:
        """Get statistics about product mappings"""
        # Count total mappings
        total_stmt = select(ProductMapping).where(ProductMapping.is_active)
        total_result = await self.db.execute(total_stmt)
        total_mappings = len(total_result.scalars().all())

        # Count fully mapped (both MAIN and FBE)
        fully_mapped_stmt = select(ProductMapping).where(
            ProductMapping.is_active,
            ProductMapping.emag_main_status == "mapped",
            ProductMapping.emag_fbe_status == "mapped"
        )
        fully_mapped_result = await self.db.execute(fully_mapped_stmt)
        fully_mapped = len(fully_mapped_result.scalars().all())
        
        # Count MAIN only
        main_only_stmt = select(ProductMapping).where(
            ProductMapping.is_active,
            ProductMapping.emag_main_status == "mapped",
            ProductMapping.emag_fbe_status != "mapped"
        )
        main_only_result = await self.db.execute(main_only_stmt)
        main_only = len(main_only_result.scalars().all())
        
        # Count FBE only
        fbe_only_stmt = select(ProductMapping).where(
            ProductMapping.is_active,
            ProductMapping.emag_fbe_status == "mapped",
            ProductMapping.emag_main_status != "mapped"
        )
        fbe_only_result = await self.db.execute(fbe_only_stmt)
        fbe_only = len(fbe_only_result.scalars().all())
        
        # Count unmapped
        unmapped_stmt = select(ProductMapping).where(
            ProductMapping.is_active,
            ProductMapping.emag_main_status != "mapped",
            ProductMapping.emag_fbe_status != "mapped",
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
    ) -> Dict[str, Any]:
        """Attempt to remap unmapped products using SKU lookups."""

        base_unmapped_stmt = (
            select(ProductMapping)
            .where(ProductMapping.is_active)
            .where(
                or_(
                    ProductMapping.emag_main_status != "mapped",
                    ProductMapping.emag_fbe_status != "mapped",
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
                or (
                    not main_match
                    and mapping.emag_main_id is not None
                )
                or (
                    main_match
                    and mapping.emag_main_id != main_product.id
                )
                or (
                    not fbe_match
                    and mapping.emag_fbe_id is not None
                )
                or (
                    fbe_match
                    and mapping.emag_fbe_id != fbe_product.id
                )
                or (
                    main_match
                    and mapping.emag_main_part_number != main_product.sku
                )
                or (
                    fbe_match
                    and mapping.emag_fbe_part_number != fbe_product.sku
                )
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
        self,
        skip: int = 0,
        limit: int = 100,
        filter_status: Optional[str] = None
    ) -> Tuple[List[ProductMapping], int]:
        """
        Get all product mappings with pagination
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filter_status: Filter by mapping status (fully_mapped, partially_mapped, unmapped, conflict)
            
        Returns:
            Tuple of (list of mappings, total count)
        """
        # Build base query
        stmt = select(ProductMapping).where(ProductMapping.is_active)
        
        # Apply filters
        if filter_status == "fully_mapped":
            stmt = stmt.where(
                ProductMapping.emag_main_status == "mapped",
                ProductMapping.emag_fbe_status == "mapped"
            )
        elif filter_status == "partially_mapped":
            stmt = stmt.where(
                (ProductMapping.emag_main_status == "mapped") |
                (ProductMapping.emag_fbe_status == "mapped")
            ).where(
                ~((ProductMapping.emag_main_status == "mapped") &
                  (ProductMapping.emag_fbe_status == "mapped"))
            )
        elif filter_status == "unmapped":
            stmt = stmt.where(
                ProductMapping.emag_main_status != "mapped",
                ProductMapping.emag_fbe_status != "mapped"
            )
        elif filter_status == "conflict":
            stmt = stmt.where(ProductMapping.has_conflicts)
        
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
        emag_main_id: Optional[int] = None,
        emag_fbe_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> ProductMapping:
        """
        Manually map a product to eMAG accounts
        
        Args:
            local_sku: Local product SKU
            emag_main_id: eMAG MAIN product ID
            emag_fbe_id: eMAG FBE product ID
            notes: Optional notes about the mapping
            
        Returns:
            ProductMapping: Updated mapping
        """
        # Get mapping
        stmt = select(ProductMapping).where(ProductMapping.local_sku == local_sku)
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
    
    async def get_import_history(
        self,
        limit: int = 10
    ) -> List[ImportLog]:
        """
        Get recent import history
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of import logs
        """
        stmt = select(ImportLog).order_by(
            ImportLog.started_at.desc()
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
