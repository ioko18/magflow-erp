# Ghid: Creare Variante Locale înainte de Publicare eMAG

## 📋 Problema Rezolvată

**Întrebare:** "Produsele versiunea a doua, le voi posta manual, dar cum le 'lipesc' în baza de date ca să mi le afișeze împreună în pagina Products?"

**Răspuns:** Sistem complet implementat pentru tracking variante ÎNAINTE de publicare eMAG!

## 🎯 Soluția Implementată

### Sistem Hibrid în 3 Pași:

1. ✅ **Creare Locală** - Creezi EMG331-V2 în baza de date locală
2. ✅ **Publicare eMAG** - Publici manual în eMAG
3. ✅ **Sincronizare** - Sync-ul actualizează automat cu date reale

## 🚀 Workflow Complet pentru EMG331-V2

### Pas 1: Creare Variantă Locală

**Endpoint:** `POST /api/v1/product-variants-local/create`

**Request:**
```json
{
  "original_sku": "EMG331",
  "new_sku": "EMG331-V2",
  "new_name": "Generator de semnal XR2206 Premium 1Hz-1MHz",
  "new_ean": "8266294692465",
  "base_price": 45.00,
  "brand": "Generic",
  "manufacturer": "Generic",
  "description": "Generator de semnal de înaltă precizie XR2206, versiune premium cu carcasă îmbunătățită.",
  "reason": "Competitor attached to original - 2 offers",
  "account_type": "main"
}
```

**Response:**
```json
{
  "local_product_id": 123,
  "sku": "EMG331-V2",
  "name": "Generator de semnal XR2206 Premium 1Hz-1MHz",
  "variant_group_id": "uuid-here",
  "status": "created_locally",
  "next_steps": [
    "1. Local product created with ID 123",
    "2. Product visible in Products page",
    "3. Publish to eMAG manually with this SKU",
    "4. Run sync to update with eMAG data",
    "5. Variant relationship will be maintained"
  ]
}
```

**Ce se întâmplă:**
- ✅ Produs creat în `app.products` (baza de date locală)
- ✅ Variant group creat (EMG331 + EMG331-V2)
- ✅ Genealogie tracking activat
- ✅ **Produsul apare IMEDIAT în Products page!**

### Pas 2: Verificare în Products Page

**Accesează:** `http://localhost:5173/products`

**Vei vedea:**
```
SKU      │ Nume                              │ Marketplace    │ Prețuri
─────────┼───────────────────────────────────┼────────────────┼──────────
EMG331   │ Generator XR2206                  │ 🔵 MAIN 🟣 FBE │ MAIN: 0
         │                                   │                │ FBE: 26
─────────┼───────────────────────────────────┼────────────────┼──────────
EMG331-V2│ Generator XR2206 Premium          │ 🟢 Local       │ Local: 45
         │                                   │                │
```

**Badge-uri:**
- 🟢 **Local** - Produs în baza de date locală (nu pe eMAG încă)
- 🔵 **MAIN** - Produs pe eMAG MAIN
- 🟣 **FBE** - Produs pe eMAG FBE

### Pas 3: Publicare în eMAG

**Publici manual în eMAG** cu:
- SKU: `EMG331-V2`
- Nume: "Generator de semnal XR2206 Premium 1Hz-1MHz"
- EAN: `8266294692465`
- **IMPORTANT:** NU folosi `part_number_key` - creezi produs NOU

**eMAG îți va atribui:**
- `part_number_key`: ex. "ABC123XYZ"
- `id`: ID-ul produsului în eMAG

### Pas 4: Update după Publicare (Opțional)

**Endpoint:** `PATCH /api/v1/product-variants-local/EMG331-V2/after-emag-publish`

**Query params:**
```
?emag_part_number_key=ABC123XYZ
```

**Ce face:**
- Salvează PNK-ul în baza de date locală
- Pregătește pentru sync

### Pas 5: Sincronizare Automată

**Endpoint:** `POST /api/v1/emag/enhanced/sync/all-products`

**Ce se întâmplă:**
- ✅ Sync găsește EMG331-V2 în eMAG (după SKU)
- ✅ Actualizează produsul local cu date complete
- ✅ Adaugă preț real, stock, PNK, status
- ✅ **Variant relationship se menține automat!**

### Pas 6: Rezultat Final în Products Page

```
SKU      │ Nume                              │ Marketplace        │ Prețuri
─────────┼───────────────────────────────────┼────────────────────┼──────────
EMG331   │ Generator XR2206                  │ 🔵 MAIN 🟣 FBE     │ MAIN: 0
         │                                   │ 🔴 Competiție Mare │ FBE: 26
─────────┼───────────────────────────────────┼────────────────────┼──────────
EMG331-V2│ Generator XR2206 Premium          │ 🟢 Local 🔵 MAIN   │ Local: 45
         │                                   │ ✅ Fără competiție │ MAIN: 45
```

## 🎨 Vizualizare în Frontend

### Products Page - Unified View

**Filtrare:**
- "Toate produsele" - Vezi EMG331 și EMG331-V2 împreună
- "Doar Locale" - Vezi doar EMG331-V2 (înainte de sync)
- "Doar MAIN" - Vezi doar EMG331 (după sync vezi ambele)

**Coloană "Variante":**
- EMG331: "2 variante" (click pentru detalii)
- EMG331-V2: "Variantă de: EMG331"

### Detalii Variante

**Click pe "Vezi variante":**
```json
{
  "variant_group": {
    "original": {
      "sku": "EMG331",
      "type": "original",
      "is_primary": true,
      "has_competitors": true,
      "competitor_count": 2
    },
    "variants": [
      {
        "sku": "EMG331-V2",
        "type": "republished",
        "is_primary": false,
        "has_competitors": false,
        "reason": "Competitor attached to original"
      }
    ]
  }
}
```

## 📊 Endpoints Disponibile

### 1. Creare Variantă Locală
```
POST /api/v1/product-variants-local/create
```
Creează produs în DB local + variant tracking

### 2. Listă Variante Locale
```
GET /api/v1/product-variants-local/list
```
Vezi toate variantele create local

### 3. Update după Publicare
```
PATCH /api/v1/product-variants-local/{sku}/after-emag-publish
```
Adaugă PNK după publicare eMAG

### 4. Ștergere Variantă
```
DELETE /api/v1/product-variants-local/{sku}
```
Șterge dacă te răzgândești (înainte de publicare)

### 5. Vezi Toate Variantele
```
GET /api/v1/product-republish/variants/{sku}
```
Istoric complet variante + genealogie

## 🔄 Scenarii de Utilizare

### Scenariu 1: Tracking Imediat

**Vrei să vezi EMG331-V2 în Products ÎNAINTE de publicare:**

```bash
# 1. Creează local
curl -X POST http://localhost:8000/api/v1/product-variants-local/create \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "original_sku": "EMG331",
    "new_sku": "EMG331-V2",
    "new_name": "Generator XR2206 Premium",
    "base_price": 45.00,
    "reason": "Competitor attached"
  }'

# 2. Vezi în Products page
# http://localhost:5173/products
# EMG331-V2 apare cu badge "Local"

# 3. Publici în eMAG

# 4. Sync
curl -X POST http://localhost:8000/api/v1/emag/enhanced/sync/all-products \
  -H "Authorization: Bearer $TOKEN"

# 5. EMG331-V2 acum are badge "MAIN" și date complete
```

### Scenariu 2: Doar Tracking Relație

**Vrei doar să trackuiești că EMG331-V2 este variantă, fără produs local:**

```bash
# Publici direct în eMAG

# După publicare, creezi doar relația
curl -X POST http://localhost:8000/api/v1/product-republish/create-variant \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "original_sku": "EMG331",
    "new_sku": "EMG331-V2",
    "reason": "Competitor attached"
  }'

# Sync va aduce produsul din eMAG
# Relația va fi păstrată
```

### Scenariu 3: Planificare în Avans

**Vrei să pregătești mai multe variante:**

```bash
# Creează EMG331-V2
POST /product-variants-local/create
{
  "original_sku": "EMG331",
  "new_sku": "EMG331-V2",
  ...
}

# Creează EMG331-V3 (pentru viitor)
POST /product-variants-local/create
{
  "original_sku": "EMG331",
  "new_sku": "EMG331-V3",
  ...
}

# Toate apar în Products page
# Publici când ești gata
```

## 💡 Avantaje Sistem

### 1. Vizibilitate Imediată
- ✅ Vezi varianta în Products page IMEDIAT
- ✅ Nu trebuie să aștepți publicarea eMAG
- ✅ Tracking complet de la început

### 2. Flexibilitate
- ✅ Creezi local când vrei
- ✅ Publici în eMAG când ești gata
- ✅ Sync actualizează automat

### 3. Organizare
- ✅ Toate variantele împreună în Products
- ✅ Badge-uri clare (Local, MAIN, FBE)
- ✅ Istoric complet în genealogie

### 4. Siguranță
- ✅ Nu șterge nimic automat
- ✅ Poți șterge manual dacă te răzgândești
- ✅ Verificări de siguranță (nu șterge dacă are PNK)

## 🎯 Best Practices

### 1. Nume Descriptive
```json
{
  "original_sku": "EMG331",
  "new_sku": "EMG331-V2",  // Clar că e versiunea 2
  "new_name": "Generator XR2206 Premium"  // Diferit de original
}
```

### 2. Prețuri Realiste
```json
{
  "base_price": 45.00  // Preț realist pentru planning
}
```

### 3. Reason Clar
```json
{
  "reason": "Competitor attached - 2 offers on original"  // Documentează de ce
}
```

### 4. Sync După Publicare
```bash
# ÎNTOTDEAUNA rulează sync după publicare
POST /emag/enhanced/sync/all-products
```

## 📈 Raportare și Analytics

### Vezi Toate Variantele Tale

```bash
GET /api/v1/product-variants-local/list
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "local_variants": [
      {
        "id": 123,
        "sku": "EMG331-V2",
        "name": "Generator XR2206 Premium",
        "base_price": 45.00,
        "variant_count": 2,
        "variants": [...]
      }
    ],
    "total": 1
  }
}
```

### Istoric Complet

```bash
GET /api/v1/product-republish/variants/EMG331
```

Vezi:
- Toate variantele (EMG331, EMG331-V2, EMG331-V3...)
- Genealogie completă
- Motive de creare
- Status fiecare variantă

## ✅ Checklist pentru EMG331-V2

- [ ] 1. Creează variantă locală cu `/product-variants-local/create`
- [ ] 2. Verifică în Products page că apare cu badge "Local"
- [ ] 3. Publică manual în eMAG cu SKU "EMG331-V2"
- [ ] 4. (Opțional) Update cu PNK după publicare
- [ ] 5. Rulează sync `/emag/enhanced/sync/all-products`
- [ ] 6. Verifică că EMG331-V2 are acum badge "MAIN" și date complete
- [ ] 7. Verifică că ambele produse (EMG331 și EMG331-V2) apar împreună
- [ ] 8. Transferă stock treptat de la EMG331 la EMG331-V2

## 🎉 Rezultat Final

**În Products Page vei vedea:**

```
┌─────────────┬──────────────────────────┬─────────────────┬────────────────┐
│ SKU         │ Nume                     │ Marketplace     │ Prețuri        │
├─────────────┼──────────────────────────┼─────────────────┼────────────────┤
│ EMG331      │ Generator XR2206         │ 🔵 MAIN 🟣 FBE  │ MAIN: 0 RON    │
│             │ [2 variante]             │ 🔴 Competiție   │ FBE: 26 RON    │
├─────────────┼──────────────────────────┼─────────────────┼────────────────┤
│ EMG331-V2   │ Generator XR2206 Premium │ 🔵 MAIN         │ MAIN: 45 RON   │
│             │ [Variantă de: EMG331]    │ ✅ Fără comp.   │                │
└─────────────┴──────────────────────────┴─────────────────┴────────────────┘
```

**Perfect organizat, vizibil, și trackuit!** 🚀

---

**Sistemul este gata pentru utilizare!**

**Next Step:** Creează EMG331-V2 local și vezi-l imediat în Products page!
