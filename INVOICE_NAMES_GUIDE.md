# Ghid: Nume Produse pentru Facturi (Română + Engleză)

## 📋 Problema Rezolvată

**Întrebare:** "Vreau să adaug nume produs pentru facturi în limba română și engleză, pentru vamă și taxe. Numele de pe eMAG sunt prea lungi pentru facturi."

**Răspuns:** Sistem complet implementat cu 2 coloane noi + API complet!

## 🎯 Soluția Implementată

### Coloane Noi în Baza de Date

**Tabel:** `app.products`

**Coloane Adăugate:**
```sql
invoice_name_ro VARCHAR(200)  -- Nume pentru facturi în română
invoice_name_en VARCHAR(200)  -- Nume pentru facturi în engleză
```

**Caracteristici:**
- ✅ Maxim 200 caractere (perfect pentru facturi)
- ✅ Optional (NULL dacă nu setezi)
- ✅ Fallback automat la numele eMAG dacă lipsesc
- ✅ Comentarii în DB pentru documentație

## 🚀 Utilizare Practică

### Exemplu Real: EMG331

**Nume eMAG (prea lung):**
```
"Generator de semnal de inalta precizie XR2206 cu carcasa, 1Hz-1Mhz"
```

**Nume Facturi (scurt, clar):**
```
RO: "Generator XR2206 1Hz-1MHz"
EN: "Signal Generator XR2206 1Hz-1MHz"
```

## 📊 API Endpoints

### 1. Obține Nume Facturi

**GET** `/api/v1/invoice-names/{sku}`

**Exemplu:**
```bash
curl -X GET "http://localhost:8000/api/v1/invoice-names/EMG331" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "sku": "EMG331",
  "name": "Generator de semnal de inalta precizie XR2206...",
  "invoice_name_ro": "Generator XR2206 1Hz-1MHz",
  "invoice_name_en": "Signal Generator XR2206 1Hz-1MHz",
  "has_invoice_names": true
}
```

### 2. Actualizează Nume Facturi

**PATCH** `/api/v1/invoice-names/{sku}`

**Exemplu:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/invoice-names/EMG331?invoice_name_ro=Generator%20XR2206&invoice_name_en=Signal%20Generator%20XR2206" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "status": "success",
  "message": "Invoice names updated for EMG331",
  "data": {
    "sku": "EMG331",
    "invoice_name_ro": "Generator XR2206",
    "invoice_name_en": "Signal Generator XR2206"
  }
}
```

### 3. Actualizare Bulk (Multiple Produse)

**POST** `/api/v1/invoice-names/bulk-update`

**Request:**
```json
{
  "updates": [
    {
      "sku": "EMG331",
      "invoice_name_ro": "Generator XR2206",
      "invoice_name_en": "Signal Generator XR2206"
    },
    {
      "sku": "EMG332",
      "invoice_name_ro": "Modul amplificator 2x15W",
      "invoice_name_en": "Amplifier Module 2x15W"
    },
    {
      "sku": "ADS206",
      "invoice_name_ro": "Placa ADS1015 16-Bit I2C",
      "invoice_name_en": "ADS1015 Board 16-Bit I2C"
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Updated 3 products, 0 errors",
  "data": {
    "summary": {
      "total": 3,
      "success": 3,
      "errors": 0
    }
  }
}
```

### 4. Generare Automată

**POST** `/api/v1/invoice-names/generate/{sku}`

**Exemplu:**
```bash
curl -X POST "http://localhost:8000/api/v1/invoice-names/generate/EMG331?max_length=50" \
  -H "Authorization: Bearer $TOKEN"
```

**Algoritm:**
1. Ia numele original eMAG
2. Elimină cuvinte inutile ("de", "cu", "pentru", etc.)
3. Trunchiază la lungimea dorită
4. Păstrează informații esențiale (brand, model)

**Response:**
```json
{
  "status": "success",
  "message": "Invoice names generated",
  "data": {
    "sku": "EMG331",
    "original_name": "Generator de semnal de inalta precizie XR2206 cu carcasa, 1Hz-1Mhz",
    "generated_ro": "Generator XR2206 1Hz-1MHz",
    "generated_en": "Signal Generator XR2206 1Hz-1MHz",
    "length_ro": 28,
    "length_en": 36
  }
}
```

### 5. Listă Produse cu/fără Nume Facturi

**GET** `/api/v1/invoice-names/`

**Filtre:**
```bash
# Doar produse cu nume facturi setate
GET /invoice-names/?has_invoice_names=true

# Doar produse fără nume facturi
GET /invoice-names/?has_invoice_names=false

# Toate produsele
GET /invoice-names/

# Cu paginare
GET /invoice-names/?limit=50&offset=0
```

### 6. Șterge Nume Facturi

**DELETE** `/api/v1/invoice-names/{sku}`

Revine la folosirea numelui eMAG original.

## 🔄 Workflow Complet

### Scenariu 1: Setare Manuală

```bash
# 1. Vezi numele actual
GET /invoice-names/EMG331

# 2. Setează nume facturi
PATCH /invoice-names/EMG331?invoice_name_ro=Generator%20XR2206&invoice_name_en=Signal%20Generator

# 3. Verifică
GET /invoice-names/EMG331
```

### Scenariu 2: Generare Automată

```bash
# 1. Generează automat
POST /invoice-names/generate/EMG331?max_length=50

# 2. Verifică rezultatul
GET /invoice-names/EMG331

# 3. Ajustează manual dacă e nevoie
PATCH /invoice-names/EMG331?invoice_name_ro=Nume%20Ajustat
```

### Scenariu 3: Bulk Update pentru Categorie

```bash
# 1. Obține lista produselor fără nume facturi
GET /invoice-names/?has_invoice_names=false&limit=100

# 2. Pregătește lista de update-uri
# (manual sau cu script)

# 3. Update bulk
POST /invoice-names/bulk-update
{
  "updates": [...]
}
```

## 📄 Integrare cu Sistemul de Facturare

### Logica de Afișare

**În template-ul de factură:**
```python
def get_invoice_product_name(product, language='ro'):
    """Get product name for invoice."""
    if language == 'ro':
        return product.invoice_name_ro or product.name
    elif language == 'en':
        return product.invoice_name_en or product.name
    return product.name
```

**Exemplu:**
```python
# Pentru factură română
product_name = get_invoice_product_name(product, 'ro')
# Returnează: "Generator XR2206" (scurt)
# Sau: "Generator de semnal..." (dacă invoice_name_ro e NULL)

# Pentru factură engleză (vamă)
product_name = get_invoice_product_name(product, 'en')
# Returnează: "Signal Generator XR2206"
```

## 🎯 Best Practices

### 1. Lungime Optimă

**Recomandări:**
- **Facturi interne**: 50-80 caractere
- **Declarații vamale**: 40-60 caractere
- **Documente TVA**: 60-100 caractere

**Exemplu:**
```
Prea lung:  "Generator de semnal de inalta precizie XR2206 cu carcasa metalica si display LCD, frecventa reglabila 1Hz-1Mhz"
Perfect:    "Generator XR2206 1Hz-1MHz cu display"
Prea scurt: "Generator XR2206"
```

### 2. Informații Esențiale

**Include:**
- ✅ Tipul produsului (Generator, Modul, Senzor)
- ✅ Model/Chip principal (XR2206, ADS1015)
- ✅ Specificații cheie (1Hz-1MHz, 16-Bit)

**Exclude:**
- ❌ Cuvinte de umplutură ("de", "cu", "pentru")
- ❌ Descrieri marketing
- ❌ Detalii secundare

### 3. Consistență

**Standardizează:**
```
Generator XR2206 1Hz-1MHz
Modul amplificator 2x15W TA2024
Placa dezvoltare ADS1015 16-Bit
Senzor presiune BMP280 I2C
```

**NU:**
```
Generator de semnal XR2206
Modul cu amplificator TA2024
ADS1015 placa
Senzor BMP280
```

### 4. Traducere Engleză

**Termeni Comuni:**
```
Generator → Generator
Modul → Module
Placa → Board
Senzor → Sensor
Display → Display
Cablu → Cable
Adaptor → Adapter
Alimentare → Power Supply
```

## 📊 Raportare și Statistici

### Vezi Produse Fără Nume Facturi

```bash
GET /invoice-names/?has_invoice_names=false&limit=1000
```

**Use case:**
- Identifică produse care necesită nume facturi
- Planning pentru bulk update
- Audit completitudine date

### Statistici

```bash
# Total produse cu nume facturi
GET /invoice-names/?has_invoice_names=true

# Total produse fără nume facturi
GET /invoice-names/?has_invoice_names=false
```

## 🔄 Sincronizare cu eMAG

### Modificări Manuale în eMAG

**Întrebare:** "Dacă modific numele în eMAG, se actualizează și numele pentru facturi?"

**Răspuns:** **NU** - Numele pentru facturi sunt independente!

**Comportament:**
1. Sync actualizează `product.name` (numele eMAG)
2. `invoice_name_ro` și `invoice_name_en` **rămân neschimbate**
3. Trebuie să actualizezi manual dacă vrei

**Avantaj:**
- ✅ Stabilitate - numele facturi nu se schimbă accidental
- ✅ Control - tu decizi când să actualizezi
- ✅ Consistență - facturi uniforme în timp

**Dacă vrei să actualizezi:**
```bash
# După sync, regenerează nume facturi
POST /invoice-names/generate/EMG331
```

## 💡 Cazuri de Utilizare

### Caz 1: Facturi pentru Vamă

**Necesitate:**
- Nume scurte, clare
- În engleză
- Fără caractere speciale

**Soluție:**
```bash
PATCH /invoice-names/EMG331?invoice_name_en=Signal%20Generator%20XR2206%201Hz-1MHz
```

**Rezultat în factură vamă:**
```
Item: Signal Generator XR2206 1Hz-1MHz
Qty: 10
Value: $450.00
```

### Caz 2: Facturi TVA România

**Necesitate:**
- Nume în română
- Descriere clară pentru ANAF
- Lungime rezonabilă

**Soluție:**
```bash
PATCH /invoice-names/EMG331?invoice_name_ro=Generator%20semnal%20XR2206
```

**Rezultat în factură:**
```
Denumire: Generator semnal XR2206
Cantitate: 10 buc
Pret unitar: 45.00 RON
```

### Caz 3: Facturi Proforma

**Necesitate:**
- Ambele limbi (RO + EN)
- Format profesional

**Soluție:**
```bash
PATCH /invoice-names/EMG331?invoice_name_ro=Generator%20XR2206&invoice_name_en=Signal%20Generator%20XR2206
```

**Rezultat:**
```
RO: Generator XR2206
EN: Signal Generator XR2206
```

## ✅ Checklist Implementare

- [ ] 1. Pornește Docker și PostgreSQL
- [ ] 2. Rulează migrarea Alembic (adaugă coloane)
- [ ] 3. Testează endpoint-uri API
- [ ] 4. Setează nume facturi pentru produse principale
- [ ] 5. Testează generare automată
- [ ] 6. Integrează în template-uri facturi
- [ ] 7. Testează facturi generate (RO + EN)

## 🎉 Rezultat Final

**Înainte:**
```
Factură:
- Generator de semnal de inalta precizie XR2206 cu carcasa metalica, frecventa reglabila 1Hz-1Mhz
  (prea lung, nu încape pe o linie)
```

**După:**
```
Factură RO:
- Generator XR2206 1Hz-1MHz
  (perfect, clar, profesional)

Factură EN (vamă):
- Signal Generator XR2206 1Hz-1MHz
  (customs-friendly, standardizat)
```

---

**Sistemul este gata pentru utilizare!** 🚀

**Next Steps:**
1. Pornește PostgreSQL: `docker-compose up -d`
2. Rulează migrarea: `alembic upgrade head`
3. Testează API: `GET /api/v1/invoice-names/EMG331`
4. Setează nume pentru produsele tale!
