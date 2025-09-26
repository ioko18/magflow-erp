# MagFlow ERP - Ghid de Development

## 🚀 Setup Rapid pentru Development

### 1. Instalare Dependențe

```bash
# Instalează toate dependențele (inclusiv cele noi)
pip install -r requirements.txt

# Dependențe cheie adăugate:
# - backoff>=2.2.1,<3.0.0  (pentru retry logic în eMAG API)
# - greenlet>=3.0.0,<4.0.0 (pentru SQLAlchemy async)
```

### 2. Configurare Bază de Date

```bash
# Pornește doar PostgreSQL și PgBouncer
docker-compose up -d db pgbouncer

# Verifică dacă tabelele sunt create
docker exec -it magflow_pg psql -U app -d magflow -c "\dt app.*"
```

### 3. Configurare eMAG API

```bash
# Setează variabile de mediu în .env
export EMAG_API_USERNAME=your_username
export EMAG_API_PASSWORD=your_password
export EMAG_MAIN_USERNAME=your_main_username
export EMAG_MAIN_PASSWORD=your_main_password
```

### 4. Pornire Completă

```bash
# Pornește toate serviciile
docker-compose up -d

# Verifică statusul
docker-compose ps

# Testează conexiunea
curl http://localhost:8000/health
```

## 🔧 Probleme Comune și Soluții

### 1. **backoff Module Not Found**

**Problemă:** `ModuleNotFoundError: No module named 'backoff'`

**Soluție:** Adaugă în requirements.txt:

```
backoff>=2.2.1,<3.0.0
```

### 2. **PgBouncer Configuration Issues**

**Problemă:** PgBouncer nu se conectează la baza de date

**Soluție:** Verifică fișierul de configurare:

```ini
[databases]
* = host=db port=5432 dbname=magflow user=app password=app_password_change_me

[pgbouncer]
listen_port = 6432
auth_type = md5
pool_mode = transaction
```

### 3. **Database Schema Missing**

**Problemă:** Tabelele eMAG nu există

**Soluție:** Rulează scriptul de inițializare:

```python
python scripts/init_database.py
```

### 4. **Volume Mount Issues**

**Problemă:** Fișierele de configurare nu sunt accesibile în container

**Soluție:** Asigură-te că volume-urile sunt setate corect în docker-compose.yml:

```yaml
volumes:
  - ./deployment/docker/pgbouncer/pgbouncer.ini:/opt/bitnami/pgbouncer/conf/pgbouncer.ini:ro
  - pgbouncer_data:/bitnami/pgbouncer/conf
```

### 5. **Environment Variables**

**Problemă:** Variabilele de mediu nu sunt setate

**Soluție:** Verifică fișierul .env:

```bash
# .env
DB_HOST=localhost
DB_NAME=magflow
DB_USER=app
DB_PASS=app_password_change_me

# eMAG API
EMAG_API_USERNAME=your_username
EMAG_API_PASSWORD=your_password
```

## 🏗️ Arhitectura Sistemului

### Database Schema

```
app/
├── emag_products (produse eMAG)
├── emag_product_offers (oferte eMAG)
├── emag_offer_syncs (sincronizări eMAG)
└── emag_import_conflicts (conflicte import)
```

### API Endpoints

```
POST /api/v1/sync          # Sincronizează produse eMAG
GET  /api/v1/status        # Status sincronizare
GET  /api/v1/products      # Listează produse eMAG
GET  /api/v1/products/statistics  # Statistici produse
```

### Servicii

- **PostgreSQL** (port 5432) - Baza de date principală
- **PgBouncer** (port 6432) - Connection pooler
- **Redis** (port 6379) - Cache și rate limiting
- **FastAPI** (port 8000) - API server
- **Nginx** (port 80) - Reverse proxy

## 🔐 Configurare de Securitate

### JWT Authentication

```python
# În app/api/v1/endpoints/emag_sync.py
from ...deps import get_current_user

@router.post("/sync")
async def sync_emag_offers(
    current_user = Depends(get_current_user)  # Protecție JWT
):
```

### Rate Limiting

```python
# În app/emag/client.py
class EmagAPIWrapper:
    def __init__(self):
        self.rate_limiter = RateLimitTracker()
```

## 📊 Monitoring și Debugging

### Health Checks

```bash
# Verifică toate serviciile
curl http://localhost:8000/health
curl http://localhost:3000/api/health  # Grafana
curl http://localhost:9090/-/healthy  # Prometheus
```

### Logs

```bash
# Logs container PgBouncer
docker logs magflow_pgbouncer

# Logs container App
docker logs magflow_app

# Logs container DB
docker logs magflow_pg
```

### Database Queries

```sql
-- Verifică tabele eMAG
\dt app.emag_*

-- Verifică sincronizări recente
SELECT * FROM app.emag_offer_syncs ORDER BY created_at DESC LIMIT 5;

-- Verifică produse
SELECT COUNT(*) FROM app.emag_products;
```

## 🚨 Troubleshooting

### 1. Conexiune Bază de Date

```bash
# Test conexiune directă
docker exec -it magflow_pg psql -U app -d magflow -c "SELECT 1;"

# Test conexiune prin PgBouncer
docker exec -it magflow_app python3 -c "
from app.db import get_db
import asyncio

async def test():
    async for session in get_db():
        result = await session.execute('SELECT 1')
        print('DB Connection: OK')
        break

asyncio.run(test())
"
```

### 2. eMAG API Connection

```bash
# Test conexiune eMAG API
docker exec -it magflow_app python3 -c "
from app.emag.client import EmagAPIWrapper
import asyncio

async def test():
    async with EmagAPIWrapper() as client:
        result = await client.test_connection()
        print('eMAG Connection:', result)

asyncio.run(test())
"
```

### 3. Sincronizare Produse

```bash
# Rulează sincronizare manual
docker exec -it magflow_app python3 -c "
from app.emag.services.offer_sync_service import OfferSyncService
import asyncio

async def sync():
    service = OfferSyncService()
    await service.sync_all_offers()

asyncio.run(sync())
"
```

## 📚 Documentație Suplimentară

- [API Documentation](../docs/API.md)
- [Database Schema](../docs/DATABASE.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Development Guide](../docs/DEVELOPMENT.md)

## 🎯 Best Practices

1. **Folosește environment variables** pentru toate configurațiile
1. **Testează conexiunile** înainte de development
1. **Verifică logs** pentru debugging
1. **Folosește volume mounts** pentru configurații persistente
1. **Rulează health checks** regulat

## 🔄 Workflow Development

1. **Start services:** `docker-compose up -d`
1. **Check health:** `curl http://localhost:8000/health`
1. **Run migrations:** `python scripts/init_database.py`
1. **Test API:** `curl http://localhost:8000/api/v1/sync`
1. **Check logs:** `docker-compose logs -f`

## 📞 Support

Pentru probleme:

1. Verifică logs: `docker-compose logs`
1. Testează conexiuni: vezi secțiunea Troubleshooting
1. Consultă documentația în directorul docs/
1. Verifică issues pe GitHub
