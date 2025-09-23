#!/usr/bin/env python3
"""
Test script to insert a single eMAG product directly
"""

import json
import sys
sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def test_single_product_insert():
    """Test inserting a single product directly"""

    # Use the same database connection as sync service
    engine = create_engine(
        "postgresql://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:6432/postgres",
        echo=True
    )
    Session = sessionmaker(bind=engine)

    # Sample product data from the debug output
    product_data = {
        "emag_id": "100",
        "name": "Modul amplificator audio stereo 2x15W cu TA2024",
        "description": "TA2024 DC 12V 2x15W amplificator audio digital HIFI pentru masina si PC",
        "part_number": "EMG140",
        "emag_category_id": 308,
        "emag_brand_id": None,
        "emag_category_name": None,
        "emag_brand_name": "OEM",
        "characteristics": json.dumps([{"id": 30, "tag": None, "value": "1 x Aux in"}, {"id": 5704, "tag": None, "value": "Amplificator"}]),
        "images": json.dumps([{"url": "https://marketplace-static.emag.ro/resources/000/051/802/524/51802524.jpg", "display_type": 0}]),
        "is_active": True,
        "raw_data": json.dumps({"id": 100, "name": "Modul amplificator audio stereo 2x15W cu TA2024", "part_number": "EMG140"}),
    }

    try:
        with Session() as session:
            print("Testing product insertion...")
            session.execute(text("""
                INSERT INTO app.emag_products (
                    emag_id, name, description, part_number, emag_category_id,
                    emag_brand_id, emag_category_name, emag_brand_name,
                    characteristics, images, is_active, raw_data, created_at, updated_at
                )
                VALUES (
                    :emag_id, :name, :description, :part_number, :emag_category_id,
                    :emag_brand_id, :emag_category_name, :emag_brand_name,
                    :characteristics, :images, :is_active, :raw_data, NOW(), NOW()
                )
            """), product_data)
            session.commit()
            print("✅ Product inserted successfully!")

            # Check if it was inserted
            result = session.execute(text("SELECT COUNT(*) FROM app.emag_products WHERE emag_id = :emag_id"), {"emag_id": "100"})
            count = result.scalar()
            print(f"📊 Products with emag_id=100: {count}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_product_insert()
