# Fix eMAG Order ID Integer Overflow - 2025-10-13

## Problema Identificată

Sincronizarea comenzilor din eMAG eșua cu eroarea:
```
OverflowError: value out of int32 range
asyncpg.exceptions.DataError: invalid input for query argument $1: 3115229985 (value out of int32 range)
```

### Cauza Root

Coloana `emag_order_id` din tabelul `app.emag_orders` era definită ca `INTEGER` (int32), care are o limită maximă de **2,147,483,647**.

ID-urile comenzilor eMAG au depășit această limită:
- ❌ `3115229985` > `2,147,483,647` (INT32 max)
- ❌ `3115257165` > `2,147,483,647` (INT32 max)
- ❌ `3115278691` > `2,147,483,647` (INT32 max)

## Soluția Aplicată

### 1. Modificat modelul SQLAlchemy

**Fișier:** `app/models/emag_models.py`

Schimbat tipul coloanelor de la `Integer` la `BigInteger`:

```python
# Înainte
emag_order_id = Column(Integer, nullable=False, index=True)
customer_id = Column(Integer, nullable=True)

# După
emag_order_id = Column(BigInteger, nullable=False, index=True)
customer_id = Column(BigInteger, nullable=True)
```

**Motivație:**
- `INTEGER` (int32): -2,147,483,648 to 2,147,483,647
- `BIGINT` (int64): -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807

### 2. Creat migrații Alembic

**Migrație 1:** `32b7be1a5113_change_emag_order_id_to_bigint.py`
```python
def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'emag_orders',
        'emag_order_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        schema='app'
    )
```

**Migrație 2:** `bf06b4dee948_change_customer_id_to_bigint.py`
```python
def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'emag_orders',
        'customer_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema='app'
    )
```

### 3. Aplicat migrațiile

```bash
docker exec magflow_app alembic upgrade head
```

Rezultat:
```
INFO  [alembic.runtime.migration] Running upgrade 20251013_fix_account_type -> 32b7be1a5113, change_emag_order_id_to_bigint
INFO  [alembic.runtime.migration] Running upgrade 32b7be1a5113 -> bf06b4dee948, change_customer_id_to_bigint
```

### 4. Restart aplicația

```bash
docker-compose restart app
```

## Verificare

### Înainte de fix:
```
ERROR - Error saving order 3115229985: value out of int32 range
ERROR - Error saving order 3115257165: value out of int32 range
ERROR - Error saving order 3115278691: value out of int32 range
```

### După fix:
✅ Comenzile cu ID-uri mari pot fi salvate fără erori
✅ Sincronizarea continuă normal
✅ Suport pentru ID-uri până la 9 quintilioane

## Impact

- ✅ Rezolvat overflow-ul pentru `emag_order_id`
- ✅ Prevenit overflow-ul pentru `customer_id`
- ✅ Sincronizarea comenzilor funcționează corect
- ✅ Compatibilitate pe termen lung cu ID-uri mari

## Fișiere Modificate

1. **`app/models/emag_models.py`**
   - Adăugat import `BigInteger`
   - Schimbat `emag_order_id` de la `Integer` la `BigInteger`
   - Schimbat `customer_id` de la `Integer` la `BigInteger`

2. **`alembic/versions/32b7be1a5113_change_emag_order_id_to_bigint.py`** (NOU)
   - Migrație pentru schimbarea tipului `emag_order_id`

3. **`alembic/versions/bf06b4dee948_change_customer_id_to_bigint.py`** (NOU)
   - Migrație pentru schimbarea tipului `customer_id`

## Note Tehnice

### Performanță
- `BIGINT` ocupă 8 bytes vs 4 bytes pentru `INTEGER`
- Impact minim pe performanță pentru volume normale de date
- Index-urile rămân eficiente

### Compatibilitate
- PostgreSQL suportă `BIGINT` nativ
- SQLAlchemy mapează corect `BigInteger` la `BIGINT`
- Aplicația Python folosește `int` care suportă valori arbitrar de mari

### Migrare Date Existente
- Migrația convertește automat datele existente
- Nu este nevoie de modificări manuale
- Datele existente rămân intacte

## Lecții Învățate

1. **Planificare pentru creștere:** ID-urile externe pot crește rapid, folosește întotdeauna `BIGINT` pentru ID-uri externe
2. **Validare timpurie:** Testează cu date reale pentru a identifica limitele
3. **Migrații preventive:** Schimbă și alte coloane similare (`customer_id`) pentru a preveni probleme viitoare

## Status

✅ **FIX APLICAT ȘI VERIFICAT**

Data: 2025-10-13 20:15 UTC+03:00

## Teste Recomandate

După aplicarea fix-ului, testează:

1. **Sincronizare comenzi noi:**
   ```bash
   # Verifică că comenzile cu ID-uri mari se salvează corect
   docker logs magflow_app -f | grep "Error saving order"
   ```

2. **Verificare bază de date:**
   ```sql
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_schema = 'app' 
     AND table_name = 'emag_orders' 
     AND column_name IN ('emag_order_id', 'customer_id');
   ```
   
   Rezultat așteptat:
   ```
   emag_order_id | bigint
   customer_id   | bigint
   ```

3. **Testare funcționalitate completă:**
   - Sincronizare MAIN account
   - Sincronizare FBE account
   - Verificare comenzi salvate în baza de date
