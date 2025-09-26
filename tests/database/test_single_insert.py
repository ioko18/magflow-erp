#!/usr/bin/env python3
"""
Test script to insert a single eMAG product directly into SQLite test database
"""

import json
import sys

sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def test_single_product_insert():
    """Test inserting a single product directly using SQLite."""

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
    )
    Session = sessionmaker(bind=engine)

    product_data = {
        "emag_id": "100",
        "name": "Modul amplificator audio stereo 2x15W cu TA2024",
        "description": "TA2024 DC 12V 2x15W amplificator audio digital HIFI pentru masina si PC",
        "part_number": "EMG140",
        "emag_category_id": 308,
        "emag_brand_id": None,
        "emag_category_name": None,
        "emag_brand_name": "OEM",
        "characteristics": json.dumps([
            {"id": 30, "tag": None, "value": "1 x Aux in"},
            {"id": 5704, "tag": None, "value": "Amplificator"},
        ]),
        "images": json.dumps([
            {
                "url": "https://marketplace-static.emag.ro/resources/000/051/802/524/51802524.jpg",
                "display_type": 0,
            },
        ]),
        "is_active": True,
        "raw_data": json.dumps(
            {
                "id": 100,
                "name": "Modul amplificator audio stereo 2x15W cu TA2024",
                "part_number": "EMG140",
            },
        ),
    }

    with Session() as session:
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS emag_products (
                    emag_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    part_number TEXT,
                    emag_category_id INTEGER,
                    emag_brand_id INTEGER,
                    emag_category_name TEXT,
                    emag_brand_name TEXT,
                    characteristics TEXT,
                    images TEXT,
                    is_active BOOLEAN,
                    raw_data TEXT
                )
                """
            )
        )

        session.execute(
            text(
                """
                INSERT INTO emag_products (
                    emag_id, name, description, part_number, emag_category_id,
                    emag_brand_id, emag_category_name, emag_brand_name,
                    characteristics, images, is_active, raw_data
                )
                VALUES (
                    :emag_id, :name, :description, :part_number, :emag_category_id,
                    :emag_brand_id, :emag_category_name, :emag_brand_name,
                    :characteristics, :images, :is_active, :raw_data
                )
                """
            ),
            product_data,
        )
        session.commit()

        count = session.execute(text("SELECT COUNT(*) FROM emag_products")).scalar()
        assert count == 1

        product = session.execute(
            text("SELECT * FROM emag_products WHERE emag_id = :emag_id"),
            {"emag_id": "100"},
        ).fetchone()
        assert product is not None
        assert product.name == product_data["name"]
        assert product.emag_id == product_data["emag_id"]

        session.execute(text("DROP TABLE IF EXISTS emag_products"))

if __name__ == "__main__":
    success = test_single_product_insert()
    sys.exit(0 if success else 1)
