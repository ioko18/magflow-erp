"""
Google Sheets Service for MagFlow ERP
Handles authentication and data retrieval from Google Sheets
"""

import logging
from typing import Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class GoogleSheetsConfig(BaseModel):
    """Configuration for Google Sheets integration"""

    sheet_name: str = "eMAG Stock"
    products_sheet_tab: str = "Products"
    suppliers_sheet_tab: str = "Product_Suppliers"
    service_account_file: str = "service_account.json"
    scopes: list[str] = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]


class ProductFromSheet(BaseModel):
    """Product data structure from Google Sheets

    Required fields:
    - sku: Product SKU (only required field)

    Optional fields (if missing, fallback values are used):
    - romanian_name: Product name (defaults to SKU if empty)
    - All other fields are optional
    """

    sku: str
    romanian_name: str  # Will be set to SKU if empty
    emag_fbe_ro_price_ron: float | None = None
    sort_product: int | None = None
    image_url: str | None = None
    brand: str | None = None
    ean: str | None = None
    weight_kg: float | None = None
    row_number: int
    raw_data: dict[str, Any] = {}


class SupplierFromSheet(BaseModel):
    """Supplier data structure from Google Sheets Product_Suppliers tab

    Required fields:
    - sku: Product SKU reference
    - supplier_name: Name of the supplier
    - price_cny: Price in Chinese Yuan

    Optional fields:
    - supplier_contact: Contact information
    - supplier_url: Product URL (e.g., 1688.com)
    - supplier_notes: Additional notes
    - supplier_product_chinese_name: Product name in Chinese from supplier
    """

    sku: str
    supplier_name: str
    price_cny: float
    supplier_contact: str | None = None
    supplier_url: str | None = None
    supplier_notes: str | None = None
    supplier_product_chinese_name: str | None = None
    supplier_product_specification: str | None = None
    row_number: int
    raw_data: dict[str, Any] = {}


class GoogleSheetsService:
    """Service for interacting with Google Sheets"""

    def __init__(self, config: GoogleSheetsConfig | None = None):
        """Initialize Google Sheets service"""
        self.config = config or GoogleSheetsConfig()
        self._client = None
        self._spreadsheet = None

    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API

        Returns:
            bool: True if authentication successful
        """
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.config.service_account_file, self.config.scopes
            )
            self._client = gspread.authorize(creds)
            logger.info("Successfully authenticated with Google Sheets API")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            return False

    def open_spreadsheet(self) -> bool:
        """
        Open the configured spreadsheet

        Returns:
            bool: True if spreadsheet opened successfully
        """
        try:
            if not self._client and not self.authenticate():
                return False

            self._spreadsheet = self._client.open(self.config.sheet_name)
            logger.info(f"Successfully opened spreadsheet: {self.config.sheet_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to open spreadsheet: {e}")
            return False

    def get_products_worksheet(self):
        """Get the products worksheet"""
        if not self._spreadsheet and not self.open_spreadsheet():
            raise Exception("Failed to open spreadsheet")

        return self._spreadsheet.worksheet(self.config.products_sheet_tab)

    def get_suppliers_worksheet(self):
        """Get the suppliers worksheet"""
        if not self._spreadsheet and not self.open_spreadsheet():
            raise Exception("Failed to open spreadsheet")

        return self._spreadsheet.worksheet(self.config.suppliers_sheet_tab)

    def get_all_products(self) -> list[ProductFromSheet]:
        """
        Retrieve all products from Google Sheets

        Returns:
            List[ProductFromSheet]: List of products from the sheet
        """
        try:
            worksheet = self.get_products_worksheet()

            # Get all records as dictionaries
            records = worksheet.get_all_records()

            # Statistics tracking
            total_rows = len(records)
            skipped_no_sku = 0
            skipped_errors = 0
            products_with_fallback_name = 0

            products = []
            for idx, record in enumerate(
                records, start=2
            ):  # Start at 2 (row 1 is header)
                try:
                    # Extract required fields
                    sku = str(record.get("SKU", "")).strip()
                    romanian_name = str(record.get("Romanian_Name", "")).strip()

                    # Only SKU is required
                    if not sku:
                        logger.warning(f"Skipping row {idx}: Missing SKU (required)")
                        skipped_no_sku += 1
                        continue

                    # If Romanian_Name is missing, use SKU as fallback
                    if not romanian_name:
                        romanian_name = sku
                        products_with_fallback_name += 1
                        logger.debug(
                            f"Row {idx}: Using SKU '{sku}' as product name (Romanian_Name is empty)"
                        )

                    # Parse price
                    price_str = str(record.get("Emag_FBE_RO_Price_RON", "")).strip()
                    price = None
                    if price_str:
                        try:
                            price = float(price_str)
                        except ValueError:
                            logger.warning(
                                f"Invalid price format in row {idx}: {price_str}"
                            )

                    # Parse sort_product (display order)
                    sort_product_str = str(record.get("sort_product", "")).strip()
                    sort_product = None
                    if sort_product_str:
                        try:
                            sort_product = int(
                                float(sort_product_str)
                            )  # Handle both int and float strings
                        except ValueError:
                            logger.warning(
                                f"Invalid sort_product format in row {idx}: {sort_product_str}"
                            )

                    # Parse image_url
                    image_url = str(record.get("Image_URL", "")).strip()
                    if not image_url:
                        image_url = None
                    elif len(image_url) > 1000:
                        logger.warning(
                            f"Image URL too long ({len(image_url)} chars) in row {idx}, truncating to 1000"
                        )
                        image_url = image_url[:1000]

                    # Parse brand (product_brand)
                    brand = str(record.get("product_brand", "")).strip()
                    if not brand:
                        brand = None
                    elif len(brand) > 100:
                        logger.warning(
                            f"Brand name too long ({len(brand)} chars) in row {idx}, truncating to 100"
                        )
                        brand = brand[:100]

                    # Parse EAN (EAN_Code)
                    ean = str(record.get("EAN_Code", "")).strip()
                    if not ean:
                        ean = None
                    else:
                        # Remove any non-numeric characters
                        ean = "".join(filter(str.isdigit, ean))
                        if not ean:
                            ean = None
                        elif len(ean) > 18:
                            logger.warning(
                                f"EAN code too long ({len(ean)} digits) in row {idx}, truncating to 18"
                            )
                            ean = ean[:18]

                    # Parse weight (Weight in kg)
                    weight_str = str(record.get("Weight", "")).strip()
                    weight_kg = None
                    if weight_str:
                        try:
                            # Replace comma with dot for decimal separator (European format)
                            weight_str_normalized = weight_str.replace(",", ".")
                            weight_value = float(weight_str_normalized)

                            # Auto-detect if value is in grams (values >= 1 without decimal point are likely grams)
                            # If the original string has no decimal separator and value >= 1, assume it's in grams
                            if (
                                weight_value >= 1.0
                                and "." not in weight_str_normalized
                                and "," not in weight_str
                            ):
                                # Convert grams to kg
                                weight_kg = weight_value / 1000.0
                                logger.info(
                                    f"Row {idx} ({sku}): Converted {weight_value}g to {weight_kg}kg"
                                )
                            else:
                                # Already in kg
                                weight_kg = weight_value

                            # Validate reasonable weight (0 to 1000 kg)
                            if weight_kg < 0:
                                logger.warning(
                                    f"Negative weight ({weight_kg} kg) in row {idx}, setting to None"
                                )
                                weight_kg = None
                            elif weight_kg > 1000:
                                logger.warning(
                                    f"Weight too high ({weight_kg} kg) in row {idx}, might be incorrect"
                                )
                        except ValueError:
                            logger.warning(
                                f"Invalid weight format in row {idx}: {weight_str}"
                            )

                    product = ProductFromSheet(
                        sku=sku,
                        romanian_name=romanian_name,
                        emag_fbe_ro_price_ron=price,
                        sort_product=sort_product,
                        image_url=image_url,
                        brand=brand,
                        ean=ean,
                        weight_kg=weight_kg,
                        row_number=idx,
                        raw_data=record,
                    )
                    products.append(product)

                except Exception as e:
                    logger.error(f"Error processing row {idx}: {e}")
                    skipped_errors += 1
                    continue

            # Log detailed statistics
            successful_products = len(products)
            total_skipped = skipped_no_sku + skipped_errors

            logger.info("=" * 80)
            logger.info("Google Sheets Import Summary:")
            logger.info(f"  Total rows in sheet: {total_rows}")
            logger.info(f"  Successfully parsed: {successful_products}")
            logger.info(f"  Skipped (no SKU): {skipped_no_sku}")
            logger.info(f"  Skipped (errors): {skipped_errors}")
            logger.info(f"  Total skipped: {total_skipped}")
            logger.info(
                f"  Products with fallback name (SKU as name): {products_with_fallback_name}"
            )
            logger.info("=" * 80)

            if total_skipped > 0:
                logger.warning(
                    f"⚠️  {total_skipped} products were skipped during import!"
                )
                logger.warning("   Check logs above for details on skipped rows")

            return products

        except Exception as e:
            logger.error(f"Failed to retrieve products from Google Sheets: {e}")
            raise

    def get_product_by_sku(self, sku: str) -> ProductFromSheet | None:
        """
        Get a specific product by SKU

        Args:
            sku: Product SKU to search for

        Returns:
            Optional[ProductFromSheet]: Product if found, None otherwise
        """
        products = self.get_all_products()
        for product in products:
            if product.sku == sku:
                return product
        return None

    def get_products_by_skus(self, skus: list[str]) -> list[ProductFromSheet]:
        """
        Get multiple products by their SKUs

        Args:
            skus: List of SKUs to search for

        Returns:
            List[ProductFromSheet]: List of found products
        """
        all_products = self.get_all_products()
        sku_set = set(skus)

        return [p for p in all_products if p.sku in sku_set]

    def get_all_suppliers(self) -> list[SupplierFromSheet]:
        """
        Retrieve all product suppliers from Google Sheets Product_Suppliers tab

        Returns:
            List[SupplierFromSheet]: List of suppliers from the sheet
        """
        try:
            worksheet = self.get_suppliers_worksheet()

            # Get all values as raw strings to preserve comma decimal separator
            all_values = worksheet.get_all_values()

            if not all_values or len(all_values) < 2:
                logger.warning("No data found in suppliers worksheet")
                return []

            # First row is header
            header_row = all_values[0]
            data_rows = all_values[1:]

            # Create column index mapping
            column_map = {col: idx for idx, col in enumerate(header_row)}

            # Statistics tracking
            total_rows = len(data_rows)
            skipped_missing_data = 0
            skipped_errors = 0

            suppliers = []
            for idx, row in enumerate(
                data_rows, start=2
            ):  # Start at 2 (row 1 is header)
                try:
                    # Extract required fields using column mapping
                    sku = str(
                        row[column_map.get("SKU", 0)]
                        if len(row) > column_map.get("SKU", 0)
                        else ""
                    ).strip()
                    supplier_name = str(
                        row[column_map.get("Supplier_Name", 0)]
                        if len(row) > column_map.get("Supplier_Name", 0)
                        else ""
                    ).strip()
                    price_cny_str = str(
                        row[column_map.get("Price_CNY", 0)]
                        if len(row) > column_map.get("Price_CNY", 0)
                        else ""
                    ).strip()

                    # Validate required fields
                    if not sku or not supplier_name or not price_cny_str:
                        # Log detailed info about what's missing
                        missing_fields = []
                        if not sku:
                            missing_fields.append("SKU")
                        if not supplier_name:
                            missing_fields.append("Supplier_Name")
                        if not price_cny_str:
                            missing_fields.append("Price_CNY")

                        logger.debug(
                            f"Skipping row {idx}: Missing {', '.join(missing_fields)} "
                            f"(SKU: '{sku}', Supplier: '{supplier_name}', Price: '{price_cny_str}')"
                        )
                        skipped_missing_data += 1
                        continue

                    # Parse price
                    try:
                        # Replace comma with dot for decimal separator
                        price_cny_str = price_cny_str.replace(",", ".")
                        price_cny = float(price_cny_str)

                        if price_cny < 0:
                            logger.warning(
                                f"Row {idx}: Negative price {price_cny}, skipping"
                            )
                            skipped_errors += 1
                            continue
                    except ValueError:
                        logger.warning(
                            f"Row {idx}: Invalid price format '{price_cny_str}', skipping"
                        )
                        skipped_errors += 1
                        continue

                    # Helper function to get column value
                    def get_col(col_name, default="", current_row=row):
                        col_idx = column_map.get(col_name)
                        if col_idx is not None and len(current_row) > col_idx:
                            return str(current_row[col_idx]).strip()
                        return default

                    # Extract optional fields
                    supplier_contact = get_col("Supplier_Contact") or None

                    # Try different URL column names
                    supplier_url = (
                        get_col("Supplier_URL")
                        or get_col("Product_Supplier_URL")
                        or None
                    )

                    # Try different notes column names
                    supplier_notes = (
                        get_col("Supplier_Notes")
                        or get_col("Supplier_Product_Notes")
                        or None
                    )

                    # Get Chinese product name
                    supplier_product_chinese_name = (
                        get_col("Supplier_Product_Chinese_Name") or None
                    )

                    # Get product specification
                    supplier_product_specification = (
                        get_col("Product_Specification") or None
                    )

                    # Truncate long fields
                    if supplier_name and len(supplier_name) > 255:
                        logger.warning(
                            f"Row {idx}: Supplier name too long, truncating to 255 chars"
                        )
                        supplier_name = supplier_name[:255]

                    if supplier_url and len(supplier_url) > 1000:
                        logger.warning(
                            f"Row {idx}: Supplier URL too long, truncating to 1000 chars"
                        )
                        supplier_url = supplier_url[:1000]

                    if (
                        supplier_product_chinese_name
                        and len(supplier_product_chinese_name) > 500
                    ):
                        logger.warning(
                            f"Row {idx}: Chinese name too long, truncating to 500 chars"
                        )
                        supplier_product_chinese_name = supplier_product_chinese_name[
                            :500
                        ]

                    supplier = SupplierFromSheet(
                        sku=sku,
                        supplier_name=supplier_name,
                        price_cny=price_cny,
                        supplier_contact=supplier_contact,
                        supplier_url=supplier_url,
                        supplier_notes=supplier_notes,
                        supplier_product_chinese_name=supplier_product_chinese_name,
                        supplier_product_specification=supplier_product_specification,
                        row_number=idx,
                        raw_data=dict(zip(header_row, row, strict=False)),  # Convert row to dict
                    )
                    suppliers.append(supplier)

                except Exception as e:
                    logger.error(f"Error processing supplier row {idx}: {e}")
                    skipped_errors += 1
                    continue

            # Log detailed statistics
            successful_suppliers = len(suppliers)
            total_skipped = skipped_missing_data + skipped_errors
            unique_skus = len({s.sku for s in suppliers})

            logger.info("=" * 80)
            logger.info("Google Sheets Suppliers Import Summary:")
            logger.info(f"  Total rows in sheet: {total_rows}")
            logger.info(f"  Successfully parsed: {successful_suppliers}")
            logger.info(f"  Unique SKUs with suppliers: {unique_skus}")
            logger.info(f"  Skipped (missing data): {skipped_missing_data}")
            logger.info(f"  Skipped (errors): {skipped_errors}")
            logger.info(f"  Total skipped: {total_skipped}")

            if skipped_missing_data > 0:
                logger.info(
                    f"  ℹ️  {skipped_missing_data} empty rows skipped (SKUs without suppliers)"
                )

            logger.info("=" * 80)

            if skipped_errors > 0:
                logger.warning(f"⚠️  {skipped_errors} rows with errors were skipped!")
                logger.warning("   Check logs above for details on error rows")

            return suppliers

        except Exception as e:
            logger.error(f"Failed to retrieve suppliers from Google Sheets: {e}")
            raise

    def get_suppliers_by_sku(self, sku: str) -> list[SupplierFromSheet]:
        """
        Get all suppliers for a specific SKU

        Args:
            sku: Product SKU to search for

        Returns:
            List[SupplierFromSheet]: List of suppliers for the SKU
        """
        all_suppliers = self.get_all_suppliers()
        return [s for s in all_suppliers if s.sku == sku]

    def get_suppliers_by_skus(
        self, skus: list[str]
    ) -> dict[str, list[SupplierFromSheet]]:
        """
        Get suppliers for multiple SKUs

        Args:
            skus: List of SKUs to search for

        Returns:
            Dict mapping SKU to list of suppliers
        """
        all_suppliers = self.get_all_suppliers()
        sku_set = set(skus)

        result: dict[str, list[SupplierFromSheet]] = {sku: [] for sku in skus}
        for supplier in all_suppliers:
            if supplier.sku in sku_set:
                result[supplier.sku].append(supplier)

        return result

    def get_sheet_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the Google Sheets data

        Returns:
            Dict with statistics
        """
        try:
            products = self.get_all_products()
            suppliers = self.get_all_suppliers()

            total_products = len(products)
            products_with_price = sum(1 for p in products if p.emag_fbe_ro_price_ron)
            unique_skus = len({p.sku for p in products})

            # Supplier statistics
            unique_supplier_skus = len({s.sku for s in suppliers})
            unique_supplier_names = len({s.supplier_name for s in suppliers})
            total_suppliers = len(suppliers)

            # Calculate average suppliers per SKU
            sku_supplier_count = {}
            for supplier in suppliers:
                sku_supplier_count[supplier.sku] = (
                    sku_supplier_count.get(supplier.sku, 0) + 1
                )

            avg_suppliers_per_sku = (
                sum(sku_supplier_count.values()) / len(sku_supplier_count)
                if sku_supplier_count
                else 0
            )

            return {
                "total_products": total_products,
                "products_with_price": products_with_price,
                "products_without_price": total_products - products_with_price,
                "unique_skus": unique_skus,
                "duplicate_skus": total_products - unique_skus,
                "sheet_name": self.config.sheet_name,
                "products_tab": self.config.products_sheet_tab,
                "suppliers_tab": self.config.suppliers_sheet_tab,
                "total_supplier_entries": total_suppliers,
                "unique_supplier_names": unique_supplier_names,
                "skus_with_suppliers": unique_supplier_skus,
                "avg_suppliers_per_sku": round(avg_suppliers_per_sku, 2),
            }
        except Exception as e:
            logger.error(f"Failed to get sheet statistics: {e}")
            return {"error": str(e)}
