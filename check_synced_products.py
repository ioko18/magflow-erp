#!/usr/bin/env python3
"""
Check which products have been synced from eMAG to our database
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_session():
    """Create database session"""
    try:
        engine = create_engine(
            "postgresql://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:6432/postgres",
            echo=False
        )
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        raise


def get_latest_syncs(session, account_type=None, limit=5):
    """Get the latest sync records"""
    query = text("""
        SELECT sync_id, account_type, started_at, completed_at, status, total_offers_processed
        FROM app.emag_offer_syncs
        ORDER BY started_at DESC
        LIMIT :limit
    """)
    
    params = {"limit": limit}
    if account_type:
        query = text("""
            SELECT sync_id, account_type, started_at, completed_at, status, total_offers_processed
            FROM app.emag_offer_syncs
            WHERE account_type = :account_type
            ORDER BY started_at DESC
            LIMIT :limit
        """)
        params["account_type"] = account_type
    
    result = session.execute(query, params)
    return result.fetchall()


def get_products_for_sync(session, sync_id):
    """Get products synced in a specific sync operation"""
    result = session.execute(text("""
        SELECT p.emag_id, p.name, p.part_number, p.is_active, 
               o.stock, o.price, o.sale_price
        FROM app.emag_products p
        JOIN app.emag_product_offers o ON p.emag_id = o.emag_product_id
        WHERE o.updated_at BETWEEN (
            SELECT started_at FROM app.emag_offer_syncs WHERE sync_id = :sync_id
        ) AND (
            SELECT COALESCE(completed_at, NOW()) FROM app.emag_offer_syncs WHERE sync_id = :sync_id
        )
        ORDER BY p.name
    """), {"sync_id": sync_id})
    
    return result.fetchall()


def format_timestamp(ts):
    """Format timestamp for display"""
    return ts.strftime('%Y-%m-%d %H:%M:%S') if ts else "N/A"


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Check synced eMAG products')
    parser.add_argument('--account', choices=['main', 'fbe'], 
                        help='Filter by account type (main or fbe)')
    parser.add_argument('--sync-id', help='Show products for a specific sync ID')
    parser.add_argument('--limit', type=int, default=5, 
                        help='Number of sync records to show (default: 5)')
    args = parser.parse_args()

    try:
        with get_db_session() as session:
            if args.sync_id:
                # Show products for a specific sync
                products = get_products_for_sync(session, args.sync_id)
                print(f"Products synced in sync {args.sync_id}:")
                print("-" * 80)
                for i, product in enumerate(products, 1):
                    print(f"{i}. ID: {product.emag_id}")
                    print(f"   Name: {product.name}")
                    print(f"   Part Number: {product.part_number}")
                    print(f"   Active: {'Yes' if product.is_active else 'No'}")
                    print(f"   Stock: {product.stock}")
                    print(f"   Price: {product.price}")
                    print(f"   Sale Price: {product.sale_price}")
                    print("-" * 80)
            else:
                # Show recent syncs
                syncs = get_latest_syncs(session, args.account, args.limit)
                print(f"Last {len(syncs)} sync operations:")
                print("=" * 80)
                for sync in syncs:
                    print(f"Sync ID: {sync.sync_id}")
                    print(f"Account: {sync.account_type}")
                    print(f"Status: {sync.status}")
                    print(f"Started: {format_timestamp(sync.started_at)}")
                    print(f"Completed: {format_timestamp(sync.completed_at)}")
                    print(f"Products Synced: {sync.total_offers_processed or 0}")
                    print("-" * 80)
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()
