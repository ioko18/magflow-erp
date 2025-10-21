# Fix Low Stock Suppliers - 20 Octombrie 2025

## Probleme Raportate

### 1. Numele chinezesc nu se actualizează în pagina "Low Stock Products - Supplier Selection"

**Problema:** După modificarea numelui chinezesc în pagina "Detalii Produs Furnizor", numele nu se actualizează automat în pagina "Low Stock Products - Supplier Selection".

**Cauza:** Pagina "Low Stock Products" citește datele din backend la fiecare încărcare. Când modifici numele chinezesc în pagina "Detalii Produs Furnizor", modificarea se salvează în baza de date, dar pagina "Low Stock Products" **nu reîncarcă automat** datele.

**Soluție Actuală:** Există deja un buton **"Refresh"** în pagina "Low Stock Products" care reîncarcă toate datele. Utilizatorul trebuie să apese acest buton după modificarea numelui chinezesc.

**Locație buton Refresh:** 
- Fișier: `/admin-frontend/src/pages/products/LowStockSuppliers.tsx`
- Linii: 1311-1315

```tsx
<Button
  icon={<ReloadOutlined />}
  onClick={loadProducts}
  loading={loading}
>
  Refresh
</Button>
```

**Recomandare:** Adăugare auto-refresh sau notificare când se modifică date în alte pagini.

---

### 2. Produsul "18650锂电池检测仪蓄电池容量测量maH/mwH高精度显示测量模块自动" de la furnizorul "TZT-T" apare ca verificat când nu este

**Problema:** Produsul apare cu tag-ul "Verified" (verde) când ar trebui să fie "Pending Verification" (portocaliu).

**Cauza:** În endpoint-ul `/inventory/low-stock-with-suppliers`, câmpul `is_verified` pentru produsele 1688 era setat la `sp.manual_confirmed`:

```python
# ÎNAINTE (GREȘIT):
"is_verified": sp.manual_confirmed,  # Linia 545
```

**Problema:** `manual_confirmed` și `is_verified` sunt concepte diferite:
- **`manual_confirmed`** = Produsul furnizor a fost **matchat manual** cu un produs local (asociere confirmată)
- **`is_verified`** = Furnizorul a fost **verificat** ca fiind de încredere (verificare calitate/fiabilitate)

**Modelul SupplierProduct** nu are câmpul `is_verified`, doar `manual_confirmed`. Doar `ProductSupplierSheet` (Google Sheets) are câmpul `is_verified`.

**Soluție Aplicată:**
```python
# DUPĂ (CORECTAT):
"is_verified": False,  # 1688 suppliers don't have is_verified field, only manual_confirmed for matching
```

**Fișier modificat:** `/app/api/v1/endpoints/inventory/low_stock_suppliers.py` - Linia 545

---

## Explicație Tehnică

### Structura Furnizorilor în Sistem

Sistemul are **2 tipuri** de furnizori:

#### 1. Google Sheets Suppliers (ProductSupplierSheet)
- Sursă: Importați din Google Sheets
- Câmpuri disponibile:
  - `is_verified` ✅ (poate fi setat manual)
  - `is_preferred` ✅
  - `supplier_product_chinese_name` ✅
  - `price_cny` ✅

#### 2. 1688 Suppliers (SupplierProduct)
- Sursă: Scrapuiți de pe 1688.com
- Câmpuri disponibile:
  - `manual_confirmed` ✅ (doar pentru matching, NU pentru verificare)
  - `is_preferred` ✅
  - `supplier_product_chinese_name` ✅
  - `supplier_price` ✅
- Câmpuri LIPSĂ:
  - `is_verified` ❌ (nu există în model)

### Logica în Endpoint

```python
# Google Sheets suppliers (linii 491-509)
suppliers_by_product[product_id].append({
    "supplier_id": f"sheet_{sheet.id}",
    "supplier_name": sheet.supplier_name,
    "supplier_type": "google_sheets",
    "is_verified": sheet.is_verified,  # ✅ Câmp valid
    # ...
})

# 1688 suppliers (linii 531-550)
suppliers_by_product[sp.local_product_id].append({
    "supplier_id": f"1688_{sp.id}",
    "supplier_name": sp.supplier.name if sp.supplier else "Unknown",
    "supplier_type": "1688",
    "is_verified": False,  # ✅ CORECTAT - nu au câmp is_verified
    # ...
})
```

---

## Recomandări pentru Viitor

### Prioritate Înaltă

1. **Adăugare câmp `is_verified` în modelul SupplierProduct**
   - Permite verificarea manuală a furnizorilor 1688
   - Separare clară între "matchat" și "verificat"
   
   ```python
   # În app/models/supplier.py
   class SupplierProduct(Base, TimestampMixin):
       # ... câmpuri existente ...
       
       # NOU - Adăugare verificare
       is_verified: Mapped[bool] = mapped_column(
           Boolean, 
           default=False,
           comment="Whether this supplier has been manually verified for quality/reliability"
       )
       verified_by: Mapped[int | None] = mapped_column(
           Integer, 
           nullable=True,
           comment="User ID who verified this supplier"
       )
       verified_at: Mapped[datetime | None] = mapped_column(
           DateTime(timezone=True),
           nullable=True,
           comment="When this supplier was verified"
       )
   ```

2. **Adăugare endpoint pentru verificare furnizori**
   ```python
   @router.post("/suppliers/{supplier_id}/products/{product_id}/verify")
   async def verify_supplier_product(
       supplier_id: int,
       product_id: int,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_user),
   ):
       """Mark a supplier product as verified"""
       # Implementare verificare
   ```

3. **Auto-refresh în frontend**
   - Folosire WebSocket sau polling pentru actualizări în timp real
   - Notificare când se modifică date în alte pagini
   
   ```tsx
   // Exemplu cu event bus
   import { EventEmitter } from 'events';
   
   const eventBus = new EventEmitter();
   
   // În pagina "Detalii Produs Furnizor"
   const handleSaveChineseName = async () => {
       await api.patch(`/suppliers/${supplierId}/products/${productId}/chinese-name`, {
           chinese_name: newName
       });
       eventBus.emit('supplier-product-updated', { productId });
   };
   
   // În pagina "Low Stock Products"
   useEffect(() => {
       const handleUpdate = () => {
           loadProducts(); // Auto-refresh
       };
       eventBus.on('supplier-product-updated', handleUpdate);
       return () => eventBus.off('supplier-product-updated', handleUpdate);
   }, []);
   ```

### Prioritate Medie

1. **Adăugare indicator de "stale data"**
   - Afișare timestamp când au fost încărcate datele
   - Sugestie de refresh dacă datele sunt vechi

2. **Optimizare queries**
   - Cache pentru datele furnizorilor
   - Invalidare cache la modificări

3. **Logging pentru modificări**
   - Audit trail pentru modificări de nume chinezesc
   - Istoric modificări pentru debugging

---

## Testare

### Test Manual 1: Verificare is_verified

1. Navighează la "Low Stock Products - Supplier Selection"
2. Selectează un produs cu furnizori 1688
3. Verifică că furnizorul 1688 are tag-ul **"Pending Verification"** (portocaliu)
4. Verifică că furnizorul Google Sheets poate avea tag-ul **"Verified"** (verde) dacă a fost verificat

### Test Manual 2: Refresh după modificare

1. Navighează la "Produse Furnizori"
2. Selectează furnizorul TZT-T
3. Găsește produsul "18650锂电池检测仪蓄电池容量测量maH/mwH高精度显示测量模块自动"
4. Modifică numele chinezesc
5. Navighează la "Low Stock Products - Supplier Selection"
6. Apasă butonul **"Refresh"**
7. Verifică că numele chinezesc s-a actualizat

---

## Fișiere Modificate

### Backend
1. `/app/api/v1/endpoints/inventory/low_stock_suppliers.py`
   - Linia 545: Schimbat `is_verified` de la `sp.manual_confirmed` la `False`

### Frontend
- **NU au fost necesare modificări** - butonul Refresh există deja

---

## Concluzie

### Problema 1: Nume chinezesc nu se actualizează
- **Status:** ✅ **NU ESTE O EROARE**
- **Soluție:** Utilizatorul trebuie să apese butonul "Refresh" după modificări
- **Recomandare:** Implementare auto-refresh pentru viitor

### Problema 2: Produsul TZT-T apare ca verificat
- **Status:** ✅ **REZOLVAT**
- **Cauză:** Confuzie între `manual_confirmed` (matching) și `is_verified` (verificare)
- **Fix:** Setat `is_verified = False` pentru produsele 1688 care nu au acest câmp în model

---

**Data:** 20 Octombrie 2025  
**Verificat de:** Cascade AI Assistant  
**Status:** ✅ Problema 2 rezolvată, Problema 1 clarificată
