# Fix AttributeError - supplier_product_name - 20 Octombrie 2025

## Eroarea Gravă

```
'ProductSupplierSheet' object has no attribute 'supplier_product_name'
```

## Cauza

În backend, am încercat să serializez câmpul `supplier_product_name`, dar modelul `ProductSupplierSheet` **NU are acest câmp**!

### Câmpuri Disponibile în ProductSupplierSheet:
- ✅ `id`
- ✅ `sku` (nu `supplier_product_name`!)
- ✅ `supplier_name`
- ✅ `supplier_product_chinese_name`
- ✅ `supplier_product_specification`
- ✅ `supplier_url`
- ✅ `supplier_contact`
- ✅ `supplier_notes`
- ✅ `price_cny`
- ✅ `calculated_price_ron`
- ✅ `exchange_rate_cny_ron`
- ✅ `is_preferred`
- ✅ `is_verified`
- ✅ `is_active`
- ✅ `created_at`
- ✅ `updated_at`
- ✅ `price_updated_at`

### Câmpuri care NU EXISTĂ:
- ❌ `supplier_product_name` - NU EXISTĂ!

## Soluția

Am eliminat câmpul inexistent din serializare:

**Fișier:** `/app/api/v1/endpoints/suppliers/suppliers.py` (linii 2556-2577)

```python
# ÎNAINTE (GREȘIT):
sheet_dict = {
    "id": supplier_sheet.id,
    "sku": supplier_sheet.sku,
    "supplier_name": supplier_sheet.supplier_name,
    "supplier_product_name": supplier_sheet.supplier_product_name,  # ❌ NU EXISTĂ!
    "supplier_product_chinese_name": supplier_sheet.supplier_product_chinese_name,
    ...
}

# DUPĂ (CORECT):
sheet_dict = {
    "id": supplier_sheet.id,
    "sku": supplier_sheet.sku,
    "supplier_name": supplier_sheet.supplier_name,
    # ✅ Eliminat supplier_product_name
    "supplier_product_chinese_name": supplier_sheet.supplier_product_chinese_name,
    "supplier_product_specification": supplier_sheet.supplier_product_specification,
    "supplier_url": supplier_sheet.supplier_url,
    "supplier_contact": supplier_sheet.supplier_contact,
    "supplier_notes": supplier_sheet.supplier_notes,
    "price_cny": supplier_sheet.price_cny,
    "calculated_price_ron": supplier_sheet.calculated_price_ron,
    "exchange_rate_cny_ron": supplier_sheet.exchange_rate_cny_ron,
    "is_preferred": supplier_sheet.is_preferred,
    "is_verified": supplier_sheet.is_verified,
    "is_active": supplier_sheet.is_active,
    "import_source": "google_sheets",
    "created_at": supplier_sheet.created_at.isoformat() if supplier_sheet.created_at else None,
    "updated_at": supplier_sheet.updated_at.isoformat() if supplier_sheet.updated_at else None,
    "price_updated_at": supplier_sheet.price_updated_at.isoformat() if supplier_sheet.price_updated_at else None,
}
```

## Diferența între Modele

### ProductSupplierSheet (Google Sheets)
- Folosit pentru produse importate din Google Sheets
- Câmpuri: `sku`, `supplier_name`, `supplier_product_chinese_name`
- **NU are** `supplier_product_name`

### SupplierProduct (1688)
- Folosit pentru produse 1688
- Câmpuri: `supplier_product_name`, `supplier_product_chinese_name`
- **ARE** `supplier_product_name`

## Lecție Învățată

**Întotdeauna verifică structura modelului înainte de a serializa!**

```python
# ✅ BUNĂ PRACTICĂ:
# 1. Verifică modelul în /app/models/
# 2. Folosește doar câmpurile care există
# 3. Testează endpoint-ul după modificare
```

## Fișiere Modificate

**Backend:**
- `/app/api/v1/endpoints/suppliers/suppliers.py` (linia 2561 - eliminat `supplier_product_name`)

**Documentație:**
- `/FIX_ATTRIBUTE_ERROR_2025_10_20.md` - Acest document

## Status

### ✅ **EROAREA REZOLVATĂ**

Backend-ul acum serializează doar câmpurile care există în modelul `ProductSupplierSheet`.

---

**Data:** 20 Octombrie 2025  
**Verificat de:** Cascade AI Assistant  
**Status:** ✅ AttributeError rezolvat - eliminat câmp inexistent
