#!/usr/bin/env python3
"""
eMAG Sync Verification Script
Checks what products have been synchronized from eMAG
"""

import psycopg2
from datetime import datetime
from typing import Dict, List

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        "postgresql://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:6432/postgres"
    )

def check_sync_status() -> Dict:
    """Check overall sync status"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get sync statistics
            cur.execute("""
                SELECT
                    COUNT(*) as total_syncs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_syncs,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_syncs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_syncs,
                    MAX(created_at) as last_sync_time
                FROM app.emag_offer_syncs
            """)
            sync_stats = cur.fetchone()

            # Get account statistics
            cur.execute("""
                SELECT
                    account_type,
                    COUNT(*) as sync_count,
                    SUM(total_offers_processed) as total_offers,
                    MAX(created_at) as last_sync
                FROM app.emag_offer_syncs
                GROUP BY account_type
                ORDER BY account_type
            """)
            account_stats = cur.fetchall()

            return {
                "total_syncs": sync_stats[0] or 0,
                "completed_syncs": sync_stats[1] or 0,
                "running_syncs": sync_stats[2] or 0,
                "failed_syncs": sync_stats[3] or 0,
                "last_sync_time": sync_stats[4].isoformat() if sync_stats[4] else None,
                "accounts": {
                    row[0]: {
                        "sync_count": row[1],
                        "total_offers": row[2] or 0,
                        "last_sync": row[3].isoformat() if row[3] else None
                    }
                    for row in account_stats
                }
            }
    finally:
        conn.close()

def get_synchronized_products(limit: int = 20) -> List[Dict]:
    """Get synchronized products"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    emag_id,
                    name,
                    part_number,
                    is_active,
                    created_at,
                    updated_at
                FROM app.emag_products
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))

            products = []
            for row in cur.fetchall():
                products.append({
                    "emag_id": row[0],
                    "name": row[1],
                    "part_number": row[2],
                    "is_active": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None
                })

            return products
    finally:
        conn.close()

def get_synchronized_offers(limit: int = 20) -> List[Dict]:
    """Get synchronized offers"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    emag_product_id,
                    emag_offer_id,
                    stock,
                    price,
                    sale_price,
                    created_at,
                    updated_at
                FROM app.emag_product_offers
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))

            offers = []
            for row in cur.fetchall():
                offers.append({
                    "emag_product_id": row[0],
                    "emag_offer_id": row[1],
                    "stock": row[2],
                    "price": float(row[3]) if row[3] else None,
                    "sale_price": float(row[4]) if row[4] else None,
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None
                })

            return offers
    finally:
        conn.close()

def generate_sync_report() -> Dict:
    """Generate comprehensive sync report"""
    return {
        "timestamp": datetime.now().isoformat(),
        "sync_status": check_sync_status(),
        "products": get_synchronized_products(),
        "offers": get_synchronized_offers()
    }

def print_sync_report():
    """Print formatted sync report"""
    report = generate_sync_report()

    print("🚀 eMAG Sync Verification Report")
    print("=" * 50)
    print(f"📅 Generated: {report['timestamp']}")
    print()

    # Sync Status
    sync_status = report['sync_status']
    print("📊 Sync Status:")
    print(f"   Total Syncs: {sync_status['total_syncs']}")
    print(f"   Completed: {sync_status['completed_syncs']}")
    print(f"   Running: {sync_status['running_syncs']}")
    print(f"   Failed: {sync_status['failed_syncs']}")
    if sync_status['last_sync_time']:
        print(f"   Last Sync: {sync_status['last_sync_time']}")
    print()

    # Account Status
    if sync_status['accounts']:
        print("🏢 Account Status:")
        for account, stats in sync_status['accounts'].items():
            print(f"   {account.upper()}: {stats['sync_count']} syncs, {stats['total_offers']} offers")
        print()

    # Products
    products = report['products']
    print(f"📦 Synchronized Products ({len(products)}):")
    if products:
        for i, product in enumerate(products, 1):
            status = "✅ Active" if product['is_active'] else "❌ Inactive"
            print(f"   {i}. [{product['emag_id']}] {product['name'][:60]}... {status}")
    else:
        print("   ❌ No products synchronized yet")
    print()

    # Offers
    offers = report['offers']
    print(f"💰 Synchronized Offers ({len(offers)}):")
    if offers:
        for i, offer in enumerate(offers, 1):
            price = f"€{offer['price']}" if offer['price'] else "N/A"
            sale_price = f"€{offer['sale_price']}" if offer['sale_price'] else "N/A"
            stock = offer['stock'] if offer['stock'] is not None else "N/A"
            print(f"   {i}. Product {offer['emag_product_id']}: Stock={stock}, Price={price}, Sale={sale_price}")
    else:
        print("   ❌ No offers synchronized yet")
    print()

    # Recommendations
    print("💡 Recommendations:")
    if not products:
        print("   • Run a sync: python3 sync_scheduler.py sync main")
        print("   • Check API connectivity: python3 sync_scheduler.py test")
        print("   • Verify credentials in .env file")
    else:
        print("   • Products are synchronized successfully!")
        print("   • Use sync_monitor.py for real-time monitoring")
        print("   • Check sync_dashboard.py for web interface")

if __name__ == "__main__":
    print_sync_report()
