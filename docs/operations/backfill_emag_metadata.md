# Backfilling `app.emag_product_offers.metadata`

1. Ensure the database role has ownership of `app.emag_product_offers`.
2. Run the migration `alembic/versions/b1234f5d6c78_add_metadata_column_to_emag_product_offers.py` if the column does not exist.
3. Execute the helper script:
   ```bash
   python scripts/backfill_emag_offer_metadata.py postgresql://OWNER:PASSWORD@HOST:PORT/DB --batch-size 1000
   ```
4. Verify results:
   ```sql
   SELECT COUNT(*)
   FROM app.emag_product_offers
   WHERE metadata IS NULL OR metadata = '{}'::jsonb;
   ```
5. If the column still lacks data, rerun the script or inspect raw payloads.

## Troubleshooting

- If you see `must be owner of table emag_product_offers`, connect using the owning database role (typically `postgres` or the migration user) before running the script.
- To add the column without Alembic, execute `scripts/sql/add_emag_metadata_column.sql` with the owner account.
