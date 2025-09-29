#!/usr/bin/env python3
"""
Test Full eMAG Sync for MagFlow ERP.

This script tests the complete eMAG synchronization with database integration.
"""

import os
import sys
import asyncio
import aiohttp
import base64
import json
import psycopg2
import uuid
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

class FullEmagSync:
    """Full eMAG synchronization with database integration."""
    
    def __init__(self, account_type: str = "main"):
        self.account_type = account_type
        self.username = os.getenv(f'EMAG_{account_type.upper()}_USERNAME')
        self.password = os.getenv(f'EMAG_{account_type.upper()}_PASSWORD')
        self.base_url = "https://marketplace-api.emag.ro/api-3"
        
        # Create Basic Auth header
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"
        
        # Database connection
        self.db_url = "postgresql://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:5433/magflow"
    
    def get_db_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.db_url)
    
    async def sync_products(self, max_pages: int = 2):
        """Sync products from eMAG to database."""
        print(f"\\n🔄 Syncing products from {self.account_type.upper()} account...")
        
        # Create sync log
        sync_log_id = str(uuid.uuid4())
        
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        try:
            # Insert sync log
            cur.execute("""
                INSERT INTO emag_sync_logs (
                    id, sync_type, account_type, operation, status, 
                    started_at, sync_version, triggered_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                sync_log_id, "products", self.account_type, "test_sync", 
                "running", datetime.utcnow(), "v4.4.8", "test_script"
            ))
            conn.commit()
            
            # Fetch products from eMAG
            products = await self._fetch_products_from_emag(max_pages)
            
            # Process and save products
            processed_count = 0
            created_count = 0
            updated_count = 0
            
            for product_data in products:
                try:
                    sku = product_data.get("part_number") or product_data.get("sku")
                    if not sku:
                        continue
                    
                    # Check if product exists
                    cur.execute("""
                        SELECT id FROM emag_products 
                        WHERE sku = %s AND account_type = %s
                    """, (sku, self.account_type))
                    
                    existing = cur.fetchone()
                    
                    if existing:
                        # Update existing product
                        cur.execute("""
                            UPDATE emag_products SET
                                name = %s, price = %s, stock_quantity = %s,
                                is_active = %s, last_synced_at = %s,
                                sync_status = %s, raw_emag_data = %s,
                                updated_at = %s
                            WHERE sku = %s AND account_type = %s
                        """, (
                            product_data.get("name", ""),
                            float(product_data.get("price", 0) or 0),
                            int(product_data.get("stock", [{"value": 0}])[0].get("value", 0)),
                            product_data.get("status") == "active",
                            datetime.utcnow(),
                            "synced",
                            json.dumps(product_data),
                            datetime.utcnow(),
                            sku,
                            self.account_type
                        ))
                        updated_count += 1
                    else:
                        # Create new product
                        product_id = str(uuid.uuid4())
                        cur.execute("""
                            INSERT INTO emag_products (
                                id, emag_id, sku, name, account_type, price,
                                stock_quantity, is_active, sync_status,
                                last_synced_at, created_at, updated_at, raw_emag_data
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            product_id,
                            str(product_data.get("id", "")),
                            sku,
                            product_data.get("name", ""),
                            self.account_type,
                            float(product_data.get("price", 0) or 0),
                            int(product_data.get("stock", [{"value": 0}])[0].get("value", 0)),
                            product_data.get("status") == "active",
                            "synced",
                            datetime.utcnow(),
                            datetime.utcnow(),
                            datetime.utcnow(),
                            json.dumps(product_data)
                        ))
                        created_count += 1
                    
                    processed_count += 1
                    
                except Exception as e:
                    print(f"    ❌ Error processing product {sku}: {e}")
            
            # Update sync log
            cur.execute("""
                UPDATE emag_sync_logs SET
                    status = %s, completed_at = %s, total_items = %s,
                    processed_items = %s, created_items = %s, updated_items = %s,
                    duration_seconds = %s
                WHERE id = %s
            """, (
                "completed", datetime.utcnow(), len(products),
                processed_count, created_count, updated_count,
                (datetime.utcnow() - datetime.utcnow()).total_seconds(),
                sync_log_id
            ))
            
            conn.commit()
            
            print(f"    ✅ Sync completed:")
            print(f"       Total products: {len(products)}")
            print(f"       Processed: {processed_count}")
            print(f"       Created: {created_count}")
            print(f"       Updated: {updated_count}")
            
            return {
                "total": len(products),
                "processed": processed_count,
                "created": created_count,
                "updated": updated_count
            }
            
        except Exception as e:
            # Update sync log with error
            cur.execute("""
                UPDATE emag_sync_logs SET
                    status = %s, completed_at = %s, errors = %s
                WHERE id = %s
            """, (
                "failed", datetime.utcnow(), 
                json.dumps([{"error": str(e), "timestamp": datetime.utcnow().isoformat()}]),
                sync_log_id
            ))
            conn.commit()
            raise
        finally:
            conn.close()
    
    async def _fetch_products_from_emag(self, max_pages: int):
        """Fetch products from eMAG API."""
        url = f"{self.base_url}/product_offer/read"
        
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        all_products = []
        
        for page in range(1, max_pages + 1):
            print(f"    📄 Fetching page {page}...")
            
            data = {
                "data": {
                    "currentPage": page,
                    "itemsPerPage": 10
                }
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=data, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if not result.get("isError", True):
                                products = result.get("results", [])
                                all_products.extend(products)
                                print(f"       ✅ {len(products)} products")
                                
                                # Check pagination
                                pagination = result.get("pagination", {})
                                if page >= pagination.get("totalPages", 0):
                                    break
                            else:
                                error_msg = result.get("messages", [{"message": "Unknown error"}])[0].get("message", "Unknown error")
                                print(f"       ❌ API error: {error_msg}")
                                break
                        else:
                            print(f"       ❌ HTTP {response.status}")
                            break
                            
            except Exception as e:
                print(f"       ❌ Exception: {str(e)}")
                break
            
            # Rate limiting delay
            await asyncio.sleep(1.5)
        
        return all_products

async def main():
    """Main test function."""
    print("MagFlow ERP - Full eMAG Sync Test")
    print("="*50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test both accounts
    results = {}
    
    for account_type in ["main", "fbe"]:
        try:
            sync = FullEmagSync(account_type)
            if sync.username and sync.password:
                result = await sync.sync_products(max_pages=2)
                results[account_type] = result
            else:
                print(f"\\n❌ {account_type.upper()} account credentials not configured")
                results[account_type] = None
        except Exception as e:
            print(f"\\n❌ {account_type.upper()} account sync failed: {e}")
            results[account_type] = None
    
    # Summary
    print(f"\\nFull Sync Test Summary")
    print("="*50)
    
    for account_type, result in results.items():
        if result:
            print(f"{account_type.upper()} Account: ✅ SUCCESS")
            print(f"  Total: {result['total']}, Created: {result['created']}, Updated: {result['updated']}")
        else:
            print(f"{account_type.upper()} Account: ❌ FAILED")
    
    # Check database
    try:
        conn = psycopg2.connect("postgresql://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:5433/magflow")
        cur = conn.cursor()
        
        cur.execute("SELECT account_type, COUNT(*) FROM emag_products GROUP BY account_type")
        counts = cur.fetchall()
        
        print(f"\\nDatabase Status:")
        for account_type, count in counts:
            print(f"  {account_type.upper()} products: {count}")
        
        cur.execute("SELECT COUNT(*) FROM emag_sync_logs WHERE sync_type = 'products'")
        log_count = cur.fetchone()[0]
        print(f"  Sync logs: {log_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"\\n❌ Database check failed: {e}")
    
    print(f"\\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())
