# Ghid Rapid: Low Stock Products - Supplier Selection
**Data:** 2025-10-14  
**Versiune:** 2.0 (cu Auto-Sync)

---

## 🚀 Cum Să Folosești (Nou & Îmbunătățit)

### Pasul 1: Sincronizează Produsele eMAG

```
1. Mergi la pagina "eMAG Products"
2. Click pe butonul "Sync Products"
3. Selectează contul: FBE sau MAIN
4. Așteaptă 2-3 minute
5. ✅ GATA! Produsele ȘI inventarul sunt sincronizate automat
```

**NU MAI TREBUIE să apeși "Sync eMAG FBE" separat!** 🎉

---

### Pasul 2: Vezi Produsele cu Stoc Scăzut

```
1. Mergi la pagina "Low Stock Products - Supplier Selection"
2. Selectează filtru: "FBE Account" sau "MAIN Account"
3. ✅ Produsele apar automat!
```

---

## 🎯 Ce S-a Schimbat?

### Înainte (Vechi)
```
❌ Pasul 1: Sync eMAG Products
❌ Pasul 2: Sync eMAG FBE (manual, separat)
❌ Pasul 3: Refresh Low Stock Products
❌ Total: 3 pași, confuz
```

### Acum (Nou)
```
✅ Pasul 1: Sync eMAG Products (totul se întâmplă automat)
✅ Pasul 2: Vezi Low Stock Products
✅ Total: 2 pași, simplu
```

---

## 📊 Funcții Disponibile

### 1. Filtrare

**Filtru Account:**
- **FBE:** Produse din eMAG Fulfillment
- **MAIN:** Produse din depozitul principal
- **ALL:** Toate produsele

**Filtru Status:**
- **Out of Stock:** Stoc 0
- **Critical:** Sub minimum stock
- **Low Stock:** Sub reorder point
- **ALL:** Toate produsele cu probleme

### 2. Quick Actions

**Select Preferred:**
- Auto-selectează furnizorii preferați pentru toate produsele
- Prioritate: Verified → Preferred → Cel mai ieftin

**Select Cheapest:**
- Auto-selectează cel mai ieftin furnizor pentru fiecare produs
- Ideal pentru comenzi mari

**Clear All:**
- Șterge toate selecțiile

### 3. Export Excel

**După ce ai selectat furnizorii:**
1. Click "Export to Excel"
2. Se generează un fișier Excel
3. Fișierul conține:
   - Foi separate pentru fiecare furnizor
   - Imagini produse
   - Prețuri și cantități
   - Link-uri către furnizori
   - Format gata pentru comandă

### 4. Create Draft POs

**Creează automat comenzi draft:**
1. Selectează furnizorii pentru produse
2. Click "Create Draft POs"
3. Se creează automat o comandă draft pentru fiecare furnizor
4. Mergi la "Purchase Orders" pentru a finaliza comenzile

---

## 💡 Tips & Tricks

### Tip 1: Folosește Filtrul Account
```
✅ Filtrează după "FBE" pentru produse eMAG Fulfillment
✅ Acestea sunt cele mai importante (eMAG gestionează stocul)
✅ Comenzile FBE trebuie procesate mai repede
```

### Tip 2: Verified Suppliers Only
```
✅ Activează "Show Verified Only"
✅ Vezi doar furnizorii verificați și de încredere
✅ Reduce riscul de produse de calitate slabă
```

### Tip 3: Expand All
```
✅ Click "Expand All" pentru a vedea toți furnizorii deodată
✅ Compară prețurile rapid
✅ Identifică cele mai bune oferte
```

### Tip 4: Edit Reorder Quantity
```
✅ Click pe cantitatea de reorder
✅ Modifică manual dacă știi că ai nevoie de mai mult/mai puțin
✅ Salvează automat
```

---

## 🔧 Troubleshooting

### Problema: Nu văd produse

**Soluție 1: Verifică filtrul**
```
1. Asigură-te că ai selectat contul corect (FBE/MAIN)
2. Încearcă să schimbi filtrul la "ALL"
3. Verifică că ai produse cu stoc scăzut
```

**Soluție 2: Sincronizează din nou**
```
1. Mergi la "eMAG Products"
2. Click "Sync Products"
3. Așteaptă 2-3 minute
4. Refresh pagina "Low Stock Products"
```

**Soluție 3: Verifică că ai produse eMAG**
```sql
-- Rulează în database
SELECT account_type, COUNT(*) 
FROM app.emag_products_v2 
WHERE is_active = true 
GROUP BY account_type;
```

### Problema: Furnizorii nu apar

**Soluție:**
```
1. Verifică că ai importat Google Sheets cu furnizori
2. Mergi la "Product Supplier Sheets"
3. Verifică că există furnizori pentru SKU-urile tale
4. Asigură-te că furnizorii sunt activi (is_active = true)
```

### Problema: Export Excel eșuează

**Soluție:**
```
1. Verifică că ai selectat cel puțin un produs
2. Asigură-te că fiecare produs are un furnizor selectat
3. Încearcă cu mai puține produse (max 100 pe export)
4. Verifică logs pentru erori: docker logs magflow_app
```

---

## 📋 Checklist Zilnic

### Dimineața
```
☐ Sincronizează produsele eMAG (FBE + MAIN)
☐ Verifică Low Stock Products (filtru FBE)
☐ Identifică produsele critice (out of stock)
☐ Selectează furnizori pentru produse urgente
☐ Creează Draft POs pentru comenzi urgente
```

### După-amiaza
```
☐ Verifică din nou Low Stock (pot apărea comenzi noi)
☐ Procesează comenzile draft create dimineața
☐ Trimite comenzi către furnizori
☐ Actualizează statusul comenzilor în sistem
```

---

## 🎯 Best Practices

### 1. Sincronizare Regulată
```
✅ Sincronizează produsele eMAG de 2-3 ori pe zi
✅ Dimineața (9:00), După-amiaza (14:00), Seara (18:00)
✅ Asigură date actualizate pentru decizii corecte
```

### 2. Prioritizare
```
✅ Prioritate 1: Out of Stock (stoc 0)
✅ Prioritate 2: Critical (sub minimum stock)
✅ Prioritate 3: Low Stock (sub reorder point)
```

### 3. Furnizori Verificați
```
✅ Preferă furnizorii verificați (is_verified = true)
✅ Verifică istoricul comenzilor anterioare
✅ Compară prețurile între furnizori
```

### 4. Cantități Optime
```
✅ Folosește cantitatea recomandată (reorder_quantity)
✅ Ajustează manual dacă știi că ai nevoie de mai mult
✅ Consideră timpul de livrare (lead time)
```

---

## 📞 Suport

### Logs
```bash
# Vezi logs aplicație
docker logs -f magflow_app | grep -i "low stock\|inventory"

# Vezi logs worker (Celery)
docker logs -f magflow_worker | grep -i "sync\|inventory"
```

### Database Queries
```sql
-- Verifică inventory items
SELECT w.code, COUNT(ii.id) as items
FROM app.warehouses w
LEFT JOIN app.inventory_items ii ON ii.warehouse_id = w.id
WHERE w.code IN ('EMAG-FBE', 'EMAG-MAIN')
GROUP BY w.code;

-- Verifică produse low stock
SELECT COUNT(*) 
FROM app.inventory_items ii
JOIN app.warehouses w ON ii.warehouse_id = w.id
WHERE w.code = 'EMAG-FBE' 
AND ii.available_quantity <= ii.reorder_point;
```

---

## 🎉 Concluzie

**Pagina "Low Stock Products - Supplier Selection" este acum complet automată!**

```
✅ Sincronizare automată a inventarului
✅ Un singur buton pentru tot
✅ Date actualizate în timp real
✅ Export Excel cu imagini
✅ Creare automată comenzi draft
```

**Enjoy! 🚀**

---

**Versiune:** 2.0  
**Data:** 2025-10-14  
**Auto-Sync:** ✅ Activat  
**Status:** Production Ready
