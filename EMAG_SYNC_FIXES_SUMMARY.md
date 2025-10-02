# eMAG Product Sync - Bug Fixes & Improvements

**Date:** 2025-10-01  
**Status:** ✅ COMPLETED

## 🐛 Probleme Identificate și Rezolvate

### 1. **CRITICAL: Eroare DB Schema - Coloana `created_at` lipsește**
**Problema:** 
```
ERROR: column "created_at" of relation "emag_sync_progress" does not exist
```

**Cauză:** Codul încerca să insereze coloana `created_at` în tabelul `emag_sync_progress`, dar aceasta nu există în schema DB.

**Soluție:**
- ✅ Eliminat `created_at` din INSERT statement în `_update_sync_progress()`
- ✅ Adăugat try-catch pentru error handling robust
- **Fișier:** `app/services/emag_product_sync_service.py` (linia 560-593)

---

### 2. **CRITICAL: Eroare AsyncIO Event Loop în Celery**
**Problema:**
```
RuntimeError: Task got Future attached to a different loop
```

**Cauză:** `asyncio.run()` creează un nou event loop, dar în Celery worker pot exista deja loop-uri active.

**Soluție:**
- ✅ Creat funcție `run_async()` care gestionează corect event loop-ul
- ✅ Înlocuit toate apelurile `asyncio.run()` cu `run_async()`
- ✅ Adăugat `nest-asyncio` în requirements pentru compatibilitate
- **Fișiere:** 
  - `app/services/tasks/emag_sync_tasks.py` (linia 26-45)
  - `requirements.txt` (linia 67)

---

### 3. **MAJOR: Sincronizare Blocată - Lipsă Timeout**
**Problema:** Sincronizarea rulează indefinit fără timeout, blocând sistemul.

**Soluție:**
- ✅ Adăugat timeout de 10 minute (configurabil) pentru `sync_all_products()`
- ✅ Implementat `asyncio.wait_for()` pentru timeout automat
- ✅ Refactorizat cod în `_sync_all_accounts()` pentru separare logică
- **Fișier:** `app/services/emag_product_sync_service.py` (linia 130-205)

---

### 4. **FEATURE: Cleanup Stuck Syncs**
**Problema:** Sincronizările blocate rămân în status "running" forever.

**Soluție:**
- ✅ Adăugat endpoint nou: `POST /api/v1/emag/products/cleanup-stuck-syncs`
- ✅ Marchează sync-urile > 15 minute ca "failed"
- ✅ Parametru configurabil `timeout_minutes` (5-60 min)
- **Fișier:** `app/api/v1/endpoints/emag_product_sync.py` (linia 533-596)

---

### 5. **UI: Buton Cleanup în Frontend**
**Soluție:**
- ✅ Adăugat funcție `cleanupStuckSyncs()` cu confirmare
- ✅ Buton "Cleanup Stuck" vizibil doar când sync rulează
- ✅ Notificări pentru succes/eroare
- **Fișier:** `admin-frontend/src/pages/EmagProductSyncV2.tsx` (linia 345-379, 744-754)

---

## 📦 Dependențe Noi

### Backend
```txt
nest-asyncio>=1.5.8,<2.0.0
```

**Motiv:** Permite rularea coroutine-urilor async în contexte unde event loop-ul este deja activ (Celery workers).

---

## 🔧 Modificări Tehnice

### Backend Changes

#### 1. `app/services/emag_product_sync_service.py`
```python
# FIX 1: Eliminat created_at din insert
async def _update_sync_progress(self, current_page: int, total_pages: int):
    # ... (fără created_at în values)
    try:
        await self.db.execute(stmt)
        await self.db.commit()
    except Exception as e:
        logger.error(f"Failed to update sync progress: {e}")
        await self.db.rollback()

# FIX 2: Adăugat timeout
async def sync_all_products(
    self,
    timeout_seconds: int = 600,  # 10 min default
    ...
):
    try:
        await asyncio.wait_for(
            self._sync_all_accounts(...),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        error_msg = f"Product sync timed out after {timeout_seconds} seconds"
        logger.error(error_msg)
        await self._complete_sync_log(sync_log, "failed", error_msg)
        raise ServiceError(error_msg)
```

#### 2. `app/services/tasks/emag_sync_tasks.py`
```python
# FIX: Safe async execution în Celery
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

# Folosit în toate task-urile:
result = run_async(_sync_orders_async())  # în loc de asyncio.run()
```

#### 3. `app/api/v1/endpoints/emag_product_sync.py`
```python
# FEATURE: Cleanup endpoint
@router.post("/cleanup-stuck-syncs")
async def cleanup_stuck_syncs(
    timeout_minutes: int = Query(default=15, ge=5, le=60),
    ...
):
    cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    # Find & mark stuck syncs as failed
    stuck_syncs = await db.execute(
        select(EmagSyncLog).where(
            EmagSyncLog.sync_type == "products",
            EmagSyncLog.status == "running",
            EmagSyncLog.started_at < cutoff_time,
        )
    )
    
    for sync in stuck_syncs:
        sync.status = "failed"
        sync.errors.append({
            "error": f"Sync timed out after {timeout_minutes} minutes",
            "timestamp": datetime.utcnow().isoformat(),
        })
```

### Frontend Changes

#### `admin-frontend/src/pages/EmagProductSyncV2.tsx`
```typescript
// FEATURE: Cleanup function
const cleanupStuckSyncs = async () => {
  Modal.confirm({
    title: 'Cleanup Stuck Synchronizations',
    content: 'This will mark all synchronizations running for more than 15 minutes as failed. Continue?',
    okType: 'danger',
    onOk: async () => {
      const response = await api.post('/emag/products/cleanup-stuck-syncs', null, {
        params: { timeout_minutes: 15 }
      })
      
      notificationApi.success({
        message: 'Cleanup Successful',
        description: `Cleaned up ${response.data.data.cleaned_count} stuck synchronizations`
      })
      
      await fetchSyncStatus()
      await fetchStatistics()
    }
  })
}

// UI: Buton în header (vizibil doar când sync rulează)
{syncStatus.is_running && (
  <Tooltip title="Cleanup stuck synchronizations (running > 15 min)">
    <Button danger icon={<CloseCircleOutlined />} onClick={cleanupStuckSyncs}>
      Cleanup Stuck
    </Button>
  </Tooltip>
)}
```

---

## 🚀 Deployment

### 1. Rebuild Containers
```bash
docker-compose down
docker-compose up -d --build
```

### 2. Verificare
```bash
# Check containers
docker ps

# Check logs
docker logs magflow_worker --tail 50
docker logs magflow_app --tail 50

# Check DB
docker exec magflow_db psql -U app -d magflow -c "\d emag_sync_progress"
```

---

## ✅ Testing Checklist

### Backend
- [x] Sincronizare MAIN account funcțională
- [x] Sincronizare FBE account funcțională
- [x] Sincronizare BOTH accounts funcțională
- [x] Timeout funcționează după 10 minute
- [x] Progress tracking fără erori DB
- [x] Celery tasks rulează fără erori event loop
- [x] Cleanup endpoint funcțional

### Frontend
- [x] Connection tests pentru MAIN/FBE
- [x] Start sync cu opțiuni configurabile
- [x] Progress monitoring în real-time
- [x] Buton cleanup vizibil când sync rulează
- [x] Notificări pentru toate acțiunile
- [x] Export CSV funcțional
- [x] Filtrare și căutare produse

---

## 📊 Îmbunătățiri Adiționale Recomandate

### 1. **Rate Limiting pe API eMAG**
```python
# În emag_api_client.py
from asyncio import Semaphore

class EmagApiClient:
    def __init__(self, ..., max_concurrent_requests=3):
        self._semaphore = Semaphore(max_concurrent_requests)
    
    async def _request(self, ...):
        async with self._semaphore:
            # Existing request logic
```

### 2. **Retry Logic Îmbunătățit**
```python
# În emag_product_sync_service.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def _fetch_products_page(self, ...):
    # Existing fetch logic
```

### 3. **Monitoring cu Prometheus**
```python
# Adăugare metrici
from prometheus_client import Counter, Histogram

sync_duration = Histogram('emag_sync_duration_seconds', 'Sync duration')
sync_products_total = Counter('emag_sync_products_total', 'Total products synced')
sync_errors_total = Counter('emag_sync_errors_total', 'Total sync errors')
```

### 4. **Webhook Notifications**
```python
# Notificare la finalizare sync
async def _complete_sync_log(self, sync_log, status, error=None):
    # Existing logic
    
    if status == "completed":
        await send_webhook_notification({
            "event": "sync_completed",
            "account": self.account_type,
            "stats": self._sync_stats
        })
```

---

## 🔍 Debugging Tips

### Verificare Sync Blocat
```sql
-- Găsește sync-uri blocate
SELECT id, account_type, operation, started_at, 
       EXTRACT(EPOCH FROM (NOW() - started_at))/60 as minutes_running
FROM emag_sync_logs 
WHERE status = 'running' 
  AND sync_type = 'products'
ORDER BY started_at DESC;

-- Cleanup manual
UPDATE emag_sync_logs 
SET status = 'failed', 
    completed_at = NOW(),
    errors = jsonb_build_array(
        jsonb_build_object(
            'error', 'Manually cleaned up',
            'timestamp', NOW()
        )
    )
WHERE status = 'running' 
  AND started_at < NOW() - INTERVAL '15 minutes';
```

### Check Celery Worker
```bash
# Verificare task-uri active
docker exec magflow_worker celery -A app.worker:celery_app inspect active

# Verificare task-uri scheduled
docker exec magflow_worker celery -A app.worker:celery_app inspect scheduled

# Restart worker dacă e necesar
docker restart magflow_worker
```

---

## 📝 Notes

1. **nest-asyncio** este necesar doar pentru Celery workers - nu afectează FastAPI
2. Timeout-ul de 10 minute este configurabil prin parametrul `timeout_seconds`
3. Cleanup endpoint poate fi apelat manual sau automatizat cu cron
4. Progress tracking folosește UPSERT pentru a evita duplicate entries

---

## 🎯 Rezultate

✅ **Sincronizarea funcționează corect** pentru ambele conturi (MAIN + FBE)  
✅ **Nu mai există erori de DB schema**  
✅ **Nu mai există erori de event loop**  
✅ **Timeout previne blocarea indefinită**  
✅ **Cleanup permite recuperarea din stări blocate**  
✅ **UI oferă control complet și vizibilitate**

---

**Autor:** Cascade AI  
**Review:** Pending  
**Deployment:** Ready for Production
