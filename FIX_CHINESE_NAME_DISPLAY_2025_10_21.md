# Fix: Afișare Nume Chinezesc în Product Matching - 21 Octombrie 2025

## Problema Identificată

În pagina "Product Matching", când se apăsa butonul "Vezi Detalii", în secțiunea "Produs Furnizor (1688.com)" se afișa doar SKU-ul produsului (ex: "HBA368") în loc de numele chinezesc complet (ex: "微波多普勒无线雷达探测器探头传感器模块10.525GHz HB100带底板").

## Analiza Problemei

### Structura Datelor în Baza de Date

Modelul `SupplierProduct` are două câmpuri separate:
- `supplier_product_name` (String 1000) - Numele principal/SKU
- `supplier_product_chinese_name` (String 500) - Numele chinezesc complet

Exemplu din baza de date pentru produsul cu ID 5987:
```
supplier_product_name: "HBA368"
supplier_product_chinese_name: "微波多普勒无线雷达探测器探头传感器模块10.525GHz HB100带底板"
```

### Cauza Root

În endpoint-ul `/api/v1/suppliers/{supplier_id}/products/match` (fișier: `app/api/v1/endpoints/suppliers/suppliers.py`), la linia 706, se returna:

```python
"name_chinese": match.supplier_product_name,
```

În loc de:

```python
"name_chinese": match.supplier_product_chinese_name or match.supplier_product_name,
```

## Modificări Implementate

### 1. Backend - API Endpoint

**Fișier**: `/app/api/v1/endpoints/suppliers/suppliers.py`

**Linia 706**: Modificat pentru a returna numele chinezesc complet dacă există:

```python
"supplier_product": {
    "name_chinese": match.supplier_product_chinese_name or match.supplier_product_name,
    "price": match.supplier_price,
    "currency": match.supplier_currency,
    "image_url": match.supplier_image_url,
    "url": match.supplier_product_url,
},
```

### 2. Frontend - Supplier Matching Page

**Fișier**: `/admin-frontend/src/pages/suppliers/SupplierMatching.tsx`

**Modificări**:

1. **Linia 1252** - Alert în modal de confirmare:
```typescript
<Text strong>{selectedProduct.supplier_product_chinese_name || selectedProduct.supplier_product_name}</Text>
```

2. **Linia 1336** - Afișare în modal de detalii:
```typescript
{selectedProduct.supplier_product_chinese_name || selectedProduct.supplier_product_name}
```

**Nota**: În tabel (linia 592), logica corectă era deja implementată:
```typescript
{record.supplier_product_chinese_name || record.supplier_product_name}
```

### 3. Frontend - Product Matching Page

**Fișier**: `/admin-frontend/src/pages/products/ProductMatching.tsx`

**Nicio modificare necesară** - Pagina folosește deja `supplier_product.name_chinese` care acum primește valoarea corectă de la backend.

## Logica de Fallback

În toate locurile modificate, s-a implementat logica de fallback:

```typescript
supplier_product_chinese_name || supplier_product_name
```

Aceasta asigură că:
1. Dacă există `supplier_product_chinese_name`, acesta va fi afișat (numele chinezesc complet)
2. Dacă nu există, se va afișa `supplier_product_name` (SKU/nume scurt)

## Consistență în Aplicație

Această logică este acum consistentă cu alte părți ale aplicației:

- `/app/api/v1/endpoints/inventory/low_stock_suppliers.py` (linia 541-542)
- `/app/services/jieba_matching_service.py` (linia 235, 374, 488)
- `/admin-frontend/src/pages/suppliers/SupplierMatching.tsx` (tabel - linia 592)

## Testare

După implementarea modificărilor:

1. ✅ Backend restartat cu succes
2. ✅ Endpoint-ul `/api/v1/suppliers/{supplier_id}/products/match` returnează acum numele chinezesc complet
3. ✅ Frontend-ul afișează corect numele chinezesc în toate locurile:
   - Tabel principal
   - Modal de confirmare
   - Modal de detalii

## Impact

- **Zero breaking changes** - Logica de fallback asigură compatibilitatea cu date existente
- **Îmbunătățire UX** - Utilizatorii văd acum numele chinezesc complet în loc de SKU
- **Consistență** - Toate paginile afișează acum același format de date

## Recomandări pentru Viitor

1. **Standardizare**: Considerați standardizarea câmpurilor în baza de date:
   - `supplier_product_name` → SKU/identificator scurt
   - `supplier_product_chinese_name` → Nume complet chinezesc
   - `supplier_product_english_name` → Nume tradus în engleză (opțional)

2. **Validare**: Adăugați validări la import pentru a asigura că `supplier_product_chinese_name` este populat când este disponibil

3. **Documentație**: Actualizați documentația API pentru a clarifica diferența între cele două câmpuri

## Fișiere Modificate

1. `/app/api/v1/endpoints/suppliers/suppliers.py` - Linia 706
2. `/admin-frontend/src/pages/suppliers/SupplierMatching.tsx` - Liniile 1252, 1336

## Data Implementării

21 Octombrie 2025, 15:30 UTC+03:00
