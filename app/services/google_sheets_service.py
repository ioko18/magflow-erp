"""
Google Sheets Service for MagFlow ERP
Handles authentication and data retrieval from Google Sheets
"""
import logging
from typing import Dict, List, Optional, Any
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
    scopes: List[str] = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]


class ProductFromSheet(BaseModel):
    """Product data structure from Google Sheets"""
    sku: str
    romanian_name: str
    emag_fbe_ro_price_ron: Optional[float] = None
    row_number: int
    raw_data: Dict[str, Any] = {}


class GoogleSheetsService:
    """Service for interacting with Google Sheets"""
    
    def __init__(self, config: Optional[GoogleSheetsConfig] = None):
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
                self.config.service_account_file,
                self.config.scopes
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
            if not self._client:
                if not self.authenticate():
                    return False
            
            self._spreadsheet = self._client.open(self.config.sheet_name)
            logger.info(f"Successfully opened spreadsheet: {self.config.sheet_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to open spreadsheet: {e}")
            return False
    
    def get_products_worksheet(self):
        """Get the products worksheet"""
        if not self._spreadsheet:
            if not self.open_spreadsheet():
                raise Exception("Failed to open spreadsheet")
        
        return self._spreadsheet.worksheet(self.config.products_sheet_tab)
    
    def get_suppliers_worksheet(self):
        """Get the suppliers worksheet"""
        if not self._spreadsheet:
            if not self.open_spreadsheet():
                raise Exception("Failed to open spreadsheet")
        
        return self._spreadsheet.worksheet(self.config.suppliers_sheet_tab)
    
    def get_all_products(self) -> List[ProductFromSheet]:
        """
        Retrieve all products from Google Sheets
        
        Returns:
            List[ProductFromSheet]: List of products from the sheet
        """
        try:
            worksheet = self.get_products_worksheet()
            
            # Get all records as dictionaries
            records = worksheet.get_all_records()
            
            products = []
            for idx, record in enumerate(records, start=2):  # Start at 2 (row 1 is header)
                try:
                    # Extract required fields
                    sku = str(record.get("SKU", "")).strip()
                    romanian_name = str(record.get("Romanian_Name", "")).strip()
                    
                    if not sku or not romanian_name:
                        logger.warning(f"Skipping row {idx}: Missing SKU or Romanian_Name")
                        continue
                    
                    # Parse price
                    price_str = str(record.get("Emag_FBE_RO_Price_RON", "")).strip()
                    price = None
                    if price_str:
                        try:
                            price = float(price_str)
                        except ValueError:
                            logger.warning(f"Invalid price format in row {idx}: {price_str}")
                    
                    product = ProductFromSheet(
                        sku=sku,
                        romanian_name=romanian_name,
                        emag_fbe_ro_price_ron=price,
                        row_number=idx,
                        raw_data=record
                    )
                    products.append(product)
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx}: {e}")
                    continue
            
            logger.info(f"Successfully retrieved {len(products)} products from Google Sheets")
            return products
            
        except Exception as e:
            logger.error(f"Failed to retrieve products from Google Sheets: {e}")
            raise
    
    def get_product_by_sku(self, sku: str) -> Optional[ProductFromSheet]:
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
    
    def get_products_by_skus(self, skus: List[str]) -> List[ProductFromSheet]:
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
    
    def get_sheet_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the Google Sheets data
        
        Returns:
            Dict with statistics
        """
        try:
            products = self.get_all_products()
            
            total_products = len(products)
            products_with_price = sum(1 for p in products if p.emag_fbe_ro_price_ron)
            unique_skus = len(set(p.sku for p in products))
            
            return {
                "total_products": total_products,
                "products_with_price": products_with_price,
                "products_without_price": total_products - products_with_price,
                "unique_skus": unique_skus,
                "duplicate_skus": total_products - unique_skus,
                "sheet_name": self.config.sheet_name,
                "products_tab": self.config.products_sheet_tab
            }
        except Exception as e:
            logger.error(f"Failed to get sheet statistics: {e}")
            return {
                "error": str(e)
            }
