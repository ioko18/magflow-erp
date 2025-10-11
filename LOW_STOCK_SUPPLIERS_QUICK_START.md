# 🚀 Quick Start: Low Stock Suppliers Feature

## Ce am creat pentru tine

Am implementat o pagină completă în MagFlow ERP care îți permite să:

✅ **Vizualizezi produsele cu stoc scăzut**  
✅ **Vezi toți furnizorii disponibili pentru fiecare produs cu prețurile lor**  
✅ **Selectezi manual furnizorul preferat prin click pe checkbox**  
✅ **Exportezi produsele grupate pe furnizori în Excel**

## 📁 Fișiere create/modificate

### Backend (Python/FastAPI)
1. **`app/api/v1/endpoints/inventory/low_stock_suppliers.py`** - Endpoint-uri API noi
   - `GET /inventory/low-stock-with-suppliers` - Listează produse cu furnizori
   - `POST /inventory/export/low-stock-by-supplier` - Export Excel per furnizor

2. **`app/api/v1/endpoints/inventory/__init__.py`** - Înregistrare router
3. **`app/api/v1/endpoints/__init__.py`** - Import router
4. **`app/api/v1/api.py`** - Adăugare în API principal

### Frontend (React/TypeScript)
1. **`admin-frontend/src/pages/products/LowStockSuppliers.tsx`** - Pagină nouă React
2. **`admin-frontend/src/pages/products/index.ts`** - Export componentă
3. **`admin-frontend/src/App.tsx`** - Adăugare rută

### Documentație
1. **`docs/LOW_STOCK_SUPPLIERS_FEATURE.md`** - Documentație completă

## 🎯 Cum să folosești feature-ul

### Pasul 1: Pornește aplicația

**Backend:**
```bash
cd /Users/macos/anaconda3/envs/MagFlow
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd admin-frontend
npm install  # Doar prima dată
npm run dev
```

### Pasul 2: Accesează pagina

Deschide browser-ul la: **http://localhost:3000/low-stock-suppliers**

### Pasul 3: Workflow

1. **Vezi statisticile** - Dashboard cu produse out of stock, critical, low stock
2. **Filtrează** - Alege status (out of stock, critical, low stock) sau warehouse
3. **Selectează furnizori:**
   - Click pe "Select Supplier" pentru fiecare produs
   - Vezi toți furnizorii disponibili cu prețuri
   - Bifează checkbox-ul la furnizorul dorit
4. **Exportă:**
   - Click "Export Selected (X)" unde X = numărul de produse selectate
   - Se descarcă Excel cu foi separate pentru fiecare furnizor

## 📊 Structura Excel exportat

Fișierul Excel va avea **foi separate pentru fiecare furnizor**:

```
📄 low_stock_by_supplier_20251010.xlsx
  📑 Sheet "Furnizor A"
    - Produs 1: SKU, Nume, Stoc curent, Cantitate comandă, Preț, Total
    - Produs 2: ...
    - TOTAL: 1,245.60 CNY
  
  📑 Sheet "Furnizor B"
    - Produs 3: ...
    - Produs 4: ...
    - TOTAL: 892.30 CNY
```

## 🔍 Surse de date pentru furnizori

Sistemul ia furnizori din **2 surse**:

### 1. Google Sheets (`ProductSupplierSheet`)
- Tabelul `product_supplier_sheets` din baza de date
- Importat din Google Sheets tab "Product_Suppliers"
- Prețuri în CNY
- Identificare: `supplier_id` începe cu `"sheet_"`

### 2. 1688.com (`SupplierProduct`)
- Tabelul `supplier_products` din baza de date
- Date scraped de pe 1688.com
- Linkuri către produse
- Identificare: `supplier_id` începe cu `"1688_"`

## 📝 Exemplu de utilizare

### Scenariul tău din screenshot

Ai un Excel cu produse și furnizori (vezi screenshot-ul tău). Acum poți:

1. **Importa furnizorii** în sistem (dacă nu sunt deja):
   ```sql
   -- Exemplu: Adaugă furnizor pentru un produs
   INSERT INTO app.product_supplier_sheets (
     sku, supplier_name, price_cny, is_active, is_preferred
   ) VALUES (
     'PROD-001', 'Furnizor Aliexpress', 22.80, true, true
   );
   ```

2. **Accesează pagina** `/low-stock-suppliers`

3. **Vezi produsele** cu stoc scăzut automat

4. **Selectează furnizori** - Click pe checkbox la furnizorul preferat

5. **Exportă** - Primești Excel gata pentru comandă

## 🎨 Caracteristici UI

### Culori status stoc
- 🔴 **Roșu** - Out of stock (urgent!)
- 🟠 **Portocaliu** - Critical (foarte scăzut)
- 🟡 **Galben** - Low stock (atenție)
- 🟢 **Verde** - In stock

### Badge-uri furnizori
- 🔵 **Preferred** - Furnizor preferat
- 🟢 **Verified** - Furnizor verificat manual
- 🟣 **Google Sheets** - Din Google Sheets
- 🟣 **1688** - De pe 1688.com

### Funcții interactive
- ✅ Checkbox pentru selecție furnizor
- 🖼️ Preview imagini produse
- 🔗 Link-uri către produse furnizor
- 📊 Calcul automat cost total

## 🔧 Configurare necesară

### 1. Verifică că ai openpyxl instalat (pentru Excel export)
```bash
pip install openpyxl
```

### 2. Asigură-te că ai date în tabele
```sql
-- Verifică produse cu stoc scăzut
SELECT p.sku, p.name, i.quantity, i.minimum_stock, i.reorder_point
FROM app.inventory_items i
JOIN app.products p ON i.product_id = p.id
WHERE i.quantity <= i.reorder_point;

-- Verifică furnizori disponibili
SELECT sku, supplier_name, price_cny
FROM app.product_supplier_sheets
WHERE is_active = true;
```

## 🐛 Troubleshooting

### Problema: Nu văd furnizori pentru produse
**Soluție:** Adaugă furnizori în `product_supplier_sheets` sau `supplier_products`

### Problema: Export Excel nu funcționează
**Soluție:** Instalează openpyxl: `pip install openpyxl`

### Problema: Produsele nu apar în listă
**Soluție:** Setează `minimum_stock` și `reorder_point` în `inventory_items`

## 📞 API Endpoints

### GET `/api/v1/inventory/low-stock-with-suppliers`
Returnează produse cu stoc scăzut și toți furnizorii

**Query params:**
- `status`: 'out_of_stock' | 'critical' | 'low_stock' | 'all'
- `warehouse_id`: Filter by warehouse
- `skip`: Pagination offset
- `limit`: Page size (max 1000)

### POST `/api/v1/inventory/export/low-stock-by-supplier`
Exportă produse selectate în Excel

**Body:**
```json
[
  {
    "product_id": 123,
    "sku": "PROD-001",
    "supplier_id": "sheet_45",
    "reorder_quantity": 50
  }
]
```

## 🎓 Next Steps

1. **Testează feature-ul** cu datele tale existente
2. **Importă furnizori** din Google Sheets dacă nu sunt în sistem
3. **Configurează minimum_stock** pentru produse
4. **Folosește exportul** pentru a comanda de la furnizori

## 📚 Documentație completă

Vezi `docs/LOW_STOCK_SUPPLIERS_FEATURE.md` pentru detalii tehnice complete.

---

**Creat:** 2025-10-10  
**Versiune:** 1.0.0  

Succes cu comenzile! 🚀
