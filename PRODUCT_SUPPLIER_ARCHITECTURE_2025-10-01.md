# Arhitectură Produse și Furnizori - MagFlow ERP

## 📋 Prezentare Generală

Sistemul MagFlow ERP folosește o arhitectură **separată dar conectată** pentru gestionarea produselor locale și produselor furnizorilor. Această abordare permite flexibilitate maximă în aprovizionare și comparare prețuri.

## 🏗️ Arhitectură Sistem

### 1. Produse Locale (app.products)

**Tabel**: `app.products`  
**Model**: `Product` (`app/models/product.py`)

```python
class Product(Base, TimestampMixin):
    id: int
    name: str                    # Nume produs (română/engleză)
    chinese_name: str | None     # 🆕 Nume chinezesc pentru matching
    sku: str                     # SKU intern unic
    description: str | None
    base_price: float
    # ... alte câmpuri
```

**Scop**:
- Catalogul principal de produse al companiei
- Produse vândute pe eMAG, site propriu, etc.
- Gestionare stocuri și prețuri de vânzare

### 2. Produse Furnizori (app.supplier_raw_products)

**Tabel**: `app.supplier_raw_products`  
**Model**: `SupplierRawProduct` (`app/models/supplier_matching.py`)

```python
class SupplierRawProduct(Base, TimestampMixin):
    id: int
    supplier_id: int             # FK la furnizor
    chinese_name: str            # Nume produs de pe 1688.com
    english_name: str | None     # Tradus automat
    price_cny: float             # Preț în Yuan
    product_url: str             # Link 1688.com
    image_url: str
    matching_status: str         # pending, matched, etc.
    product_group_id: int | None # FK la grup matching
    # ... alte câmpuri
```

**Scop**:
- Produse de pe 1688.com (Alibaba China)
- Comparare prețuri între furnizori
- Păstrare istoric prețuri
- **RĂMÂN SEPARATE** - nu se șterg după matching

### 3. Grupuri Matching (app.product_matching_groups)

**Tabel**: `app.product_matching_groups`  
**Model**: `ProductMatchingGroup` (`app/models/supplier_matching.py`)

```python
class ProductMatchingGroup(Base, TimestampMixin):
    id: int
    group_name: str              # Nume reprezentativ
    product_count: int           # Câte produse furnizori în grup
    min_price_cny: float
    max_price_cny: float
    avg_price_cny: float
    best_supplier_id: int | None
    local_product_id: int | None # 🔗 Link la produs local
    confidence_score: float
    matching_method: str         # text, image, hybrid
    status: str                  # auto_matched, manual_matched
    # ... alte câmpuri
```

**Scop**:
- Grupare produse similare de la furnizori diferiți
- Comparare prețuri
- **Link opțional** la produs local

## 🔄 Flux de Lucru

### Scenariul 1: Import și Matching Produse Furnizori

```
1. IMPORT EXCEL
   ↓
   [Supplier Raw Products] (2985 produse)
   ↓
2. RUN MATCHING (text/image/hybrid)
   ↓
   [Product Matching Groups] (836 grupuri)
   ↓
3. REVIEW & CONFIRM
   ↓
4. LINK LA PRODUS LOCAL (opțional)
   ↓
   [Product.id] ← [ProductMatchingGroup.local_product_id]
```

### Scenariul 2: Aprovizionare Flexibilă

**Situație**: Furnizor principal în vacanță

```
Produs Local: "Senzor BMP280"
  ↓ linked to
ProductMatchingGroup: "气压传感器 BMP280"
  ↓ contains
  ├─ Furnizor A: ¥12.50 (în vacanță ❌)
  ├─ Furnizor B: ¥13.20 (disponibil ✅)
  └─ Furnizor C: ¥14.00 (disponibil ✅)

→ Cumpăr de la Furnizor B (preț puțin mai mare, dar disponibil)
```

**Avantaje**:
- ✅ Produsele furnizorilor rămân în sistem
- ✅ Istoric complet de prețuri
- ✅ Flexibilitate în aprovizionare
- ✅ Backup suppliers mereu disponibili

## 🆕 Funcționalitate Nouă: Chinese Name Matching

### Problema Rezolvată

**Înainte**: Nu puteam face matching între produse locale și produse furnizori

**Acum**: Câmp `chinese_name` în `Product` model

### Cum Funcționează

```python
# Produs Local
Product(
    name="Senzor de presiune BMP280",
    chinese_name="气压传感器 BMP280",  # 🆕 Adăugat manual
    sku="BMP280-001"
)

# Produse Furnizori (automat din 1688.com)
SupplierRawProduct(
    chinese_name="气压传感器 BMP280 3.3V",
    supplier_id=1,
    price_cny=12.50
)

SupplierRawProduct(
    chinese_name="BMP280 气压传感器模块",
    supplier_id=2,
    price_cny=13.20
)

# Matching Algorithm
similarity("气压传感器 BMP280", "气压传感器 BMP280 3.3V") = 0.85
similarity("气压传感器 BMP280", "BMP280 气压传感器模块") = 0.82

→ Creează ProductMatchingGroup cu ambele produse
→ Link la Product.id prin local_product_id
```

### Implementare

**1. Migrare Bază de Date**:
```bash
# Rulează migrarea
alembic upgrade head
```

**2. Adăugare Nume Chinezești**:
```sql
-- Manual sau prin UI
UPDATE app.products 
SET chinese_name = '气压传感器 BMP280'
WHERE sku = 'BMP280-001';
```

**3. Run Matching**:
- Algoritmul va folosi `chinese_name` pentru matching
- Creează grupuri automat
- Sugerează linkuri la produse locale

## 📊 Relații Bază de Date

```
┌─────────────────┐
│   Suppliers     │
│  (furnizori)    │
└────────┬────────┘
         │ 1:N
         ↓
┌─────────────────────────┐
│ SupplierRawProducts     │
│ (produse furnizori)     │
│ - chinese_name          │
│ - price_cny             │
│ - product_group_id  ────┼──┐
└─────────────────────────┘  │
                              │ N:1
                              ↓
                    ┌──────────────────────┐
                    │ ProductMatchingGroup │
                    │ (grupuri matching)   │
                    │ - local_product_id ──┼──┐
                    └──────────────────────┘  │
                                              │ N:1
                                              ↓
                                    ┌─────────────────┐
                                    │    Products     │
                                    │ (catalog local) │
                                    │ - chinese_name  │
                                    └─────────────────┘
```

## 🎯 Best Practices

### 1. Păstrare Produse Furnizori

**❌ NU FACE**:
```python
# NU șterge produse furnizori după matching
after_matching:
    delete supplier_products  # GREȘIT!
```

**✅ FACE**:
```python
# Păstrează toate produsele furnizorilor
after_matching:
    update product_group_id  # Link la grup
    keep supplier_products   # Păstrează pentru istoric
```

**Motivație**:
- Istoric prețuri complet
- Backup suppliers disponibili
- Flexibilitate în aprovizionare
- Tracking variații prețuri

### 2. Linking Produse Locale

**Opțional, nu obligatoriu**:
```python
# Doar dacă există produs local corespondent
if local_product_exists:
    matching_group.local_product_id = product.id
else:
    matching_group.local_product_id = None  # OK!
```

**Cazuri de utilizare**:
- **Cu link**: Produse pe care le vinzi (eMAG, site)
- **Fără link**: Produse noi, în evaluare, sau doar monitoring prețuri

### 3. Adăugare Nume Chinezești

**Metode**:

**A. Manual prin UI** (recomandat pentru produse importante):
```
1. Deschide produs în admin
2. Găsește nume chinezesc pe 1688.com
3. Copy-paste în câmp "Chinese Name"
4. Save
```

**B. Bulk prin SQL**:
```sql
-- Pentru produse cu SKU cunoscut
UPDATE app.products 
SET chinese_name = '电子元件 LED灯珠'
WHERE sku IN ('LED-001', 'LED-002');
```

**C. API Traducere** (viitor):
```python
# Auto-traducere cu Google Translate sau similar
chinese_name = translate_to_chinese(product.name)
product.chinese_name = chinese_name
```

### 4. Workflow Complet

```
┌─────────────────────────────────────────────┐
│ 1. IMPORT PRODUSE FURNIZORI                 │
│    - Excel de pe 1688.com                   │
│    - Nume chinezești automat                │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 2. RUN MATCHING                             │
│    - Text similarity pe chinese_name        │
│    - Image similarity                       │
│    - Hybrid (recomandat)                    │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 3. REVIEW GROUPS                            │
│    - Verifică grupuri auto-matched          │
│    - Confirmă sau reject                    │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 4. LINK LA PRODUSE LOCALE (opțional)        │
│    - Dacă există produs local               │
│    - Set local_product_id                   │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 5. APROVIZIONARE                            │
│    - Compară prețuri în grup                │
│    - Alege furnizor disponibil              │
│    - Comandă                                │
└─────────────────────────────────────────────┘
```

## 🔧 Implementări Tehnice

### Backend Endpoints

**Suppliers**:
- `GET /api/v1/suppliers` - Listare furnizori ✅
- `POST /api/v1/suppliers` - Creare furnizor ✅
- `PUT /api/v1/suppliers/{id}` - Update furnizor ✅
- `DELETE /api/v1/suppliers/{id}` - Ștergere furnizor ✅

**Supplier Products**:
- `GET /api/v1/suppliers/matching/products` - Listare cu paginare ✅
- `POST /api/v1/suppliers/matching/import/excel` - Import Excel ✅
- `DELETE /api/v1/suppliers/matching/products/{id}` - Ștergere ✅
- `POST /api/v1/suppliers/matching/products/delete-batch` - Bulk delete ✅

**Matching**:
- `POST /api/v1/suppliers/matching/match/text` - Text matching ✅
- `POST /api/v1/suppliers/matching/match/image` - Image matching ✅
- `POST /api/v1/suppliers/matching/match/hybrid` - Hybrid (recomandat) ✅
- `GET /api/v1/suppliers/matching/groups` - Listare grupuri ✅
- `POST /api/v1/suppliers/matching/groups/{id}/confirm` - Confirmare ✅
- `POST /api/v1/suppliers/matching/groups/{id}/reject` - Respingere ✅

**Price Comparison**:
- `GET /api/v1/suppliers/matching/groups/{id}/price-comparison` - Comparare prețuri ✅

### Frontend Pages

**Suppliers** (`/suppliers`):
- ✅ Conectat la backend real (nu mai folosește mock data)
- ✅ CRUD complet funcțional
- ✅ Ștergere persistentă

**Supplier Matching** (`/supplier-matching`):
- ✅ Import Excel produse furnizori
- ✅ Algoritmi matching (text/image/hybrid)
- ✅ Review și confirmare grupuri
- ✅ Tab "Manage Products" cu delete

**Products** (viitor):
- 🔄 Adăugare câmp "Chinese Name" în formular
- 🔄 Linking la matching groups
- 🔄 Vizualizare furnizori disponibili per produs

## 📈 Statistici Curente

```
Total Produse Locale: ~200 (eMAG sync)
Total Produse Furnizori: 2,985
Total Grupuri Matching: 836
Total Furnizori: 5
Matching Rate: 56% (1,672/2,985)
```

## 🚀 Următorii Pași

### Prioritate Înaltă
1. ✅ Conectare Suppliers.tsx la backend (DONE)
2. ✅ Adăugare chinese_name la Product model (DONE)
3. ✅ Migrare bază de date (DONE)
4. 🔄 UI pentru adăugare chinese_name în Products page
5. 🔄 Auto-linking produse locale la grupuri matching

### Prioritate Medie
6. 🔄 API traducere automată (Google Translate)
7. 🔄 Bulk import chinese names din CSV
8. 🔄 Dashboard aprovizionare cu recomandări
9. 🔄 Alerting când furnizor principal indisponibil

### Prioritate Scăzută
10. 🔄 ML pentru matching mai precis
11. 🔄 Tracking istoric prețuri cu grafice
12. 🔄 Predicție prețuri viitoare
13. 🔄 Integrare directă cu 1688.com API

## 🎉 Rezumat

**Arhitectura actuală este CORECTĂ și OPTIMĂ**:

✅ **Separare clară**: Produse locale vs. produse furnizori  
✅ **Flexibilitate**: Păstrare toate produse furnizori  
✅ **Backup**: Multiple surse de aprovizionare  
✅ **Istoric**: Tracking complet prețuri  
✅ **Matching**: Link opțional la produse locale  
✅ **Chinese Names**: Suport complet pentru matching  

**NU schimba arhitectura** - este deja bine gândită pentru cazul tău de utilizare!

---

**Data**: 2025-10-01  
**Versiune**: 2.0.0  
**Status**: ✅ IMPLEMENTAT ȘI DOCUMENTAT
