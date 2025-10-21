# Fix: Missing Constraint Error
**Data:** 2025-10-14 02:00 UTC+03:00  
**Status:** ✅ REZOLVAT

---

## 🐛 Problema

**Eroare:**
```
asyncpg.exceptions.UndefinedObjectError: 
constraint "uq_inventory_items_product_warehouse" for table "inventory_items" does not exist
```

**Cauza:**
- Codul folosea `constraint="uq_inventory_items_product_warehouse"` în `ON CONFLICT`
- Dar acest constraint **nu există** în baza de date
- Probabil a fost șters sau nu a fost creat niciodată

---

## ✅ Soluția

În loc să folosim numele constraint-ului (care nu există), folosim **coloanele direct** cu `index_elements`:

### ÎNAINTE (Rău):
```python
.on_conflict_do_update(
    constraint="uq_inventory_items_product_warehouse",  # ❌ Nu există!
    set_={...}
)
```

### DUPĂ (Bine):
```python
.on_conflict_do_update(
    index_elements=["product_id", "warehouse_id"],  # ✅ Folosește coloanele direct
    set_={...}
)
```

---

## 📁 Fișier Modificat

**File:** `app/api/v1/endpoints/inventory/emag_inventory_sync.py`  
**Linia:** 166  
**Modificare:** `constraint=` → `index_elements=`

---

## 🎯 Impact

- ✅ Sincronizarea inventarului funcționează acum
- ✅ Nu mai depinde de existența constraint-ului
- ✅ Folosește index-ul implicit pe (product_id, warehouse_id)

---

## 🚀 Testare

```bash
# Restart servicii
docker-compose restart magflow_app

# Testează sync
# UI: eMAG Products → Sync Products (FBE)

# Verifică că nu mai sunt erori
docker logs magflow_app | grep "constraint.*does not exist"
# Ar trebui să nu găsească nimic
```

---

**Status:** ✅ FIXED  
**Ready for:** Production
