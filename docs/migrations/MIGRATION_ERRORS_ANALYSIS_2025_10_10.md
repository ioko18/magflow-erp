# Analiza Erorilor de Migrare - 2025-10-10

## Problemele Identificate

### 1. **Duplicate Index Definitions** ⚠️ CRITIC

Două migrații creează indexuri pe aceleași coloane cu nume diferite:

#### Conflict 1: `updated_at` index
- **add_inventory_indexes_2025_10_10.py**: `ix_emag_products_v2_updated_at`
- **add_performance_indexes_2025_10_10.py**: `idx_emag_products_v2_updated_at`

#### Conflict 2: `is_active` index  
- **add_inventory_indexes_2025_10_10.py**: `ix_emag_products_v2_is_active` (partial index WHERE is_active = true)
- **add_performance_indexes_2025_10_10.py**: `idx_emag_products_v2_active` (partial index WHERE is_active = true)

#### Conflict 3: `account_type` index
- **add_inventory_indexes_2025_10_10.py**: `ix_emag_products_v2_account_type`
- **add_performance_indexes_2025_10_10.py**: `idx_emag_products_v2_account`

**Impact**: Încercarea de a crea același index de două ori va cauza erori.

### 2. **Migration Chain Issues** ⚠️ MEDIU

Migrații cu `down_revision` incorect sau lipsă:

| Migration File | Revision ID | Down Revision | Status |
|---------------|-------------|---------------|---------|
| `add_inventory_indexes_2025_10_10.py` | `add_inventory_indexes` | `14b0e514876f` | ❌ Orphaned |
| `add_performance_indexes_2025_10_10.py` | `perf_idx_20251010` | `bd898485abe9` | ✅ OK |
| `14b0e514876f_add_missing_supplier_columns.py` | `14b0e514876f` | `perf_idx_20251010` | ✅ OK |

**Problema**: `add_inventory_indexes` revizuiește `14b0e514876f`, dar `14b0e514876f` revizuiește `perf_idx_20251010`, creând o dependență circulară.

### 3. **Multiple Branch Heads** ⚠️ MEDIU

Există mai multe branch points în istoricul migrărilor:
- `add_section8_fields` (branchpoint)
- `c8e960008812` (branchpoint)
- `20250929_add_enhanced_emag_models` (branchpoint)
- `069bd2ae6d01` (branchpoint)
- `f8a938c16fd8` (branchpoint)

## Soluții Recomandate

### Soluție 1: Eliminarea Duplicatelor de Indexuri

**Opțiune A**: Păstrăm doar `add_performance_indexes_2025_10_10.py` (RECOMANDAT)
- Are `IF NOT EXISTS` pentru siguranță
- Folosește convenția de denumire `idx_*` (mai standard)
- Include mai multe indexuri pentru dashboard

**Opțiune B**: Combinăm ambele migrații într-una singură
- Păstrăm toate indexurile unice
- Eliminăm duplicatele
- Folosim `IF NOT EXISTS` pentru idempotență

### Soluție 2: Corectarea Lanțului de Migrări

**Pas 1**: Ștergem `add_inventory_indexes_2025_10_10.py` (duplicat)

**Pas 2**: Verificăm că lanțul este corect:
```
bd898485abe9 → perf_idx_20251010 → 14b0e514876f → (HEAD)
```

### Soluție 3: Îmbunătățiri pentru Viitor

1. **Convenție de denumire consistentă**:
   - Folosim `idx_` pentru toate indexurile noi
   - Format: `idx_{table}_{columns}_{optional_suffix}`

2. **Verificări de idempotență**:
   - Folosim `IF NOT EXISTS` pentru toate operațiile CREATE
   - Folosim `IF EXISTS` pentru toate operațiile DROP

3. **Documentație îmbunătățită**:
   - Adăugăm comentarii clare despre scopul fiecărui index
   - Documentăm query-urile care beneficiază de index

## Plan de Acțiune

### Etapa 1: Backup și Verificare ✅
- [x] Analizat toate migrațiile
- [x] Identificat conflictele
- [ ] Creat backup înainte de modificări

### Etapa 2: Corectare Migrații 🔄
- [ ] Șters `add_inventory_indexes_2025_10_10.py`
- [ ] Îmbunătățit `add_performance_indexes_2025_10_10.py`
- [ ] Verificat lanțul de migrări

### Etapa 3: Testare 🔄
- [ ] Testat migrarea pe baza de date de test
- [ ] Verificat că toate indexurile sunt create
- [ ] Verificat performanța query-urilor

### Etapa 4: Documentație 🔄
- [ ] Actualizat documentația de migrare
- [ ] Creat ghid pentru migrări viitoare
- [ ] Adăugat verificări automate

## Indexuri Finale Recomandate

### Pentru `emag_products_v2`:
1. `idx_emag_products_v2_updated_at` - pentru sortare după dată
2. `idx_emag_products_v2_active` - partial index pentru produse active
3. `idx_emag_products_v2_account` - pentru filtrare după cont
4. `idx_emag_products_v2_stock_quantity` - partial index pentru stoc scăzut
5. `idx_emag_products_v2_sku` - pentru căutare după SKU
6. `idx_emag_products_v2_part_number_key` - pentru căutare după part number
7. `idx_emag_products_v2_account_stock` - composite pentru query-uri complexe
8. `idx_emag_products_v2_sku_account` - composite pentru căutare per cont
9. `idx_emag_products_v2_name_trgm` - GIN index pentru text search

### Pentru alte tabele:
- Sales Orders: date, status, customer_id
- Products: SKU, name, created_at
- Inventory: product_id, quantity
- Customers: email, created_at

## Verificări Finale

```bash
# Verifică heads
alembic heads

# Verifică branches
alembic branches

# Verifică istoricul
alembic history --verbose

# Testează upgrade
alembic upgrade head

# Verifică starea curentă
alembic current
```
