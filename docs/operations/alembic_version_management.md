# Alembic Version Management

## Requirements
- Database role with privileges to create and update the `alembic_version` table.
- Access to the target database URL.

## Initialize Alembic Tracking
1. Confirm the latest migration revision ID (e.g., `b1234f5d6c78`).
2. Connect with an admin/owner account and run:
   ```bash
   alembic stamp b1234f5d6c78
   ```
   or, if using the Python API:
   ```bash
   alembic -x db_url=postgresql://OWNER:PASSWORD@HOST:PORT/DB stamp b1234f5d6c78
   ```

## Ongoing Usage
- After stamping, use normal commands (`alembic upgrade head`, `alembic downgrade -1`).
- Ensure pipelines authenticate with a role that can read/write `alembic_version`.
