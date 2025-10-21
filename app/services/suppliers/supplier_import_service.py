"""Service for importing supplier products from Excel files.

Handles the import of scraped 1688.com product data from Excel files with:
- Chinese product names
- Prices in CNY
- Product URLs
- Image URLs
"""

import uuid
from datetime import UTC, datetime
from io import BytesIO

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier
from app.models.supplier_matching import MatchingStatus, SupplierRawProduct


class SupplierImportService:
    """Service for importing supplier product data from Excel files."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def import_from_excel(
        self,
        file_content: bytes,
        supplier_id: int,
        column_mapping: dict[str, str] | None = None,
    ) -> dict:
        """Import products from Excel file.

        Args:
            file_content: Excel file content as bytes
            supplier_id: ID of the supplier
            column_mapping: Optional mapping of Excel columns to expected fields
                Default mapping:
                {
                    "chinese_name": "Nume produs",
                    "price_cny": "Pret CNY",
                    "product_url": "URL produs",
                    "image_url": "URL imagine"
                }

        Returns:
            Dict with import statistics
        """
        # Verify supplier exists
        supplier = await self._get_supplier(supplier_id)
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        # Default column mapping
        if column_mapping is None:
            column_mapping = {
                "chinese_name": "Nume produs",
                "price_cny": "Pret CNY",
                "product_url": "URL produs",
                "image_url": "URL imagine",
            }

        # Read Excel file
        try:
            df = pd.read_excel(BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {str(e)}") from e

        # Validate columns
        missing_columns = []
        for expected_col in column_mapping.values():
            if expected_col not in df.columns:
                missing_columns.append(expected_col)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {', '.join(missing_columns)}. "
                f"Available columns: {', '.join(df.columns)}"
            )

        # Generate batch ID for this import
        batch_id = f"import_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Import products
        imported_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                # Extract data
                chinese_name = str(row[column_mapping["chinese_name"]]).strip()
                price_cny = float(row[column_mapping["price_cny"]])
                product_url = str(row[column_mapping["product_url"]]).strip()
                image_url = str(row[column_mapping["image_url"]]).strip()

                # Validate required fields
                if not chinese_name or not product_url:
                    skipped_count += 1
                    continue

                if price_cny <= 0:
                    skipped_count += 1
                    continue

                # Check for duplicates (same supplier + URL)
                existing = await self._check_duplicate(supplier_id, product_url)
                if existing:
                    # Update price if changed
                    if existing.price_cny != price_cny:
                        existing.price_cny = price_cny
                        existing.last_price_check = datetime.now(UTC)
                    skipped_count += 1
                    continue

                # Create new product
                product = SupplierRawProduct(
                    supplier_id=supplier_id,
                    chinese_name=chinese_name,
                    price_cny=price_cny,
                    product_url=product_url,
                    image_url=image_url,
                    import_batch_id=batch_id,
                    import_date=datetime.now(UTC),
                    matching_status=MatchingStatus.PENDING,
                    is_active=True,
                )

                self.db.add(product)
                imported_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Row {idx + 2}: {str(e)}")

        # Commit transaction
        await self.db.commit()

        return {
            "success": True,
            "batch_id": batch_id,
            "supplier_id": supplier_id,
            "supplier_name": supplier.name,
            "total_rows": len(df),
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors[:10] if errors else [],  # First 10 errors
        }

    async def import_from_dataframe(
        self, df: pd.DataFrame, supplier_id: int, batch_id: str | None = None
    ) -> dict:
        """Import products from pandas DataFrame.

        Expected columns: chinese_name, price_cny, product_url, image_url
        """
        supplier = await self._get_supplier(supplier_id)
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        if batch_id is None:
            batch_id = (
                "import_"
                f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
                f"_{uuid.uuid4().hex[:8]}"
            )

        imported_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            try:
                # Check for duplicates
                existing = await self._check_duplicate(supplier_id, row["product_url"])

                if existing:
                    if existing.price_cny != row["price_cny"]:
                        existing.price_cny = row["price_cny"]
                        existing.last_price_check = datetime.now(UTC)
                    skipped_count += 1
                    continue

                # Create new product
                product = SupplierRawProduct(
                    supplier_id=supplier_id,
                    chinese_name=row["chinese_name"],
                    price_cny=row["price_cny"],
                    product_url=row["product_url"],
                    image_url=row["image_url"],
                    import_batch_id=batch_id,
                    import_date=datetime.now(UTC),
                    matching_status=MatchingStatus.PENDING,
                    is_active=True,
                )

                self.db.add(product)
                imported_count += 1

            except Exception:
                skipped_count += 1

        await self.db.commit()

        return {
            "success": True,
            "batch_id": batch_id,
            "imported": imported_count,
            "skipped": skipped_count,
        }

    async def get_import_statistics(self, batch_id: str) -> dict:
        """Get statistics for an import batch."""

        stmt = select(SupplierRawProduct).where(
            SupplierRawProduct.import_batch_id == batch_id
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        if not products:
            return {"error": "Batch not found"}

        # Calculate statistics
        total = len(products)
        matched = sum(
            1 for p in products if p.matching_status != MatchingStatus.PENDING
        )
        pending = total - matched

        prices = [p.price_cny for p in products]

        return {
            "batch_id": batch_id,
            "total_products": total,
            "matched": matched,
            "pending": pending,
            "supplier_id": products[0].supplier_id,
            "import_date": products[0].import_date,
            "price_stats": {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
            },
        }

    async def _get_supplier(self, supplier_id: int) -> Supplier | None:
        """Get supplier by ID."""
        stmt = select(Supplier).where(Supplier.id == supplier_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _check_duplicate(
        self, supplier_id: int, product_url: str
    ) -> SupplierRawProduct | None:
        """Check if product already exists."""
        stmt = select(SupplierRawProduct).where(
            SupplierRawProduct.supplier_id == supplier_id,
            SupplierRawProduct.product_url == product_url,
            SupplierRawProduct.is_active,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_supplier_products_summary(self) -> list[dict]:
        """Get summary of products per supplier."""

        stmt = select(Supplier).where(Supplier.is_active)
        result = await self.db.execute(stmt)
        suppliers = result.scalars().all()

        summary = []
        for supplier in suppliers:
            # Count products
            count_stmt = select(SupplierRawProduct).where(
                SupplierRawProduct.supplier_id == supplier.id,
                SupplierRawProduct.is_active,
            )
            count_result = await self.db.execute(count_stmt)
            products = count_result.scalars().all()

            if not products:
                continue

            # Calculate statistics
            prices = [p.price_cny for p in products]
            matched = sum(
                1 for p in products if p.matching_status != MatchingStatus.PENDING
            )

            summary.append(
                {
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name,
                    "total_products": len(products),
                    "matched_products": matched,
                    "pending_products": len(products) - matched,
                    "avg_price_cny": sum(prices) / len(prices),
                    "min_price_cny": min(prices),
                    "max_price_cny": max(prices),
                }
            )

        return summary

    async def delete_import_batch(self, batch_id: str) -> dict:
        """Delete all products from an import batch."""

        stmt = select(SupplierRawProduct).where(
            SupplierRawProduct.import_batch_id == batch_id
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        if not products:
            return {"error": "Batch not found"}

        count = len(products)

        for product in products:
            await self.db.delete(product)

        await self.db.commit()

        return {"success": True, "batch_id": batch_id, "deleted_count": count}
