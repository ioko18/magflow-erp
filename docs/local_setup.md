# MagFlow ERP - Local-Only Setup Guide

The steps below assume that you plan to run MagFlow ERP strictly on your personal computer without sharing services with other systems.

## 1. Configure Environment Variables

1.1 Copy the template and adjust credentials if you have not already:
```bash
cp .env.example .env.local
```

1.2 Edit `.env.local` and confirm the following baseline values:
- `DB_HOST=localhost`
- `DB_PORT=5432`
- `DB_USER=magflow_dev`
- `DB_PASS=dev_password`
- `DB_NAME=magflow_dev`
- `DB_SCHEMA=app`

1.3 Export the local overrides when working outside Docker:
```bash
export $(grep -v '^#' .env.local | xargs)
```

> **Tip:** Keep `.env.local` out of version control. Add custom secrets (API keys, passwords) only to your local file.

## 2. Provision the PostgreSQL Database

2.1 Start PostgreSQL (install via Homebrew, Docker, or local package manager). For Homebrew on macOS:
```bash
brew services start postgresql
```

2.2 Create the development database and role:
```sql
CREATE USER magflow_dev WITH PASSWORD 'dev_password';
CREATE DATABASE magflow_dev OWNER magflow_dev;
GRANT ALL PRIVILEGES ON DATABASE magflow_dev TO magflow_dev;
```

2.3 Run migrations:
```bash
alembic upgrade head
```

2.4 Optional seed data:
```bash
python scripts/init_db.py
```

## 3. Run the Application

3.1 Install Python dependencies:
```bash
pip install -r requirements-dev.txt
```

3.2 Start Redis only if you need background jobs. Otherwise you can keep `REDIS_ENABLED=False` in `.env.local`.

3.3 Launch the API using Uvicorn:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will connect to `magflow_dev` automatically through the environment overrides.

## 4. Smoke Tests for the Database

4.1 Verify direct connectivity and schema via psycopg2:
```bash
python tests/scripts/test_db_direct.py
```

4.2 Verify the async SQLAlchemy stack:
```bash
python tests/scripts/test_app_db.py
```

4.3 To run the main unit test suite quickly:
```bash
make local-smoke
```

## 5. Routine Maintenance

- **Backups:** Use `pg_dump magflow_dev > backups/magflow_dev_$(date +%Y%m%d).sql` periodically.
- **Log rotation:** Run `make manage-logs` weekly to archive `logs/` (see the target description below).
- **Dependency updates:** Use `pip install -r requirements.txt --upgrade` monthly, then run tests.
- **Security:** Store any API secrets in `.env.local`; never commit them to the repository.

## 6. Troubleshooting

- If Uvicorn fails to connect to PostgreSQL, verify that PostgreSQL is running and that `PGDATA` is initialized.
- Use `psql -h localhost -U magflow_dev -d magflow_dev` to open a shell and inspect schema or data.
- Ensure Alembic migrations are up to date with `alembic history --verbose`.
