#!/usr/bin/env bash
set -euo pipefail

mkdir -p app/core app/routers docker migrations/versions docs scripts

# .env.example
cat > .env.example <<'EOF'
APP_PORT=8010
DB_HOST=db
DB_PORT=5432
DB_NAME=magflow
DB_USER=app
DB_PASS=app_password_change_me
SEARCH_PATH=app,public
OBS_KEY=change_me
EOF

# docker-compose.yml
cat > docker-compose.yml <<'EOF'
version: "3.9"
services:
  db:
    image: postgres:16
    container_name: magflow_pg
    environment:
      POSTGRES_DB: ${DB_NAME:-magflow}
      POSTGRES_USER: ${DB_USER:-app}
      POSTGRES_PASSWORD: ${DB_PASS:-app_password_change_me}
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-app} -d ${DB_NAME:-magflow}"]
      interval: 5s
      timeout: 3s
      retries: 20
    volumes: [ "pg_data:/var/lib/postgresql/data" ]

  app:
    build: .
    container_name: magflow_app
    depends_on:
      db: { condition: service_healthy }
    environment:
      APP_PORT: ${APP_PORT:-8010}
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: ${DB_NAME:-magflow}
      DB_USER: ${DB_USER:-app}
      DB_PASS: ${DB_PASS:-app_password_change_me}
      SEARCH_PATH: ${SEARCH_PATH:-app,public}
      OBS_KEY: ${OBS_KEY:-change_me}
    ports: [ "${APP_PORT:-8010}:8001" ]
    command: ["/bin/sh", "/app/docker/app-entrypoint.sh"]
    volumes: [ ".:/app" ]

volumes:
  pg_data:
EOF

# Dockerfile
cat > Dockerfile <<'EOF'
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg postgresql-client \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
EOF

# requirements.txt
cat > requirements.txt <<'EOF'
fastapi==0.116.*
uvicorn[standard]==0.30.*
SQLAlchemy==2.0.*
psycopg[binary]==3.2.*
alembic==1.13.*
pydantic-settings==2.4.*
EOF

# alembic.ini
cat > alembic.ini <<'EOF'
[alembic]
script_location = migrations
prepend_sys_path = .
sqlalchemy.url = postgresql+psycopg://%(DB_USER)s:%(DB_PASS)s@%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s
[post_write_hooks]
EOF

# migrations/env.py
cat > migrations/env.py <<'EOF'
from __future__ import annotations
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql+psycopg://{os.getenv('DB_USER','app')}:{os.getenv('DB_PASS','app_password_change_me')}"
    f"@{os.getenv('DB_HOST','db')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','magflow')}"
)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None
VERSION_TABLE_SCHEMA = "app"
SEARCH_PATH = os.getenv("SEARCH_PATH", "app,public")

def _configure_connection(conn):
    conn.execute(text(f"SET search_path TO {SEARCH_PATH}"))

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        version_table_schema=VERSION_TABLE_SCHEMA,
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        _configure_connection(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=VERSION_TABLE_SCHEMA,
            include_schemas=True,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF

# migrations/versions/0001_init_schema.py
cat > migrations/versions/0001_init_schema.py <<'EOF'
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public")
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(12,2), nullable=True),
        schema="app",
    )
    op.create_index(
        "ix_products_name_lower",
        "products",
        [sa.text("lower(name)")],
        unique=False,
        postgresql_using="btree",
        schema="app",
    )
    op.create_index(
        "ix_products_price",
        "products",
        ["price"],
        unique=False,
        schema="app",
    )

def downgrade() -> None:
    op.drop_index("ix_products_price", table_name="products", schema="app")
    op.drop_index("ix_products_name_lower", table_name="products", schema="app")
    op.drop_table("products", schema="app")
EOF

# app files
cat > app/__init__.py <<'EOF'
__all__ = []
EOF

cat > app/core/config.py <<'EOF'
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_port: int = 8010
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "magflow"
    db_user: str = "app"
    db_pass: str = "app_password_change_me"
    search_path: str = "app,public"
    obs_key: str = "change_me"
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
settings = Settings()
EOF

cat > app/db.py <<'EOF'
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .core.config import settings
DATABASE_URL = (
    f"postgresql+psycopg://{settings.db_user}:{settings.db_pass}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"options": f"-c search_path={settings.search_path}"},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOF

cat > app/routers/health.py <<'EOF'
from fastapi import APIRouter
router = APIRouter(tags=["health"])
@router.get("/health")
def health():
    return {"ok": True}
EOF

cat > app/main.py <<'EOF'
from fastapi import FastAPI
from .routers import health as health_router
def create_app() -> FastAPI:
    app = FastAPI(title="MagFlow API", version="0.1.0")
    app.include_router(health_router.router)
    return app
app = create_app()
EOF

# entrypoint
cat > docker/app-entrypoint.sh <<'EOF'
#!/bin/sh
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
EOF
chmod +x docker/app-entrypoint.sh

# Makefile
cat > Makefile <<'EOF'
.PHONY: up down logs ci
up:
	docker compose up -d db app
down:
	docker compose down
logs:
	docker compose logs -f app
ci:
	docker compose build --no-cache
	docker compose up -d db app
	curl -sS http://127.0.0.1:8010/health | grep -q '"ok": true'
EOF

# README
cat > README.md <<'EOF'
# MagFlow — ERP (FastAPI + Postgres)
Quick start:
  cp .env.example .env
  docker compose up -d db app
  curl http://127.0.0.1:8010/health
Alembic rulează la startup (`alembic upgrade head`).
EOF

# .gitignore
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
*.pyo
*.pyd
.env
.venv/
dist/
build/
pg_data/
.pytest_cache/
.mypy_cache/
EOF

# docs/cascade_master_prompt.md (scurt)
cat > docs/cascade_master_prompt.md <<'EOF'
# CASCADE MASTER PROMPT — MagFlow (ERP all-in)
Mode: PLAN → DIFF → APPLY → TEST → REPORT. Schimbări ≤200 LoC și ≤10 fișiere/pas.
Nu atingi .env/secrete; fără comenzi distructive; fără rețea externă în CI.
KILL-SWITCH: DROP/RENAME, docker compose cu porturi/secrete noi, ștergeri masive, apeluri reale upstream, publish/stock fără dry_run=1 — CERERE CONFIRMARE.

Pinned: .env.example, docker-compose.yml, alembic/env.py, app/main.py, app/routers/*, app/models/*, app/schemas/*, migrations/**, scripts/smoke.*, tests/**, README.md, docs/cascade_master_prompt.md

Allow (auto): git status/diff, ls, cat, rg, curl http://127.0.0.1:8010/health
Deny: rm, sudo, docker system prune, drop database, truncate , curl http(s):// (non-local)

SLO/KPI: TTP<15m/SKU; non-orders ≤3 rps/≤180 rpm; p99 publish<1500ms; pg_stat_statements on.
EOF

cp .env.example .env
echo "Bootstrap gata."
