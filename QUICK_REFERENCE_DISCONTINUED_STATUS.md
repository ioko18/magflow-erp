# Quick Reference: Statusul "Discontinuat" - Ghid Rapid

## 🎯 Ce înseamnă "Discontinuat"?

Un produs **discontinuat** (`is_discontinued = true`) înseamnă că:
- ❌ Nu mai este disponibil de la furnizor
- ❌ Nu poate fi comandat
- ❌ Trebuie marcat automat ca inactiv

---

## 🔧 Cum modific statusul?

### Metoda 1: Interfață Web (Recomandat) ⭐

1. Accesează pagina **Products** (http://localhost:3000/products)
2. Click pe **Edit** (✏️) pentru produsul dorit
3. Scroll la secțiunea **"Status Produs"**
4. Toggle switch-ul **"Status Discontinuat"**
5. Click **"Actualizează"**

### Metoda 2: API Toggle Rapid

```bash
# Obține token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret"}' \
  | jq -r '.access_token')

# Toggle discontinued pentru produs ID=4
curl -X POST http://localhost:8000/api/v1/products/4/toggle-discontinued \
  -H "Authorization: Bearer $TOKEN"
```

### Metoda 3: Bulk Update (Multiple produse)

```bash
curl -X POST http://localhost:8000/api/v1/products/bulk-toggle-discontinued \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_ids": [1, 2, 4],
    "discontinued": false
  }'
```

---

## 📊 Verificare Status

### În Interfață Web
- Coloana **"Status"** afișează tag-ul roșu **"Discontinuat"**
- Filtrează cu **"🚫 Doar discontinuate"** din dropdown

### În Baza de Date
```sql
SELECT id, sku, name, is_active, is_discontinued 
FROM app.products 
WHERE sku IN ('EMG180', 'BN283', 'MCP601');
```

### Via API
```bash
curl -X GET http://localhost:8000/api/v1/products/4 \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data.is_discontinued'
```

---

## 🆕 Endpoint-uri Noi

| Endpoint | Metodă | Descriere |
|----------|--------|-----------|
| `/products/{id}/toggle-discontinued` | POST | Toggle rapid discontinued status |
| `/products/bulk-toggle-discontinued` | POST | Actualizare în masă |
| `/products/{id}` | PATCH | Update cu `is_discontinued` field |

---

## ⚠️ Important!

- Când marchezi un produs ca **discontinued**, acesta devine automat **inactiv**
- Toate modificările sunt **loggate** pentru audit
- Poți **reactiva** un produs discontinued prin toggle

---

## 🐛 Probleme Comune

**Q: Switch-ul nu se salvează?**  
A: Verifică că browser-ul nu are cache vechi. Refresh cu Ctrl+F5.

**Q: Produsul rămâne activ după marcare ca discontinued?**  
A: Folosește endpoint-ul `/toggle-discontinued` care face auto-inactivare.

**Q: Cum văd istoricul modificărilor?**  
A: `GET /products/{id}/change-log?field_name=is_discontinued`

---

**Documentație completă:** `PRODUCT_DISCONTINUED_STATUS_IMPROVEMENTS.md`
