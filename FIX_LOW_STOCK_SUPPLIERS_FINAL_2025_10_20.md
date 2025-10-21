# Fix Final Low Stock Suppliers - 20 Octombrie 2025

## Problema 1: Numele chinezesc nu se actualizează după modificare ✅ REZOLVAT

### Cauza Reală
Când modifici numele chinezesc în pagina "Detalii Produs Furnizor", frontend-ul apela **întotdeauna** endpoint-ul pentru produse 1688:
```
PATCH /suppliers/{supplier_id}/products/{product_id}/chinese-name
```

Dar produsul din imagine este de tip **Google Sheets**, nu 1688! Pentru produsele Google Sheets, trebuie să folosim endpoint-ul:
```
PATCH /suppliers/sheets/{sheet_id}
```

### Soluția Aplicată
Am modificat funcția `handleUpdateSupplierChineseName` din `/admin-frontend/src/pages/suppliers/SupplierProducts.tsx` pentru a verifica tipul produsului (`import_source`) și a apela endpoint-ul corect:

```tsx
// ÎNAINTE (GREȘIT):
await api.patch(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/chinese-name`, {
  chinese_name: editingSupplierChineseName
});

// DUPĂ (CORECTAT):
if (selectedProduct.import_source === 'google_sheets') {
  // Update Google Sheets product
  await api.patch(`/suppliers/sheets/${selectedProduct.id}`, {
    supplier_product_chinese_name: editingSupplierChineseName
  });
} else {
  // Update 1688 product
  await api.patch(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/chinese-name`, {
    chinese_name: editingSupplierChineseName
  });
}
```

**Rezultat:** Acum când modifici numele chinezesc pentru un produs Google Sheets, modificarea se salvează corect în tabelul `ProductSupplierSheet` și apare în pagina "Low Stock Products" după refresh.

---

## Problema 2: Produsul TZT-T apare ca verificat când nu este ✅ PARȚIAL REZOLVAT

### Investigație

Am identificat **2 probleme separate**:

#### A. Produsele 1688 apăreau ca verificate (REZOLVAT în sesiunea anterioară)
**Cauza:** Endpoint-ul `/inventory/low-stock-with-suppliers` seta `is_verified = sp.manual_confirmed` pentru produsele 1688.

**Fix aplicat anterior:**
```python
# Linia 545 în /app/api/v1/endpoints/inventory/low_stock_suppliers.py
"is_verified": False,  # 1688 suppliers don't have is_verified field
```

#### B. Produsele Google Sheets pot fi marcate ca verificate din greșeală
**Cauza:** Există un endpoint `/suppliers/sync-verification-status` care sincronizează statusul de verificare de la produsele 1688 (`manual_confirmed`) la produsele Google Sheets (`is_verified`).

**Locație:** `/app/api/v1/endpoints/suppliers/supplier_sheet_sync.py` - Linia 187

```python
# Sync verification status
supplier_sheet.is_verified = True  # ⚠️ PROBLEMĂ!
supplier_sheet.verified_by = str(current_user.id)
supplier_sheet.verified_at = sp.confirmed_at
```

**Problema:** Acest endpoint confundă `manual_confirmed` (matching confirmat) cu `is_verified` (furnizor verificat)!

### Verificare în Baza de Date

Pentru a verifica dacă produsul din imagine este marcat ca verificat în baza de date, rulează:

```sql
-- Verifică statusul is_verified pentru produsul TZT-T
SELECT 
    id,
    sku,
    supplier_name,
    supplier_product_chinese_name,
    is_verified,
    is_preferred,
    verified_by,
    verified_at
FROM app.product_supplier_sheets
WHERE supplier_name LIKE '%TZT%'
  AND supplier_product_chinese_name LIKE '%18650锂电池检测仪%'
  AND is_active = true;
```

### Soluție Recomandată

**Opțiune 1: Resetare manuală în baza de date**
```sql
-- Resetează is_verified pentru produsele care nu ar trebui să fie verificate
UPDATE app.product_supplier_sheets
SET 
    is_verified = false,
    verified_by = NULL,
    verified_at = NULL
WHERE supplier_name LIKE '%TZT%'
  AND supplier_product_chinese_name LIKE '%18650锂电池检测仪%';
```

**Opțiune 2: Adăugare buton "Mark as Verified" în frontend**
Permite utilizatorului să marcheze manual produsele ca verificate, în loc să se facă automat.

**Opțiune 3: Eliminare endpoint sincronizare automată**
Endpoint-ul `/suppliers/sync-verification-status` creează confuzie între matching și verificare. Ar trebui eliminat sau modificat.

---

## Diferența între Matching și Verificare

### Manual Confirmed (Matching)
- **Tabel:** `SupplierProduct` (1688)
- **Câmp:** `manual_confirmed`
- **Semnificație:** Produsul furnizor a fost **asociat manual** cu un produs local
- **Scop:** Confirmă că matching-ul automat este corect
- **Exemplu:** "Da, acest produs 1688 corespunde cu produsul nostru local"

### Is Verified (Verificare Furnizor)
- **Tabel:** `ProductSupplierSheet` (Google Sheets) și `ProductMapping`
- **Câmp:** `is_verified`
- **Semnificație:** Furnizorul a fost **verificat** ca fiind de încredere
- **Scop:** Confirmă calitatea și fiabilitatea furnizorului
- **Exemplu:** "Da, acest furnizor este de încredere și produsele sunt de calitate"

**Concluzie:** Acestea sunt **2 concepte diferite** și nu ar trebui confundate!

---

## Testare

### Test 1: Modificare nume chinezesc pentru produs Google Sheets ✅

1. Navighează la "Produse Furnizori"
2. Selectează furnizorul TZT-T
3. Găsește produsul "18650锂电池检测仪蓄电池容量测量maH/mwH高精度显示测量模块自动"
4. Deschide "Detalii Produs Furnizor"
5. Modifică numele chinezesc (adaugă un caracter sau șterge unul)
6. Salvează modificarea
7. Navighează la "Low Stock Products - Supplier Selection"
8. Apasă butonul **"Refresh"**
9. Verifică că numele chinezesc s-a actualizat ✅

### Test 2: Verificare status is_verified

1. Navighează la "Low Stock Products - Supplier Selection"
2. Găsește produsul "18650锂电池检测仪蓄电池容量测量maH/mwH高精度显示测量模块自动"
3. Verifică tag-ul furnizorului TZT-T:
   - Dacă este **"Verified"** (verde) → Produsul este marcat ca verificat în baza de date
   - Dacă este **"Pending Verification"** (portocaliu) → Produsul NU este verificat ✅

---

## Fișiere Modificate

### Frontend
1. `/admin-frontend/src/pages/suppliers/SupplierProducts.tsx`
   - Funcția `handleUpdateSupplierChineseName` (linii 463-493)
   - Adăugat verificare pentru `import_source === 'google_sheets'`
   - Apelează endpoint-ul corect în funcție de tipul produsului

### Backend
1. `/app/api/v1/endpoints/inventory/low_stock_suppliers.py`
   - Linia 545: Schimbat `is_verified` de la `sp.manual_confirmed` la `False` pentru produsele 1688

---

## Recomandări Finale

### Prioritate Înaltă

1. **Verificare manuală în baza de date**
   - Rulează query-ul SQL pentru a verifica statusul `is_verified`
   - Resetează câmpul dacă este setat greșit

2. **Adăugare buton "Mark as Verified" în pagina "Produse Furnizori"**
   - Permite utilizatorului să marcheze manual produsele ca verificate
   - Adaugă confirmare înainte de marcare

3. **Eliminare sau modificare endpoint `/suppliers/sync-verification-status`**
   - Acest endpoint creează confuzie între matching și verificare
   - Ar trebui eliminat sau modificat pentru a nu seta automat `is_verified = True`

### Prioritate Medie

1. **Adăugare câmp `is_verified` în modelul `SupplierProduct`**
   - Permite verificarea manuală a furnizorilor 1688
   - Separare clară între "matchat" și "verificat"

2. **Documentare diferență între matching și verificare**
   - Adaugă tooltip-uri în frontend
   - Explicații clare în documentație

---

## Concluzie

### Problema 1: Nume chinezesc nu se actualizează
- **Status:** ✅ **REZOLVAT**
- **Cauză:** Frontend apela endpoint-ul greșit pentru produsele Google Sheets
- **Fix:** Verificare `import_source` și apelare endpoint corect

### Problema 2: Produsul TZT-T apare ca verificat
- **Status:** ⚠️ **PARȚIAL REZOLVAT**
- **Cauză:** 
  - Produsele 1688 foloseau `manual_confirmed` în loc de `is_verified` ✅ REZOLVAT
  - Produsele Google Sheets pot fi marcate ca verificate din greșeală prin endpoint `/suppliers/sync-verification-status` ⚠️ NECESITĂ VERIFICARE MANUALĂ
- **Acțiune necesară:** Verifică în baza de date dacă `is_verified = true` pentru produsul TZT-T și resetează dacă este necesar

---

**Data:** 20 Octombrie 2025  
**Verificat de:** Cascade AI Assistant  
**Status:** ✅ Problema 1 rezolvată complet, Problema 2 necesită verificare manuală în baza de date
