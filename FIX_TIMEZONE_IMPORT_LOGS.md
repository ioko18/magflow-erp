# Fix Timezone Error - ImportLog Model

**Data**: 2025-10-13 04:12 UTC+3  
**Status**: ✅ **REZOLVAT**

---

## 🐛 Problema Identificată

### Eroare
```
(sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.DataError'>: 
invalid input for query argument $10: datetime.datetime(2025, 10, 13, 1, 4, 30... 
(can't subtract offset-naive and offset-aware datetimes)
```

### Cauza
Modelul `ImportLog` avea coloanele `started_at` și `completed_at` definite ca:
- **În model**: `DateTime` (fără timezone)
- **În baza de date**: `TIMESTAMP WITHOUT TIME ZONE`

Dar aplicația trimitea datetime-uri **cu timezone** (`datetime.timezone.utc`), cauzând eroarea.

---

## ✅ Soluție Aplicată

### 1. Actualizat Modelul
**Fișier**: `app/models/product_mapping.py`

**Înainte**:
```python
started_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
)
completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**După**:
```python
started_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
)
completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 2. Creat Migrare
**Fișier**: `alembic/versions/20251013_fix_import_logs_timezone.py`

```sql
-- Convert started_at to TIMESTAMP WITH TIME ZONE
ALTER TABLE app.import_logs 
ALTER COLUMN started_at TYPE TIMESTAMP WITH TIME ZONE 
USING started_at AT TIME ZONE 'UTC';

-- Convert completed_at to TIMESTAMP WITH TIME ZONE
ALTER TABLE app.import_logs 
ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE 
USING completed_at AT TIME ZONE 'UTC';
```

### 3. Aplicat Migrarea
```bash
docker compose exec app alembic upgrade head
```

### 4. Restart Aplicație
```bash
docker compose restart app worker
```

---

## 🔍 Verificare

### Structura Tabelului
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'app' 
  AND table_name = 'import_logs' 
  AND column_name IN ('started_at', 'completed_at');
```

**Rezultat**:
```
 column_name  |        data_type         
--------------+--------------------------
 completed_at | timestamp with time zone ✅
 started_at   | timestamp with time zone ✅
```

---

## 📋 Lanțul Migrărilor Actualizat

```
86f7456767fd (initial schema)
    ↓
6d303f2068d4 (emag offer tables)
    ↓
b1234f5d6c78 (metadata column)
    ↓
4242d9721c62 (missing tables)
    ↓
97aa49837ac6 (product relationships)
    ↓
20251013_fix_import_logs_tz (fix timezone) ← NEW HEAD
```

---

## 🎯 Impact

### Înainte
- ❌ Import din Google Sheets CRASH
- ❌ Eroare timezone la salvare ImportLog
- ❌ Nu se putea track importurile

### După
- ✅ Import din Google Sheets funcționează
- ✅ Datetime-uri cu timezone salvate corect
- ✅ Tracking complet al importurilor

---

## 📝 Lecții Învățate

### Best Practices pentru DateTime

1. **Folosește întotdeauna timezone**:
   ```python
   # ✅ CORECT
   DateTime(timezone=True)
   
   # ❌ GREȘIT
   DateTime  # fără timezone
   ```

2. **Consistență în aplicație**:
   - Dacă aplicația folosește `datetime.now(UTC)`, modelul trebuie `DateTime(timezone=True)`
   - Dacă aplicația folosește `datetime.now()`, modelul poate fi `DateTime` (fără timezone)

3. **Migrări pentru timezone**:
   ```sql
   ALTER COLUMN column_name TYPE TIMESTAMP WITH TIME ZONE 
   USING column_name AT TIME ZONE 'UTC'
   ```

---

## 🔧 Fișiere Modificate

1. **Model**: `app/models/product_mapping.py`
   - Actualizat `started_at` și `completed_at` la `DateTime(timezone=True)`

2. **Migrare**: `alembic/versions/20251013_fix_import_logs_timezone.py`
   - Creat migrare pentru conversie timezone

---

## ✅ Status Final

**PROBLEMA REZOLVATĂ COMPLET!**

- ✅ Model actualizat
- ✅ Migrare aplicată
- ✅ Baza de date actualizată
- ✅ Aplicație restartată
- ✅ Import funcționează corect

**Sistemul este gata pentru import din Google Sheets!** 🚀

---

**Creat**: 2025-10-13 04:12 UTC+3  
**Status**: ✅ **REZOLVAT**  
**Versiune**: 1.0
