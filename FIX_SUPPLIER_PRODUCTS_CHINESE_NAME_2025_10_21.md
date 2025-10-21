# Fix: Afișare Nume Chinezesc în Pagina "Produse Furnizori" - 21 Octombrie 2025

## Problema Identificată

În pagina "Produse Furnizori", când se apăsa butonul "Vezi detalii", în modal-ul de detalii se afișa "Adaugă nume chinezesc" în loc de numele chinezesc complet care era vizibil în tabel.

### Exemplu Concret
- **În tabel**: Se afișa corect "微波多普勒无线雷达探测器探头传感器模块10.525GHz HB100带底板"
- **În modal**: Se afișa "Adaugă nume chinezesc"

## Analiza Problemei

### Investigație Bază de Date

Am descoperit că există două scenarii pentru stocarea numelor chinezești în `app.supplier_products`:

#### Scenariul 1: Produse cu câmpuri separate (Exemplu: ID 5987)
```sql
supplier_product_name: "HBA368"  -- SKU/Nume scurt
supplier_product_chinese_name: "微波多普勒无线雷达探测器探头传感器模块10.525GHz HB100带底板"  -- Nume complet
```

#### Scenariul 2: Produse cu nume chinezesc în câmpul principal (Exemplu: ID 7614)
```sql
supplier_product_name: "微波多普勒无线雷达探测器探头传感器模块10.525GHz HB100带底板"  -- Nume complet
supplier_product_chinese_name: NULL  -- Gol
```

### Statistici Furnizor TZT

```sql
Total produse: 2558
- Cu supplier_product_chinese_name populat: 652 (25.5%)
- Fără supplier_product_chinese_name: 1906 (74.5%)
```

**Concluzie**: Majoritatea produselor (74.5%) au numele chinezesc doar în `supplier_product_name`, nu în `supplier_product_chinese_name`.

### Cauza Root

#### 1. Frontend - Inconsistență în Logică

**În tabel** (`SupplierProducts.tsx`, linia 729):
```typescript
{record.supplier_product_chinese_name || record.supplier_product_name}  // ✓ Corect
```

**În modal** (`SupplierProducts.tsx`, linia 1419 - ÎNAINTE):
```typescript
{selectedProduct.supplier_product_chinese_name ? (  // ✗ Incomplet
  // Afișează numele
) : (
  // Afișează "Adaugă nume chinezesc"
)}
```

Problema: Modal-ul verifica DOAR `supplier_product_chinese_name`, ignorând `supplier_product_name`.

#### 2. Backend - Endpoint Incomplet

Endpoint-ul `GET /suppliers/{supplier_id}/products/{product_id}` nu returna câmpurile:
- `supplier_product_chinese_name`
- `supplier_product_specification`
- `supplier_image_url`

#### 3. Backend - Search Incomplet

Endpoint-ul `GET /suppliers/{supplier_id}/products` căuta DOAR în `supplier_product_name`, nu și în `supplier_product_chinese_name`.

## Modificări Implementate

### 1. Frontend - Modal Detalii Produs

**Fișier**: `/admin-frontend/src/pages/suppliers/SupplierProducts.tsx`

**Linia 1419-1429**: Actualizat logica pentru a include fallback la `supplier_product_name`:

```typescript
// ÎNAINTE
{selectedProduct.supplier_product_chinese_name ? (
  <Text>🇨🇳 {selectedProduct.supplier_product_chinese_name}</Text>
) : (
  <Button>Adaugă nume chinezesc</Button>
)}

// DUPĂ
{(selectedProduct.supplier_product_chinese_name || selectedProduct.supplier_product_name) ? (
  <Text>🇨🇳 {selectedProduct.supplier_product_chinese_name || selectedProduct.supplier_product_name}</Text>
) : (
  <Button>Adaugă nume chinezesc</Button>
)}
```

### 2. Backend - Endpoint GET Product Details

**Fișier**: `/app/api/v1/endpoints/suppliers/suppliers.py`

**Linia 1188-1191**: Adăugat câmpuri lipsă în răspuns:

```python
"data": {
    "id": supplier_product.id,
    "supplier_id": supplier_product.supplier_id,
    "supplier_product_name": supplier_product.supplier_product_name,
    "supplier_product_chinese_name": supplier_product.supplier_product_chinese_name,  # NOU
    "supplier_product_specification": supplier_product.supplier_product_specification,  # NOU
    "supplier_product_url": supplier_product.supplier_product_url,
    "supplier_image_url": supplier_product.supplier_image_url,  # NOU
    # ... rest of fields
}
```

### 3. Backend - Search în Ambele Câmpuri

**Fișier**: `/app/api/v1/endpoints/suppliers/suppliers.py`

**Linia 457-461**: Actualizat search query:

```python
# ÎNAINTE
if search:
    search_filter = f"%{search}%"
    query = query.where(
        or_(
            SupplierProduct.supplier_product_name.ilike(search_filter),
        )
    )

# DUPĂ
if search:
    search_filter = f"%{search}%"
    query = query.where(
        or_(
            SupplierProduct.supplier_product_name.ilike(search_filter),
            SupplierProduct.supplier_product_chinese_name.ilike(search_filter),  # NOU
        )
    )
```

**Linia 487-492**: Actualizat count query similar.

## Logica de Fallback Implementată

În toate locurile modificate, s-a implementat logica:

```typescript
supplier_product_chinese_name || supplier_product_name
```

Aceasta asigură că:
1. Dacă există `supplier_product_chinese_name`, acesta va fi afișat
2. Dacă nu există, se va afișa `supplier_product_name` (care poate conține numele chinezesc)
3. Doar dacă ambele lipsesc, se afișează "Adaugă nume chinezesc"

## Consistență în Aplicație

Această logică este acum consistentă în:
- ✅ Tabel produse furnizori
- ✅ Modal detalii produs
- ✅ Pagina Product Matching (fix anterior)
- ✅ Pagina Supplier Matching (fix anterior)
- ✅ Endpoint-uri API

## Testare

După implementarea modificărilor:

1. ✅ Backend restartat cu succes
2. ✅ Search funcționează în ambele câmpuri (`supplier_product_name` și `supplier_product_chinese_name`)
3. ✅ Modal-ul afișează corect numele chinezesc pentru toate produsele
4. ✅ Endpoint-ul GET product details returnează toate câmpurile necesare

## Impact

- **Zero breaking changes** - Logica de fallback asigură compatibilitatea cu toate datele existente
- **Îmbunătățire UX** - Utilizatorii văd acum numele chinezesc în modal, consistent cu tabelul
- **Search îmbunătățit** - Căutarea funcționează acum în ambele câmpuri
- **Consistență** - Toate paginile folosesc aceeași logică de afișare

## Problema Structurală Identificată

### Date Inconsistente în Baza de Date

Există două pattern-uri de stocare a numelor chinezești:

**Pattern 1**: Câmpuri separate (25.5% din produse)
```
supplier_product_name: "SKU/Cod"
supplier_product_chinese_name: "Nume chinezesc complet"
```

**Pattern 2**: Nume chinezesc în câmpul principal (74.5% din produse)
```
supplier_product_name: "Nume chinezesc complet"
supplier_product_chinese_name: NULL
```

### Cauze Posibile

1. **Import din surse diferite**: Google Sheets vs. scraping vs. manual
2. **Evoluție în timp**: Schimbări în logica de import
3. **Lipsă validare**: Nu există validări la import pentru a asigura consistența

## Recomandări pe Termen Lung

### 1. Migrare Date (Prioritate: Medie)

Creați un script de migrare pentru a standardiza datele:

```python
# Pseudo-cod
for product in supplier_products:
    if product.supplier_product_chinese_name is None:
        # Verifică dacă supplier_product_name conține caractere chinezești
        if contains_chinese_characters(product.supplier_product_name):
            # Mută numele chinezesc în câmpul dedicat
            product.supplier_product_chinese_name = product.supplier_product_name
            # Încearcă să extragi SKU-ul din alte surse
            product.supplier_product_name = extract_sku(product) or product.supplier_product_name
```

### 2. Validare la Import (Prioritate: Ridicată)

Adăugați validări în serviciile de import:

```python
def validate_supplier_product(product_data):
    # Asigură că numele chinezesc este în câmpul corect
    if contains_chinese_characters(product_data.get('name')):
        product_data['supplier_product_chinese_name'] = product_data['name']
        # Extrage SKU separat
        product_data['supplier_product_name'] = extract_sku(product_data)
```

### 3. Documentare (Prioritate: Ridicată)

Documentați clar în cod și în documentația API:
- `supplier_product_name`: SKU sau identificator scurt
- `supplier_product_chinese_name`: Nume complet în limba chineză

### 4. UI pentru Corectare Manuală (Prioritate: Scăzută)

Adăugați în interfață un tool pentru a identifica și corecta produsele cu date inconsistente.

## Fișiere Modificate

1. `/admin-frontend/src/pages/suppliers/SupplierProducts.tsx` - Liniile 1419-1429
2. `/app/api/v1/endpoints/suppliers/suppliers.py` - Liniile 457-461, 487-492, 1188-1191

## Fișiere Conexe

Acest fix este complementar cu:
- `FIX_CHINESE_NAME_DISPLAY_2025_10_21.md` - Fix pentru Product Matching
- `RECOMANDARI_STRUCTURA_NUME_PRODUSE_2025_10_21.md` - Recomandări structurale

## Data Implementării

21 Octombrie 2025, 16:00 UTC+03:00

## Autor

Cascade AI - Deep Analysis & Systematic Fixes
