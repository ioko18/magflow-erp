#!/usr/bin/env python3
"""Backfill the app.emag_product_offers.metadata column from raw_data.

Run this script with a database role that owns the table.
"""
import argparse
import json
from typing import Any

from sqlalchemy import create_engine, text


def build_engine(database_url: str):
    return create_engine(database_url)


def build_metadata(raw_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "validation_status": raw_data.get("offer_validation_status"),
        "availability": raw_data.get("availability"),
        "genius_eligibility": raw_data.get("genius_eligibility"),
    }


def backfill(engine, batch_size: int) -> int:
    updated = 0
    query = text(
        """
        SELECT emag_offer_id, raw_data
        FROM app.emag_product_offers
        WHERE metadata IS NULL
           OR metadata = '{}'::jsonb
        ORDER BY emag_offer_id
        LIMIT :limit
        """
    )

    update_stmt = text(
        """
        UPDATE app.emag_product_offers
        SET metadata = CAST(:metadata AS jsonb)
        WHERE emag_offer_id = :emag_offer_id
        """
    )

    with engine.begin() as conn:
        while True:
            rows = conn.execute(query, {"limit": batch_size}).fetchall()
            if not rows:
                break

            for row in rows:
                raw_json = row.raw_data
                if isinstance(raw_json, str):
                    raw_json = json.loads(raw_json or "{}")
                payload = build_metadata(raw_json or {})
                conn.execute(
                    update_stmt,
                    {
                        "emag_offer_id": row.emag_offer_id,
                        "metadata": json.dumps(payload),
                    },
                )
                updated += 1

    return updated


def main():
    parser = argparse.ArgumentParser(description="Backfill eMAG offer metadata")
    parser.add_argument("database_url", help="Database URL with ownership privileges")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    engine = build_engine(args.database_url)
    updated = backfill(engine, args.batch_size)
    print(f"Rows updated: {updated}")


if __name__ == "__main__":
    main()
