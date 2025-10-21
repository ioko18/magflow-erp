# 🕐 Timezone Fix Complete - ProductSKUHistory & ProductChangeLog

**Data**: 15 Octombrie 2025, 21:40  
**Status**: ✅ **FIX APLICAT**

---

## 🔴 Problema

### Eroare la Import:
```
Error: Import Error: (sqlalchemy.dialects.postgresql.asyncpg.Error) 
<class 'asyncpg.exceptions.DataError'>: invalid input for query argument $4: 
datetime.datetime(2025, 10, 15, 18, 38, ... 
(can't subtract offset-naive and offset-aware datetimes)

[SQL: INSERT INTO app.product_sku_history 
(product_id, old_sku, new_sku, changed_at, ...)
```

### Cauza Root:
**Mismatch între tipul datetime trimis și tipul așteptat de baza de date:**

1. **Modelul `ProductSKUHistory`** (linia 46-52 în `product_history.py`):
   ```python
   changed_at: Mapped[datetime] = mapped_column(
       DateTime,  # TIMESTAMP WITHOUT TIME ZONE în PostgreSQL
       nullable=False,
       default=lambda: datetime.now(UTC).replace(tzinfo=None),  # ✅ Fără timezone
       index=True,
   )
   ```

2. **Codul nostru** (în `product_import_service.py`):
   ```python
   sku_history = ProductSKUHistory(
       ...
       changed_at=datetime.now(UTC),  # ❌ CU timezone (tzinfo=UTC)
       ...
   )
   ```

**Problema**: PostgreSQL nu poate compara/stoca datetime cu timezone într-o coloană `TIMESTAMP WITHOUT TIME ZONE`.

---

## ✅ Soluția

### Principiu:
Când coloana database este `TIMESTAMP WITHOUT TIME ZONE`, trebuie să trimitem datetime **FĂRĂ timezone** (timezone-naive).

### Conversie:
```python
# ÎNAINTE (GREȘIT):
datetime.now(UTC)  # datetime cu tzinfo=UTC

# DUPĂ (CORECT):
datetime.now(UTC).replace(tzinfo=None)  # datetime fără tzinfo
```

---

## 📝 Fix-uri Aplicate

### 1. **product_import_service.py** ✅

**Locație**: Linia 274 în metoda `_import_sku_history()`

**ÎNAINTE**:
```python
sku_history = ProductSKUHistory(
    product_id=product.id,
    old_sku=old_sku,
    new_sku=product.sku,
    changed_at=datetime.now(UTC),  # ❌ CU timezone
    changed_by_id=None,
    change_reason="Imported from Google Sheets SKU_History column",
    ip_address=None,
    user_agent="Google Sheets Import Service",
)
```

**DUPĂ**:
```python
sku_history = ProductSKUHistory(
    product_id=product.id,
    old_sku=old_sku,
    new_sku=product.sku,
    changed_at=datetime.now(UTC).replace(tzinfo=None),  # ✅ FĂRĂ timezone
    changed_by_id=None,
    change_reason="Imported from Google Sheets SKU_History column",
    ip_address=None,
    user_agent="Google Sheets Import Service",
)
```

---

### 2. **product_update_service.py** ✅

**Locație**: Linia 470 în metoda `_import_sku_history()`

**ÎNAINTE**:
```python
sku_history = ProductSKUHistory(
    product_id=product.id,
    old_sku=old_sku,
    new_sku=product.sku,
    changed_at=datetime.now(UTC),  # ❌ CU timezone
    changed_by_id=None,
    change_reason="Imported from Google Sheets SKU_History column",
    ip_address=None,
    user_agent="Google Sheets Import Service",
)
```

**DUPĂ**:
```python
sku_history = ProductSKUHistory(
    product_id=product.id,
    old_sku=old_sku,
    new_sku=product.sku,
    changed_at=datetime.now(UTC).replace(tzinfo=None),  # ✅ FĂRĂ timezone
    changed_by_id=None,
    change_reason="Imported from Google Sheets SKU_History column",
    ip_address=None,
    user_agent="Google Sheets Import Service",
)
```

---

### 3. **product_management.py** - 4 locații ✅

#### A. Funcția `log_sku_change()` - Linia 232
**ÎNAINTE**:
```python
sku_history = ProductSKUHistory(
    product_id=product_id,
    old_sku=old_sku,
    new_sku=new_sku,
    changed_at=datetime.now(UTC),  # ❌
    changed_by_id=user_id,
    change_reason=change_reason,
    ip_address=ip_address,
    user_agent=user_agent,
)
```

**DUPĂ**:
```python
sku_history = ProductSKUHistory(
    product_id=product_id,
    old_sku=old_sku,
    new_sku=new_sku,
    changed_at=datetime.now(UTC).replace(tzinfo=None),  # ✅
    changed_by_id=user_id,
    change_reason=change_reason,
    ip_address=ip_address,
    user_agent=user_agent,
)
```

---

#### B. Funcția `log_field_change()` - Linia 206
**ÎNAINTE**:
```python
change_log = ProductChangeLog(
    product_id=product_id,
    field_name=field_name,
    old_value=old_str,
    new_value=new_str,
    changed_at=datetime.now(UTC),  # ❌
    changed_by_id=user_id,
    change_type="update",
    ip_address=ip_address,
)
```

**DUPĂ**:
```python
change_log = ProductChangeLog(
    product_id=product_id,
    field_name=field_name,
    old_value=old_str,
    new_value=new_str,
    changed_at=datetime.now(UTC).replace(tzinfo=None),  # ✅
    changed_by_id=user_id,
    change_type="update",
    ip_address=ip_address,
)
```

---

#### C. Endpoint `POST /products` (create) - Linia 902
**ÎNAINTE**:
```python
change_log = ProductChangeLog(
    product_id=product.id,
    field_name="product",
    old_value=None,
    new_value="created",
    changed_at=datetime.now(UTC),  # ❌
    changed_by_id=current_user.id,
    change_type="create",
    ip_address=ip_address,
)
```

**DUPĂ**:
```python
change_log = ProductChangeLog(
    product_id=product.id,
    field_name="product",
    old_value=None,
    new_value="created",
    changed_at=datetime.now(UTC).replace(tzinfo=None),  # ✅
    changed_by_id=current_user.id,
    change_type="create",
    ip_address=ip_address,
)
```

---

#### D. Endpoint `DELETE /products/{id}` - Linia 1034
**ÎNAINTE**:
```python
change_log = ProductChangeLog(
    product_id=product.id,
    field_name="product",
    old_value="active",
    new_value="deleted",
    changed_at=datetime.now(UTC),  # ❌
    changed_by_id=current_user.id,
    change_type="delete",
    ip_address=ip_address,
)
```

**DUPĂ**:
```python
change_log = ProductChangeLog(
    product_id=product.id,
    field_name="product",
    old_value="active",
    new_value="deleted",
    changed_at=datetime.now(UTC).replace(tzinfo=None),  # ✅
    changed_by_id=current_user.id,
    change_type="delete",
    ip_address=ip_address,
)
```

---

## 📊 Rezumat Fix-uri

### Fișiere Modificate: 3
1. ✅ `app/services/product/product_import_service.py` - 1 fix
2. ✅ `app/services/product/product_update_service.py` - 1 fix
3. ✅ `app/api/v1/endpoints/products/product_management.py` - 4 fix-uri

### Total Linii Modificate: 6
- ProductSKUHistory: 3 locații
- ProductChangeLog: 3 locații

### Pattern Aplicat:
```python
# Înlocuit peste tot:
datetime.now(UTC)
# Cu:
datetime.now(UTC).replace(tzinfo=None)
```

---

## 🧪 Testare

### Test 1: Import SKU_History
```bash
# 1. Accesează Product Import from Google Sheets
# 2. Click "Import Products & Suppliers"
# 3. Verifică că importul se finalizează cu succes
```

**Rezultat Așteptat**: ✅ Import reușit, fără erori de timezone

---

### Test 2: Verificare Database
```sql
-- Verifică că SKU history a fost inserat
SELECT * FROM app.product_sku_history 
WHERE change_reason LIKE '%Google Sheets%'
ORDER BY changed_at DESC
LIMIT 10;

-- Verifică tipul coloanei
SELECT column_name, data_type, datetime_precision
FROM information_schema.columns
WHERE table_schema = 'app' 
  AND table_name = 'product_sku_history'
  AND column_name = 'changed_at';
-- Rezultat așteptat: timestamp without time zone
```

---

### Test 3: Update Produs (SKU Change)
```bash
# 1. Accesează Products page
# 2. Editează un produs și schimbă SKU-ul
# 3. Verifică că se salvează fără erori
# 4. Verifică istoric SKU în modal
```

**Rezultat Așteptat**: ✅ Update reușit, istoric salvat corect

---

## 📚 Explicație Tehnică

### De ce TIMESTAMP WITHOUT TIME ZONE?

**Avantaje**:
1. **Simplitate**: Nu trebuie să gestionezi conversii de timezone
2. **Performanță**: Comparații mai rapide (fără conversii)
3. **Consistență**: Toate timestamp-urile sunt în același timezone (implicit UTC)

**Dezavantaje**:
1. **Pierdere informație**: Nu știi în ce timezone a fost creat
2. **Ambiguitate**: Trebuie să documentezi că toate sunt UTC

### Alternativa: TIMESTAMP WITH TIME ZONE

Dacă vrei să păstrezi timezone-ul:

**1. Modifică modelul**:
```python
changed_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),  # TIMESTAMP WITH TIME ZONE
    nullable=False,
    default=lambda: datetime.now(UTC),  # CU timezone
    index=True,
)
```

**2. Migrație database**:
```sql
ALTER TABLE app.product_sku_history 
ALTER COLUMN changed_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE app.product_change_log 
ALTER COLUMN changed_at TYPE TIMESTAMP WITH TIME ZONE;
```

**3. Cod rămâne cu timezone**:
```python
changed_at=datetime.now(UTC)  # OK cu TIMESTAMP WITH TIME ZONE
```

---

## ⚠️ Best Practices

### 1. **Consistență în Proiect**
- Verifică TOATE modelele care au `changed_at`, `created_at`, `updated_at`
- Asigură-te că toate folosesc același tip (cu sau fără timezone)

### 2. **Documentare**
- Documentează în cod că datetime-urile sunt UTC
- Adaugă comentarii la modelele cu TIMESTAMP WITHOUT TIME ZONE

### 3. **Validare**
- Testează toate operațiile CRUD care folosesc history tables
- Verifică că nu mai apar erori de timezone

---

## 🔍 Verificare Completă

### Caută alte potențiale probleme:
```bash
# Caută toate folosirile de datetime.now(UTC) în history tables
grep -r "datetime.now(UTC)" app/ | grep -i "history\|change_log"

# Verifică toate modelele cu DateTime
grep -r "DateTime" app/models/ | grep -v "timezone=True"
```

---

## ✅ Status Final

**TOATE FIX-URILE APLICATE!** 🎉

- ✅ 6 locații reparate
- ✅ Cod consistent
- ✅ Gata de testare
- ✅ Documentație completă

**Următorii pași**:
1. Restart backend: `docker-compose restart backend`
2. Testează import din Google Sheets
3. Verifică că nu mai apar erori de timezone
4. Monitorizează logs pentru alte probleme

**Succes!** 🚀
