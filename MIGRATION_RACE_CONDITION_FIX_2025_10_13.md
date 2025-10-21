# Rezolvarea Race Condition în Migrările Alembic - 13 Octombrie 2025

## Problema Identificată

Când multiple containere Docker (app, worker, beat) porneau simultan, toate încercau să ruleze migrările Alembic în același timp, cauzând eroarea:

```
duplicate key value violates unique constraint "pg_type_typname_nsp_index"
DETAIL: Key (typname, typnamespace)=(alembic_version, 16443) already exists.
```

### Cauza Root

1. **Concurență la startup**: Toate containerele rulau `alembic upgrade head` simultan
2. **Crearea tabelei alembic_version**: Când Alembic încearcă să creeze tabela `alembic_version`, PostgreSQL creează automat un tip pentru aceasta
3. **Race condition**: Două containere încercau să creeze același tip simultan, cauzând eroarea de duplicate key

## Soluții Implementate

### 1. Îmbunătățirea Migrării Inițiale (86f7456767fd)

**Fișier**: `alembic/versions/86f7456767fd_initial_database_schema_with_users_.py`

**Modificări**:
- Adăugat verificare pentru fiecare tabelă înainte de creare
- Implementat error handling pentru cazurile de race condition
- Folosit parametrizare SQL pentru a preveni SQL injection
- Adăugat contorizare pentru tabele create vs. skipped

```python
# Check if table already exists (in case of race condition)
result = conn.execute(text(
    "SELECT COUNT(*) FROM information_schema.tables "
    "WHERE table_schema = 'app' AND table_name = :table_name"
), {"table_name": table.name})

if result.scalar() > 0:
    skipped_count += 1
    continue

table.create(bind=conn, checkfirst=True)
```

### 2. Mecanism de Retry în docker-entrypoint.sh

**Fișier**: `scripts/docker-entrypoint.sh`

**Funcționalități**:
- **Retry logic**: Până la 3 încercări pentru rularea migrărilor
- **Detectare race condition**: Verifică dacă eroarea este cauzată de duplicate key/type
- **Verificare automată**: După detectarea unui race condition, verifică dacă migrările au fost completate de alt container
- **Output capture**: Capturează output-ul migrărilor pentru analiză

```bash
# Detectează race condition
if grep -q -E "(duplicate key|already exists|UniqueViolation)" "$temp_output" 2>/dev/null; then
    echo "   ⚠️  Race condition detected (another container is running migrations)"
    
    # Verifică dacă migrările sunt complete
    if check_migrations_complete; then
        echo "✅ Migrations completed by another container!"
        return 0
    fi
fi
```

## Rezultate

### Înainte
```
magflow_app     | ERROR: duplicate key value violates unique constraint
magflow_app exited with code 1 (restarting)
magflow_worker  | ERROR: duplicate key value violates unique constraint
magflow_worker exited with code 1 (restarting)
```

### După
```
magflow_app     | 📝 Migration attempt 1/3...
magflow_app     | ✅ Migrations completed successfully!

magflow_worker  | 📝 Migration attempt 1/3...
magflow_worker  | ⚠️  Migration attempt 1 failed with exit code 1
magflow_worker  | 🔍 Race condition detected (another container is running migrations)
magflow_worker  | 💤 Waiting for other container to complete migrations...
magflow_worker  | ✅ Migrations completed by another container!

magflow_beat    | 📝 Migration attempt 1/3...
magflow_beat    | ✅ Migrations completed successfully!
```

### Status Containere
```
NAME             STATUS
magflow_app      Up (healthy)
magflow_worker   Up (healthy)
magflow_beat     Up (healthy)
magflow_db       Up (healthy)
magflow_redis    Up (healthy)
```

## Testare

### Test 1: Fresh Start
```bash
make down
make up
# Rezultat: Toate containerele pornesc fără erori
```

### Test 2: Restart Containere
```bash
docker compose restart app worker beat
# Rezultat: Toate containerele se restartează corect
```

### Test 3: Health Check
```bash
curl http://localhost:8000/api/v1/health/ready
# Rezultat: {"status": "ready", ...}
```

## Beneficii

1. **Eliminarea erorilor de race condition**: Containerele nu mai eșuează la pornire
2. **Startup mai rapid**: Nu mai sunt necesare restartări
3. **Logs mai curate**: Erorile de duplicate key sunt gestionate elegant
4. **Robustețe crescută**: Sistemul gestionează corect concurența la startup
5. **Zero downtime**: Toate containerele devin healthy fără intervenție manuală

## Fișiere Modificate

1. `scripts/docker-entrypoint.sh` - Adăugat mecanism de retry și detectare race condition
2. `alembic/versions/86f7456767fd_initial_database_schema_with_users_.py` - Îmbunătățit error handling

## Note Tehnice

- **PostgreSQL advisory locks** au fost considerate dar respinse deoarece nu funcționează corect în timpul creării tabelei alembic_version
- **File-based locks (flock)** nu funcționează între containere separate
- **Soluția finală** folosește retry logic + verificare automată a stării migrărilor
- Migrările sunt **idempotente** - pot fi rulate de mai multe ori fără efecte adverse

## Verificare Finală

```bash
# Test complet
docker compose down -v && docker compose up -d && sleep 30 && docker compose ps

# Toate containerele ar trebui să fie "Up (healthy)"
```

## Data Implementării

13 Octombrie 2025, 12:30 UTC+03:00
