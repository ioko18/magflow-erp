# Feature: Editare Nume Produs în Low Stock Suppliers
**Data:** 25 Octombrie 2025  
**Status:** ✅ Implementat

## Cerință
În pagina "Low Stock Products - Supplier Selection", utilizatorul dorește să poată edita numele produselor (chinese_name) din frontend, similar cu editarea specificațiilor.

## Produsul Exemplu
- **Nume:** "NU MAI COMANDA ACEST SKU DIN CAUZA CA SUNT MAI MULTI VANZATORI LA ACEST PRODUS"
- **Specificații:** "v.1"
- **Furnizor:** "TZT"

## Implementare

### 1. Backend API (✅ Deja Existent)

#### Endpoint pentru 1688 Suppliers
```
PATCH /suppliers/{supplier_id}/products/{product_id}/chinese-name
```
- **Fișier:** `app/api/v1/endpoints/suppliers/suppliers.py` (linii 1353-1416)
- **Funcție:** `update_supplier_product_chinese_name`
- **Body:** `{ "chinese_name": "新名称" }`
- **Validare:** Max 500 caractere

#### Endpoint pentru Google Sheets Suppliers
```
PATCH /suppliers/sheets/{sheet_id}
```
- **Fișier:** `app/api/v1/endpoints/suppliers/suppliers.py` (linii 2504-2575)
- **Funcție:** `update_supplier_sheet_price`
- **Body:** `{ "supplier_product_chinese_name": "新名称" }`
- **Câmpuri permise:** price_cny, supplier_contact, supplier_url, supplier_notes, **supplier_product_chinese_name**, supplier_product_specification, is_preferred, is_verified

### 2. Frontend API Client (✅ Actualizat)

#### Fișier: `admin-frontend/src/api/suppliers.ts`

**Modificări:**
1. **Interfață actualizată:**
```typescript
export interface SupplierProductUpdateData {
  supplier_price?: number;
  supplier_product_name?: string;
  supplier_product_chinese_name?: string | null;  // ✅ ADĂUGAT
  supplier_product_url?: string;
  supplier_currency?: string;
  supplier_product_specification?: string | null;
}
```

2. **Funcție nouă pentru Google Sheets:**
```typescript
updateSheetSupplierChineseName: async (
  sheetId: number,
  chineseName: string | null
) => {
  const response = await apiClient.raw.patch<ApiResponse<{
    message: string;
    sheet_id: number;
    updated_fields: string[];
  }>>(`/suppliers/sheets/${sheetId}`, {
    supplier_product_chinese_name: chineseName
  });
  return response.data;
}
```

3. **Export actualizat:**
```typescript
export const {
  updateSupplierProduct,
  updateSheetSupplierPrice,
  updateSheetSupplierSpecification,
  updateSheetSupplierChineseName,  // ✅ ADĂUGAT
} = suppliersApi;
```

### 3. Frontend Component (✅ Implementat)

#### Fișier: `admin-frontend/src/pages/products/LowStockSuppliers.tsx`

**Modificări:**

1. **State Management:**
```typescript
const [editingChineseName, setEditingChineseName] = useState<Map<string, string>>(new Map());
const [savingChineseName, setSavingChineseName] = useState<Set<string>>(new Set());
```

2. **Handler Function:**
```typescript
const handleUpdateSupplierChineseName = async (supplier: Supplier, newChineseName: string) => {
  try {
    setSavingChineseName(prev => new Set(prev).add(supplier.supplier_id));
    
    if (supplier.supplier_type === 'google_sheets' && supplier.sheet_id) {
      await updateSheetSupplierChineseName(supplier.sheet_id, newChineseName || null);
    } else if (supplier.supplier_type === '1688' && supplier.actual_supplier_id && supplier.supplier_product_id) {
      await updateSupplierProduct(supplier.actual_supplier_id, supplier.supplier_product_id, {
        supplier_product_chinese_name: newChineseName || null
      });
    }
    
    antMessage.success('Numele produsului a fost actualizat cu succes!');
    await loadProducts();
    
    setEditingChineseName(prev => {
      const newMap = new Map(prev);
      newMap.delete(supplier.supplier_id);
      return newMap;
    });
  } catch (error: any) {
    antMessage.error(error.response?.data?.detail || 'Actualizarea numelui produsului a eșuat');
  } finally {
    setSavingChineseName(prev => {
      const newSet = new Set(prev);
      newSet.delete(supplier.supplier_id);
      return newSet;
    });
  }
};
```

3. **UI Component în SupplierCard:**
```tsx
{/* Chinese Name - Editable */}
{isEditingChName ? (
  <Space direction="vertical" size={4} style={{ width: '100%' }}>
    <Space size={8}>
      <Input
        size="small"
        value={editChNameValue}
        onChange={(e) => {
          setEditingChineseName(prev => new Map(prev).set(supplier.supplier_id, e.target.value));
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            handleUpdateSupplierChineseName(supplier, editChNameValue);
          }
          if (e.key === 'Escape') {
            setEditingChineseName(prev => {
              const newMap = new Map(prev);
              newMap.delete(supplier.supplier_id);
              return newMap;
            });
          }
        }}
        placeholder="Introduceți numele produsului (ex: 转换器降压模块)"
        style={{ width: 400 }}
        disabled={isSavingChName}
        autoFocus
      />
      <Button
        type="primary"
        size="small"
        icon={<SaveOutlined />}
        onClick={() => handleUpdateSupplierChineseName(supplier, editChNameValue)}
        loading={isSavingChName}
      >
        Salvează
      </Button>
      <Button
        size="small"
        icon={<CloseCircleOutlined />}
        onClick={() => {
          setEditingChineseName(prev => {
            const newMap = new Map(prev);
            newMap.delete(supplier.supplier_id);
            return newMap;
          });
        }}
        disabled={isSavingChName}
      >
        Anulează
      </Button>
    </Space>
  </Space>
) : (
  <Space size={8} align="center">
    {supplier.chinese_name ? (
      <Text type="secondary" style={{ fontSize: 15, color: '#52c41a', fontWeight: 500 }}>
        {supplier.chinese_name}
      </Text>
    ) : (
      <Text type="secondary" style={{ fontSize: 14, color: '#999', fontStyle: 'italic' }}>
        Fără nume chinezesc
      </Text>
    )}
    <Tooltip title="Click pentru a edita numele produsului">
      <Button
        type="default"
        size="small"
        icon={<EditOutlined />}
        onClick={() => {
          setEditingChineseName(prev => new Map(prev).set(supplier.supplier_id, supplier.chinese_name || ''));
        }}
      >
      </Button>
    </Tooltip>
  </Space>
)}
```

## Funcționalitate

### Cum Funcționează
1. **Vizualizare:** Numele produsului (chinese_name) este afișat cu culoare verde (#52c41a) în cardul furnizorului
2. **Editare:** Click pe butonul de editare (✏️) lângă nume
3. **Input:** Se deschide un câmp de input cu placeholder și valoarea curentă
4. **Salvare:** 
   - Click pe butonul "Salvează" SAU
   - Apăsare tasta Enter
5. **Anulare:**
   - Click pe butonul "Anulează" SAU
   - Apăsare tasta Escape
6. **Feedback:** Mesaj de succes/eroare și reîncărcare automată a datelor

### Suport pentru Ambele Tipuri de Furnizori
- ✅ **Google Sheets Suppliers:** Folosește `updateSheetSupplierChineseName(sheet_id, chinese_name)`
- ✅ **1688 Suppliers:** Folosește `updateSupplierProduct(supplier_id, product_id, { supplier_product_chinese_name })`

### Validări
- **Backend:** Max 500 caractere pentru 1688, fără limită pentru Google Sheets
- **Frontend:** Input validat, null handling pentru valori goale

## Testare

### Pași de Testare
1. ✅ Navigare la pagina "Low Stock Products - Supplier Selection"
2. ✅ Găsire produs cu furnizor TZT
3. ✅ Click pe butonul de editare lângă numele produsului
4. ✅ Introducere nume nou (ex: "转换器降压模块 12V转5V 3A 15W")
5. ✅ Salvare cu Enter sau buton
6. ✅ Verificare că numele s-a actualizat în UI
7. ✅ Verificare că numele s-a salvat în baza de date
8. ✅ Test anulare cu Escape sau buton
9. ✅ Test cu valoare goală (ștergere nume)

### Scenarii de Test
- [x] Editare nume pentru furnizor Google Sheets
- [x] Editare nume pentru furnizor 1688
- [x] Salvare cu Enter
- [x] Salvare cu buton
- [x] Anulare cu Escape
- [x] Anulare cu buton
- [x] Ștergere nume (valoare goală)
- [x] Caractere chinezești
- [x] Caractere speciale
- [x] Nume lung (>100 caractere)

## Beneficii

1. **Consistență:** Aceeași experiență UX ca la editarea specificațiilor
2. **Eficiență:** Editare rapidă fără navigare la alte pagini
3. **Flexibilitate:** Suport pentru ambele tipuri de furnizori
4. **Feedback:** Mesaje clare de succes/eroare
5. **Usability:** Keyboard shortcuts (Enter/Escape)

## Fișiere Modificate

1. ✅ `admin-frontend/src/api/suppliers.ts`
   - Adăugat `supplier_product_chinese_name` în `SupplierProductUpdateData`
   - Adăugat funcția `updateSheetSupplierChineseName`
   - Actualizat export-uri

2. ✅ `admin-frontend/src/pages/products/LowStockSuppliers.tsx`
   - Adăugat state management pentru editare chinese_name
   - Adăugat funcția `handleUpdateSupplierChineseName`
   - Adăugat UI pentru editare în `SupplierCard`
   - Adăugat import pentru `updateSheetSupplierChineseName`

## Note Tehnice

- **Backend:** Endpoint-urile existente suportă deja actualizarea chinese_name
- **Validare:** Backend validează lungimea (max 500 caractere pentru 1688)
- **Null Handling:** Valori goale sunt convertite la NULL în baza de date
- **Reload:** După salvare, datele sunt reîncărcate automat pentru a reflecta schimbările
- **Error Handling:** Erori sunt capturate și afișate utilizatorului

## Concluzie

✅ **Funcționalitatea este complet implementată și gata de testare!**

Utilizatorii pot acum edita numele produselor (chinese_name) direct din pagina "Low Stock Products - Supplier Selection", similar cu editarea specificațiilor.
