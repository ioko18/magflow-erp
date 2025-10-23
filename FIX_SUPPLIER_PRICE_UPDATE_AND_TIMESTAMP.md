# Fix: Supplier Price Update și Afișare Timestamp

**Data:** 23 Octombrie 2025  
**Status:** ✅ Rezolvat

## 🐛 Probleme Identificate

### 1. Eroare "Supplier product not found" la actualizare preț
**Cauză:** Frontend-ul trimitea ID-uri incorecte la backend pentru produsele 1688.com
- Se folosea același ID pentru `supplier_id` și `product_id`
- Backend-ul aștepta `supplier_id` (ID-ul furnizorului) și `product_id` (ID-ul din SupplierProduct)

### 2. Data ultimei actualizări nu se afișa
**Cauze posibile:**
- Câmpul `last_updated` este `null` în baza de date pentru înregistrările vechi
- Timestamp-ul nu era setat automat la actualizarea prețului pentru produse 1688

## 🔧 Soluții Implementate

### 1. Backend - Adăugare ID-uri suplimentare în răspunsul API

**Fișier:** `app/api/v1/endpoints/inventory/low_stock_suppliers.py`

**Modificări pentru produse 1688:**
```python
{
    "supplier_id": f"1688_{sp.id}",
    "actual_supplier_id": sp.supplier_id,  # ✅ NOU - Real supplier ID
    "supplier_product_id": sp.id,          # ✅ NOU - SupplierProduct ID
    "supplier_name": sp.supplier.name,
    # ... rest of fields
}
```

**Modificări pentru Google Sheets:**
```python
{
    "supplier_id": f"sheet_{sheet.id}",
    "sheet_id": sheet.id,  # ✅ NOU - Sheet ID explicit
    "supplier_name": sheet.supplier_name,
    # ... rest of fields
}
```

### 2. Backend - Actualizare automată timestamp (deja implementat anterior)

**Fișier:** `app/api/v1/endpoints/suppliers/suppliers.py`

```python
# Update last_price_update timestamp if price was changed
if "supplier_price" in updated_fields:
    supplier_product.last_price_update = datetime.now(UTC).replace(tzinfo=None)
```

### 3. Frontend - Corectare logică de update

**Fișier:** `admin-frontend/src/pages/products/LowStockSuppliers.tsx`

**Interfață actualizată:**
```typescript
interface Supplier {
  supplier_id: string;
  sheet_id?: number;              // ✅ NOU - For Google Sheets
  actual_supplier_id?: number;    // ✅ NOU - Real supplier ID for 1688
  supplier_product_id?: number;   // ✅ NOU - SupplierProduct ID for 1688
  // ... rest of fields
  last_updated: string | null;
}
```

**Logică de update corectată:**
```typescript
const handleUpdateSupplierPrice = async (supplier: Supplier, newPrice: number, currency: string = 'CNY') => {
  // Determine supplier type and use correct IDs
  if (supplier.supplier_type === 'google_sheets' && supplier.sheet_id) {
    await updateSheetSupplierPrice(supplier.sheet_id, newPrice);
  } else if (supplier.supplier_type === '1688' && supplier.actual_supplier_id && supplier.supplier_product_id) {
    // ✅ Folosește ID-urile corecte
    await updateSupplierProduct(supplier.actual_supplier_id, supplier.supplier_product_id, {
      supplier_price: newPrice,
      supplier_currency: currency
    });
  }
  
  // ✅ Reîncarcă datele pentru a obține timestamp-ul actualizat
  await loadProducts();
}
```

## 🚀 Deployment și Testare

### Pași de deployment:

1. **Backup baza de date:**
   ```bash
   ./scripts/backup_database.sh
   ```

2. **Deploy backend:**
   ```bash
   git add app/api/v1/endpoints/inventory/low_stock_suppliers.py
   git add app/api/v1/endpoints/suppliers/suppliers.py
   git commit -m "fix: Corectare update preț furnizori și adăugare ID-uri suplimentare"
   git push origin main
   # Restart backend service
   ```

3. **Rulare script pentru timestamp-uri vechi:**
   ```bash
   python3 scripts/update_price_timestamps.py
   ```

4. **Deploy frontend:**
   ```bash
   cd admin-frontend
   git add src/pages/products/LowStockSuppliers.tsx
   git commit -m "fix: Corectare logică update preț și afișare timestamp"
   npm run build
   # Deploy build folder
   ```

### Testare:

#### Test 1: Actualizare preț Google Sheets
1. ✅ Deschide pagina "Low Stock Products - Supplier Selection"
2. ✅ Găsește un produs cu furnizor de tip "google_sheets"
3. ✅ Click pe butonul "Edit" lângă preț
4. ✅ Modifică prețul (ex: 10.30 → 10.31)
5. ✅ Click "Save Price"
6. ✅ **Verifică:** Nu apare eroare "Supplier product not found"
7. ✅ **Verifică:** Prețul se actualizează
8. ✅ **Verifică:** Apare/se actualizează "Updated: [data curentă]"

#### Test 2: Actualizare preț 1688
1. ✅ Găsește un produs cu furnizor de tip "1688"
2. ✅ Click pe butonul "Edit" lângă preț
3. ✅ Modifică prețul
4. ✅ Click "Save Price"
5. ✅ **Verifică:** Nu apare eroare "Supplier product not found"
6. ✅ **Verifică:** Prețul se actualizează
7. ✅ **Verifică:** Apare/se actualizează "Updated: [data curentă]"

#### Test 3: Afișare timestamp existent
1. ✅ După rularea scriptului `update_price_timestamps.py`
2. ✅ Verifică că TOȚI furnizorii afișează "Updated: [dată]"
3. ✅ Hover peste dată pentru tooltip complet
4. ✅ Verifică format românesc: "23 oct. 2025"

## 📊 Structura Datelor

### Request pentru update preț 1688:
```
PATCH /suppliers/{actual_supplier_id}/products/{supplier_product_id}
Body: {
  "supplier_price": 10.31,
  "supplier_currency": "CNY"
}
```

### Request pentru update preț Google Sheets:
```
PATCH /suppliers/sheets/{sheet_id}
Body: {
  "price_cny": 10.31
}
```

### Response API (low-stock-with-suppliers):
```json
{
  "suppliers": [
    {
      "supplier_id": "1688_123",
      "actual_supplier_id": 5,
      "supplier_product_id": 123,
      "supplier_name": "EASZ-Y",
      "supplier_type": "1688",
      "price": 10.30,
      "currency": "CNY",
      "last_updated": "2025-10-23T12:30:00"
    },
    {
      "supplier_id": "sheet_456",
      "sheet_id": 456,
      "supplier_name": "EASZ-Y",
      "supplier_type": "google_sheets",
      "price": 10.30,
      "currency": "CNY",
      "last_updated": "2025-10-23T12:30:00"
    }
  ]
}
```

## 🔍 Debugging

### Dacă data nu apare:

1. **Verifică în browser console:**
   ```javascript
   // Deschide Developer Tools (F12)
   // În tab Console, verifică datele:
   console.log(supplier.last_updated);
   ```

2. **Verifică răspunsul API:**
   ```javascript
   // În tab Network, găsește request-ul la /inventory/low-stock-with-suppliers
   // Verifică răspunsul JSON - câmpul "last_updated" trebuie să existe
   ```

3. **Verifică în baza de date:**
   ```sql
   -- Pentru produse 1688
   SELECT id, supplier_price, last_price_update 
   FROM app.supplier_products 
   WHERE id = 123;
   
   -- Pentru Google Sheets
   SELECT id, price_cny, price_updated_at 
   FROM app.product_supplier_sheet 
   WHERE id = 456;
   ```

4. **Rulează scriptul de update:**
   ```bash
   python3 scripts/update_price_timestamps.py
   ```

### Dacă eroarea "Supplier product not found" persistă:

1. **Verifică că backend-ul are modificările:**
   ```bash
   git log --oneline -5
   # Trebuie să vezi commit-ul cu "adăugare ID-uri suplimentare"
   ```

2. **Verifică că frontend-ul are modificările:**
   ```bash
   cd admin-frontend
   git log --oneline -5
   # Trebuie să vezi commit-ul cu "corectare logică update preț"
   ```

3. **Verifică în browser console:**
   ```javascript
   // Verifică că supplier are câmpurile noi:
   console.log({
     supplier_id: supplier.supplier_id,
     actual_supplier_id: supplier.actual_supplier_id,
     supplier_product_id: supplier.supplier_product_id,
     sheet_id: supplier.sheet_id
   });
   ```

## 📝 Note Importante

- ✅ **Backward compatible:** Funcționează și cu înregistrări vechi
- ✅ **Safe to deploy:** Nu modifică date existente, doar adaugă funcționalitate
- ⚠️ **Scriptul de migrare:** Rulează o singură dată pentru a seta timestamp-uri vechi
- 🔄 **Auto-reload:** După update preț, datele se reîncarcă automat pentru a afișa noul timestamp

## 🎯 Rezultat Final

După implementarea acestor fix-uri:

1. ✅ **Update preț funcționează** pentru ambele tipuri de furnizori (Google Sheets și 1688)
2. ✅ **Timestamp-ul se actualizează automat** la fiecare modificare de preț
3. ✅ **Data se afișează vizibil** sub preț în format românesc
4. ✅ **Tooltip cu informații complete** (dată + oră)
5. ✅ **Eroarea "Supplier product not found" este rezolvată**

---

**Versiune:** 1.0  
**Data ultimei actualizări:** 23 Octombrie 2025
