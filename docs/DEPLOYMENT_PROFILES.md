# MagFlow ERP - Docker Compose Profiles

This guide explains how to run the MagFlow ERP stack using Docker Compose profiles.
Profiles let you keep the default development stack lean and enable optional components on demand.

## Profiles

- `proxy`
  - Enables the `nginx` reverse proxy.
- `monitoring`
  - Enables exporters, `prometheus`, and `grafana`.
- `ops`
  - Enables the `worker` (Celery) and `flower` UI.
- `otel` (production compose only)
  - Enables `otel-collector` and `jaeger`.
- `certs` (production compose only)
  - Enables `certbot` for certificate issuance/renewal.

## Development

- Core minimal:
  ```bash
  docker compose up
  ```
- With reverse proxy:
  ```bash
  docker compose --profile proxy up
  ```
- With monitoring stack:
  ```bash
  docker compose --profile monitoring up
  ```
- With worker and Flower:
  ```bash
  docker compose --profile ops up
  ```
- Combine profiles:
  ```bash
  docker compose --profile proxy --profile monitoring --profile ops up
  ```

## Production (consolidated)

Use the consolidated production compose with optional profiles:

```bash
# Base production (app, db, redis, pgbouncer, nginx may be disabled if not using proxy)
docker compose -f docker-compose.production.yml up -d

# Enable reverse proxy
docker compose -f docker-compose.production.yml --profile proxy up -d

# Enable monitoring stack
docker compose -f docker-compose.production.yml --profile monitoring up -d

# Enable OpenTelemetry collector and Jaeger
docker compose -f docker-compose.production.yml --profile otel up -d

# Enable certbot (Let's Encrypt)
docker compose -f docker-compose.production.yml --profile certs up -d
```

## CI

A dedicated CI compose file (`docker-compose.ci.yml`) is provided with a minimal stack:

```bash
docker compose -f docker-compose.ci.yml up --build
```

You can wait for the API health endpoint using:

```bash
./scripts/wait_for_health.sh http://localhost:8000 /health 90 3
```

## Security & Secrets

- Production compose uses Docker secrets for:
  - Postgres password (`secrets/postgres_password.txt`)
  - Grafana admin password (`secrets/grafana_admin_password.txt`)
- Ensure you set strong values and keep the `secrets/` directory out of version control (already ignored by `.gitignore`).

## Standardized Healthchecks

- All health probes use the `GET /health` endpoint exposed by the application.
- The `Dockerfile` and compose files are aligned to use `/health`.

## Notes

- Bind-mount data directories are created under `./data/` (ignored in Git):
  - `./data/postgres`, `./data/redis`, `./data/prometheus`, `./data/grafana`, `./data/pgbouncer`
- Default DB endpoint is standardized to PgBouncer (`pgbouncer:6432`).
