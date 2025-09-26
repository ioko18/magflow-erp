# CASCADE MASTER PROMPT — MagFlow (ERP all-in)

Mode: PLAN → DIFF → APPLY → TEST → REPORT. Schimbări ≤200 LoC și ≤10 fișiere/pas.
Nu atingi .env/secrete; fără comenzi distructive; fără rețea externă în CI.
KILL-SWITCH: DROP/RENAME, docker compose cu porturi/secrete noi, ștergeri masive, apeluri reale upstream, publish/stock fără dry_run=1 — CERERE CONFIRMARE.

Pinned: .env.example, docker-compose.yml, alembic/env.py, app/main.py, app/routers/*, app/models/*, app/schemas/*, migrations/\*\*, scripts/smoke.*, tests/\*\*, README.md, docs/cascade_master_prompt.md

Allow (auto): git status/diff, ls, cat, rg, curl http://127.0.0.1:8010/health
Deny: rm, sudo, docker system prune, drop database, truncate , curl http(s):// (non-local)

SLO/KPI: TTP\<15m/SKU; non-orders ≤3 rps/≤180 rpm; p99 publish\<1500ms; pg_stat_statements on.
