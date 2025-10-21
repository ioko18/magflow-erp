# Fix Timezone Issue - Display Order Update - 17 Octombrie 2025

## Problemă Raportată

Utilizatorul a întâmpinat erori 500 la:
- Ordonarea produselor (drag & drop)
- Modificarea cifrei din coloana "Ordine"

### Eroare Specifică

```
(sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.DataError'>: 
invalid input for query argument $2: datetime.datetime(2025, 10, 17, 20, 5, 3... 
(can't subtract offset-naive and offset-aware datetimes)

[SQL: UPDATE app.products SET display_order=$1::INTEGER, updated_at=$2::TIMESTAMP WITHOUT TIME ZONE 
WHERE app.products.id = $3::INTEGER]

[parameters: (4, datetime.datetime(2025, 10, 17, 20, 5, 34, 662106, tzinfo=datetime.timezone.utc), 5)]
```

## Cauza Principală

### Inconsistență Timezone

Coloana `updated_at` din tabelul `app.products` este definită ca `TIMESTAMP WITHOUT TIME ZONE`, dar codul Python seta valoarea folosind `datetime.now(UTC)` care returnează un datetime **cu timezone** (timezone-aware).

PostgreSQL nu poate compara sau stoca datetime-uri cu timezone într-o coloană `TIMESTAMP WITHOUT TIME ZONE`, rezultând eroarea:
> "can't subtract offset-naive and offset-aware datetimes"

### Locații Problematice

**Fișier**: `app/api/v1/endpoints/products/product_management.py`

1. **Linia 1276** - Endpoint `POST /{product_id}/display-order`
   ```python
   product.updated_at = datetime.now(UTC)  # ❌ CU timezone
   ```

2. **Linia 1374** - Endpoint `DELETE /{product_id}/display-order`
   ```python
   product.updated_at = datetime.now(UTC)  # ❌ CU timezone
   ```

## Soluție Implementată

### Modificări în `product_management.py`

Am adăugat `.replace(tzinfo=None)` pentru a înlătura timezone-ul din datetime:

#### 1. Update Display Order (Linia 1276)

**Înainte**:
```python
product.display_order = new_order
product.updated_at = datetime.now(UTC)  # ❌ Eroare
```

**După**:
```python
product.display_order = new_order
product.updated_at = datetime.now(UTC).replace(tzinfo=None)  # ✅ Corect
```

#### 2. Remove Display Order (Linia 1374)

**Înainte**:
```python
product.display_order = None
product.updated_at = datetime.now(UTC)  # ❌ Eroare
```

**După**:
```python
product.display_order = None
product.updated_at = datetime.now(UTC).replace(tzinfo=None)  # ✅ Corect
```

### Consistență în Cod

Am verificat că toate celelalte locuri din `product_management.py` folosesc deja pattern-ul corect:

```python
# ✅ Exemplu corect din alte părți ale codului
product.updated_at = datetime.now(UTC).replace(tzinfo=None)
```

Locații verificate și corecte:
- ✅ Linia 984 - Update product fields
- ✅ Linia 1025 - Soft delete product
- ✅ Linia 1085 - Update product status
- ✅ Linia 1169 - Bulk status update
- ✅ Linia 1334 - Bulk reorder products

## Testare

### Test 1: Update Display Order
```bash
POST /api/v1/products/199/display-order
{
  "display_order": 4,
  "auto_adjust": true
}
```
**Rezultat**: ✅ SUCCESS (înainte: 500 Error)

### Test 2: Update Display Order (alt produs)
```bash
POST /api/v1/products/5/display-order
{
  "display_order": 10,
  "auto_adjust": true
}
```
**Rezultat**: ✅ SUCCESS (înainte: 500 Error)

### Test 3: Remove Display Order
```bash
DELETE /api/v1/products/199/display-order
```
**Rezultat**: ✅ SUCCESS

### Test 4: Backend Health
```bash
GET /api/v1/health/live
```
**Rezultat**: ✅ HEALTHY

## Explicație Tehnică

### Diferența între Timezone-Aware și Timezone-Naive

#### Timezone-Aware (CU timezone)
```python
datetime.now(UTC)
# Rezultat: datetime.datetime(2025, 10, 17, 20, 5, 34, 662106, tzinfo=datetime.timezone.utc)
```

#### Timezone-Naive (FĂRĂ timezone)
```python
datetime.now(UTC).replace(tzinfo=None)
# Rezultat: datetime.datetime(2025, 10, 17, 20, 5, 34, 662106)
```

### Tipuri de Coloane PostgreSQL

#### TIMESTAMP WITHOUT TIME ZONE
```sql
updated_at TIMESTAMP WITHOUT TIME ZONE
```
- Stochează doar data și ora, **fără** informații despre timezone
- Necesită datetime-uri **naive** (fără tzinfo)
- Folosit în modelul `Product`

#### TIMESTAMP WITH TIME ZONE
```sql
updated_at TIMESTAMP WITH TIME ZONE
```
- Stochează data, ora **și** timezone
- Acceptă datetime-uri **aware** (cu tzinfo)
- Nu este folosit în acest caz

## Impact și Beneficii

### ✅ Probleme Rezolvate

1. **Ordonare produse** - Funcționează corect
2. **Modificare ordine** - Funcționează corect
3. **Drag & drop** - Funcționează corect
4. **Ștergere ordine** - Funcționează corect

### ✅ Îmbunătățiri

1. **Consistență** - Toate update-urile folosesc același pattern
2. **Stabilitate** - Nu mai apar erori de timezone
3. **Performanță** - Queries executate corect

### ⚠️ Alte Fișiere cu Aceeași Problemă

Am identificat alte fișiere care ar putea avea aceeași problemă (dar nu afectează funcționalitatea curentă):

```
app/models_backup/user.py
app/services/catalog_service.py (comentat)
app/services/communication/sms_service.py
app/services/orders/payment_service.py
```

**Recomandare**: Acestea pot fi corectate în viitor pentru consistență completă.

## Verificare Finală

### Backend Status
```
✅ Container: RUNNING
✅ Health: HEALTHY
✅ Migrations: UP TO DATE
✅ API: FUNCTIONAL
```

### Endpoints Testate
```
✅ POST /api/v1/products/{id}/display-order
✅ DELETE /api/v1/products/{id}/display-order
✅ POST /api/v1/products/reorder
✅ GET /api/v1/health/live
```

## Recomandări pentru Viitor

### 1. Standardizare Timezone
Considerați migrarea la `TIMESTAMP WITH TIME ZONE` pentru toate coloanele de timp:

```sql
ALTER TABLE app.products 
ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;
```

**Avantaje**:
- Suport nativ pentru timezone-aware datetimes
- Mai puțin cod de conversie
- Mai puține erori

### 2. Helper Function
Creați o funcție helper pentru a evita repetarea codului:

```python
def get_naive_utc_now() -> datetime:
    """Get current UTC time without timezone info."""
    return datetime.now(UTC).replace(tzinfo=None)

# Utilizare
product.updated_at = get_naive_utc_now()
```

### 3. Linting Rule
Adăugați o regulă de linting pentru a detecta pattern-ul problematic:

```python
# Detectează: datetime.now(UTC) fără .replace(tzinfo=None)
# În contextul de assignment la câmpuri *_at
```

## Concluzie

✅ **Problema de timezone la ordonarea produselor a fost rezolvată complet**

Modificările sunt minime (doar 2 linii), dar esențiale pentru funcționalitatea corectă a sistemului de ordonare produse. Backend-ul a fost restartat și funcționează corect.

**Data**: 17 Octombrie 2025, 23:09 (UTC+3)
**Status**: ✅ REZOLVAT - TESTAT ȘI VERIFICAT
**Impact**: CRITIC → REZOLVAT
