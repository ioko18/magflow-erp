# 🚀 Implementare Endpoint "Promote" pentru Google Sheets Products - 21 Octombrie 2025

## 📋 Cerință

Implementare endpoint pentru transformarea produselor Google Sheets (`ProductSupplierSheet`) în produse interne (`SupplierProduct`) pentru management mai bun.

## ✅ Implementare Backend

### 1. Endpoint Nou: `POST /suppliers/sheets/{sheet_id}/promote`

**Fișier:** `app/api/v1/endpoints/suppliers/promote_sheet_product.py`

#### Funcționalitate

```python
@router.post("/sheets/{sheet_id}/promote")
async def promote_sheet_to_supplier_product(
    sheet_id: int,
    mark_sheet_inactive: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Promote a Google Sheets product to an internal supplier product.

    Steps:
    1. Clone ProductSupplierSheet → SupplierProduct
    2. Copy all fields (Chinese name, specs, price, URL)
    3. Link to supplier_id and local_product_id
    4. Mark sheet entry as inactive (optional)
    """
```

#### Validări Implementate

1. ✅ **Verifică existența produsului Google Sheets**
   ```python
   if not sheet:
       raise HTTPException(status_code=404, detail="Google Sheets product not found")
   ```

2. ✅ **Verifică supplier_id**
   ```python
   if not sheet.supplier_id:
       raise HTTPException(
           status_code=400,
           detail="Cannot promote: product has no supplier_id"
       )
   ```

3. ✅ **Verifică existența furnizorului**
   ```python
   if not supplier:
       raise HTTPException(status_code=404, detail=f"Supplier with ID {sheet.supplier_id} not found")
   ```

4. ✅ **Verifică existența produsului local**
   ```python
   if not local_product:
       raise HTTPException(
           status_code=404,
           detail=f"Local product with SKU {sheet.sku} not found"
       )
   ```

5. ✅ **Previne duplicate**
   ```python
   if existing:
       raise HTTPException(
           status_code=400,
           detail=f"Supplier product already exists (ID: {existing.id})"
       )
   ```

#### Câmpuri Copiate

```python
new_supplier_product = SupplierProduct(
    supplier_id=sheet.supplier_id,                          # ✅ FK către supplier
    local_product_id=local_product.id,                      # ✅ FK către product
    supplier_product_name=sheet.supplier_product_chinese_name or sheet.sku,
    supplier_product_chinese_name=sheet.supplier_product_chinese_name,  # ✅ Nume chinezesc
    supplier_product_specification=sheet.supplier_product_specification,  # ✅ Specificații
    supplier_product_url=sheet.supplier_url,                # ✅ URL
    supplier_price=sheet.price_cny,                         # ✅ Preț
    supplier_currency="CNY",
    exchange_rate=sheet.exchange_rate_cny_ron or 0.65,
    calculated_price_ron=sheet.calculated_price_ron,
    last_price_update=sheet.price_updated_at or datetime.now(UTC).replace(tzinfo=None),
    is_active=True,
    manual_confirmed=True,                                  # ✅ Marcat ca confirmat
    confidence_score=1.0,                                   # ✅ Confidence ridicată
)
```

#### Marcare Sheet ca Inactiv

```python
if mark_sheet_inactive:
    sheet.is_active = False
    sheet.updated_at = datetime.now(UTC).replace(tzinfo=None)
```

### 2. Integrare în Router

**Fișier:** `app/api/v1/routers/suppliers_router.py`

```python
from app.api.v1.endpoints.suppliers import (
    promote_sheet_router,  # ✅ NOU
    supplier_matching_router,
    supplier_migration_router,
    suppliers_router,
)

# Promote Google Sheets products to internal supplier products
router.include_router(promote_sheet_router, tags=["supplier-sheets"])
```

---

## 📊 Răspuns API

### Success Response

```json
{
  "status": "success",
  "data": {
    "message": "Google Sheets product promoted successfully",
    "sheet_id": 5357,
    "new_supplier_product_id": 12345,
    "sheet_marked_inactive": true,
    "supplier_name": "TZT",
    "product_sku": "EMG322"
  }
}
```

### Error Responses

#### 404 - Sheet Not Found
```json
{
  "detail": "Google Sheets product not found"
}
```

#### 400 - No supplier_id
```json
{
  "detail": "Cannot promote: product has no supplier_id. Please set supplier_id first."
}
```

#### 404 - Supplier Not Found
```json
{
  "detail": "Supplier with ID 1 not found"
}
```

#### 404 - Local Product Not Found
```json
{
  "detail": "Local product with SKU EMG322 not found. Please create it first."
}
```

#### 400 - Duplicate
```json
{
  "detail": "Supplier product already exists (ID: 12345). Cannot promote duplicate."
}
```

---

## 🧪 Testare

### 1. Test Manual cu cURL

```bash
# Promote product cu ID 5357
curl -X POST "http://localhost:8000/api/v1/suppliers/sheets/5357/promote" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"

# Promote fără a marca sheet-ul ca inactiv
curl -X POST "http://localhost:8000/api/v1/suppliers/sheets/5357/promote?mark_sheet_inactive=false" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### 2. Test în Python

```python
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.product_supplier_sheet import ProductSupplierSheet
from app.models.supplier_product import SupplierProduct

async def test_promote():
    async with AsyncSessionLocal() as session:
        # Find a Google Sheets product
        result = await session.execute(
            select(ProductSupplierSheet)
            .where(ProductSupplierSheet.is_active == True)
            .where(ProductSupplierSheet.supplier_id.isnot(None))
            .limit(1)
        )
        sheet = result.scalar_one_or_none()
        
        if sheet:
            print(f"Found sheet: ID={sheet.id}, SKU={sheet.sku}")
            print(f"Supplier ID: {sheet.supplier_id}")
            print(f"Chinese Name: {sheet.supplier_product_chinese_name}")
            
            # After calling promote endpoint, verify
            result2 = await session.execute(
                select(SupplierProduct)
                .where(SupplierProduct.supplier_id == sheet.supplier_id)
                .where(SupplierProduct.local_product_id.isnot(None))
            )
            supplier_products = result2.scalars().all()
            print(f"\nSupplier products: {len(supplier_products)}")

asyncio.run(test_promote())
```

### 3. Verificare în UI

1. **Înainte de promote:**
   - Produsul apare cu badge "Google Sheets"
   - `import_source = 'google_sheets'`

2. **După promote:**
   - Produsul apare cu badge "1688" sau fără badge
   - `import_source = null` sau `'1688'`
   - Sheet-ul original nu mai apare (dacă `mark_sheet_inactive=true`)

---

## 🎯 Cazuri de Utilizare

### 1. **Migrare Produse Frecvent Editate**

Produsele Google Sheets care sunt editate des ar trebui promovate pentru:
- Management mai bun
- Editare mai rapidă
- Integrare cu workflow-ul 1688

```bash
# Identifică produse frecvent editate
SELECT id, sku, supplier_name, updated_at
FROM app.product_supplier_sheets
WHERE is_active = true
AND updated_at > NOW() - INTERVAL '30 days'
ORDER BY updated_at DESC;

# Promote-le unul câte unul
curl -X POST "http://localhost:8000/api/v1/suppliers/sheets/{id}/promote"
```

### 2. **Cleanup Duplicate**

Dacă ai produse duplicate (Google Sheets + SupplierProduct):
```bash
# Găsește duplicate
SELECT pss.id as sheet_id, sp.id as supplier_product_id, pss.sku
FROM app.product_supplier_sheets pss
JOIN app.supplier_products sp ON sp.supplier_id = pss.supplier_id
JOIN app.products p ON p.sku = pss.sku AND p.id = sp.local_product_id
WHERE pss.is_active = true;

# Marchează sheet-urile ca inactive
UPDATE app.product_supplier_sheets
SET is_active = false
WHERE id IN (SELECT sheet_id FROM duplicate_query);
```

### 3. **Migrare în Batch**

Pentru migrare în masă:
```python
import asyncio
import httpx

async def batch_promote():
    async with httpx.AsyncClient() as client:
        # Get all sheets to promote
        sheets_to_promote = [5357, 5358, 5359]  # IDs
        
        for sheet_id in sheets_to_promote:
            try:
                response = await client.post(
                    f"http://localhost:8000/api/v1/suppliers/sheets/{sheet_id}/promote",
                    headers={"Authorization": "Bearer YOUR_TOKEN"}
                )
                print(f"Sheet {sheet_id}: {response.status_code}")
            except Exception as e:
                print(f"Error promoting {sheet_id}: {e}")

asyncio.run(batch_promote())
```

---

## 📋 Fișiere Create/Modificate

### Fișiere Noi
1. **`app/api/v1/endpoints/suppliers/promote_sheet_product.py`** - Endpoint nou

### Fișiere Modificate
1. **`app/api/v1/endpoints/suppliers/__init__.py`** - Export promote_sheet_router
2. **`app/api/v1/routers/suppliers_router.py`** - Include promote_sheet_router

---

## 🚀 Pași Următori (Frontend)

### 1. Adaugă Buton "Promote" în UI

În `admin-frontend/src/pages/suppliers/SupplierProducts.tsx`:

```tsx
// În modal "Detalii Produs Furnizor"
{selectedProduct?.import_source === 'google_sheets' && (
  <Button
    type="primary"
    icon={<UploadOutlined />}
    onClick={handlePromoteToSupplierProduct}
  >
    Transformă în Produs Intern
  </Button>
)}
```

### 2. Implementează Handler

```tsx
const handlePromoteToSupplierProduct = async () => {
  if (!selectedProduct?.id) return;

  try {
    const response = await api.post(
      `/suppliers/sheets/${selectedProduct.id}/promote`,
      null,
      { params: { mark_sheet_inactive: true } }
    );

    message.success('Produs transformat cu succes în produs intern!');
    
    // Reload products
    await loadProducts();
    
    // Close modal
    setDetailModalVisible(false);
  } catch (error: any) {
    message.error(error.response?.data?.detail || 'Eroare la transformare');
  }
};
```

### 3. Adaugă Confirmare

```tsx
const handlePromoteToSupplierProduct = async () => {
  if (!selectedProduct?.id) return;

  Modal.confirm({
    title: 'Transformă în Produs Intern?',
    content: (
      <div>
        <p>Acest produs va fi transformat din Google Sheets în produs intern (1688).</p>
        <p><strong>Beneficii:</strong></p>
        <ul>
          <li>Management mai bun</li>
          <li>Editare mai rapidă</li>
          <li>Integrare cu workflow-ul 1688</li>
        </ul>
        <p><strong>Notă:</strong> Produsul Google Sheets va fi marcat ca inactiv.</p>
      </div>
    ),
    onOk: async () => {
      try {
        await api.post(`/suppliers/sheets/${selectedProduct.id}/promote`);
        message.success('Produs transformat cu succes!');
        await loadProducts();
        setDetailModalVisible(false);
      } catch (error: any) {
        message.error(error.response?.data?.detail || 'Eroare');
      }
    },
  });
};
```

---

## 🎉 Beneficii

### 1. **Flexibilitate**
- User-ul decide când să promoveze produse
- Poate păstra ambele versiuni (sheet + supplier product)

### 2. **Siguranță**
- Validări extensive
- Previne duplicate
- Rollback automat la eroare

### 3. **Transparență**
- Răspuns detaliat cu toate informațiile
- Log-uri pentru audit

### 4. **Scalabilitate**
- Poate fi folosit în batch
- Suportă migrare în masă

---

## 📝 Concluzie

### ✅ ENDPOINT IMPLEMENTAT COMPLET!

**Funcționalitate:**
- ✅ Clone ProductSupplierSheet → SupplierProduct
- ✅ Copy all fields (Chinese name, specs, price, URL)
- ✅ Link to supplier_id and local_product_id
- ✅ Mark sheet entry inactive (optional)
- ✅ Extensive validation
- ✅ Detailed response

**Integrare:**
- ✅ Router configurat
- ✅ Endpoint disponibil la `/suppliers/sheets/{sheet_id}/promote`
- ✅ Documentație completă

**Pași Următori:**
- 🔄 Adaugă buton în frontend (opțional)
- 🔄 Testează în UI
- 🔄 Migrează produse frecvent editate

---

**Data:** 21 Octombrie 2025  
**Status:** ✅ **IMPLEMENTAT ȘI DOCUMENTAT**  
**Implementat de:** Cascade AI Assistant  

**🚀 Endpoint-ul este gata de utilizare! Rebuild backend și testează! 🎯**
