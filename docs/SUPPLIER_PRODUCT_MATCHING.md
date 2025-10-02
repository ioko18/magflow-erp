# Sistem de Imperechere Produse Furnizori - Ghid Complet

## 📋 Cuprins
1. [Prezentare Generală](#prezentare-generală)
2. [Arhitectură](#arhitectură)
3. [Instalare și Configurare](#instalare-și-configurare)
4. [Utilizare](#utilizare)
5. [API Reference](#api-reference)
6. [Algoritmi de Matching](#algoritmi-de-matching)
7. [Best Practices](#best-practices)

---

## Prezentare Generală

### Problema
Ai produse electronice de la 4-6 furnizori chinezi (scraping de pe 1688.com) cu nume similare în chineză. Trebuie să identifici automat care produse sunt identice între furnizori pentru a compara prețurile și a selecta mereu furnizorul cu prețul cel mai bun.

### Soluția
Sistem inteligent de matching bazat pe:
- **Similaritate text** (nume în chineză + traducere automată)
- **Similaritate imagini** (perceptual hashing)
- **Clustering automat** pentru grupare produse similare
- **Dashboard pentru validare manuală**

### Beneficii
✅ **Automatizare**: Matching automat cu algoritmi avansați  
✅ **Comparare prețuri**: Identificare instant a celui mai bun preț  
✅ **Tracking istoric**: Monitorizare evoluție prețuri în timp  
✅ **Validare manuală**: Confirmare/respingere grupuri de matching  
✅ **Scalabilitate**: Suport pentru orice număr de furnizori și produse

---

## Arhitectură

### Componente Principale

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPPLIER MATCHING SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Import     │───▶│   Matching   │───▶│  Validation  │  │
│  │   Excel      │    │   Engine     │    │  Dashboard   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              PostgreSQL Database                      │  │
│  │  - supplier_raw_products                              │  │
│  │  - product_matching_groups                            │  │
│  │  - product_matching_scores                            │  │
│  │  - supplier_price_history                             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Modele Database

#### 1. **SupplierRawProduct**
Stochează produsele brute din Excel (scraping 1688.com):
- Nume produs în chineză
- Preț în CNY
- URL produs (1688.com)
- URL imagine
- Status matching
- Metadata (import batch, specificații, etc.)

#### 2. **ProductMatchingGroup**
Grupuri de produse similare de la furnizori diferiți:
- Nume reprezentativ
- Statistici preț (min, max, avg)
- Furnizor cu cel mai bun preț
- Scor de încredere
- Status validare (auto/manual)

#### 3. **ProductMatchingScore**
Scoruri detaliate de similaritate între perechi de produse:
- Similaritate text
- Similaritate imagini
- Scor total
- Algoritm folosit
- Threshold aplicat

#### 4. **SupplierPriceHistory**
Istoric prețuri pentru tracking în timp:
- Preț CNY
- Schimbare preț (absolut și procent)
- Data înregistrării
- Sursa (scraping, manual, API)

---

## Instalare și Configurare

### 1. Rulare Migrare Database

```bash
# Navighează în directorul proiectului
cd /Users/macos/anaconda3/envs/MagFlow

# Rulează migrarea
alembic upgrade head
```

### 2. Verificare Tabele Create

```sql
-- Conectează-te la PostgreSQL
psql -h localhost -p 5433 -U postgres -d magflow_erp

-- Verifică tabelele
\dt app.supplier_*
\dt app.product_matching_*

-- Verifică structura
\d app.supplier_raw_products
\d app.product_matching_groups
```

### 3. Adăugare Furnizori

Înainte de import, asigură-te că ai furnizorii creați în sistem:

```python
# Exemplu: Adăugare furnizor via API sau direct în DB
POST /api/v1/suppliers
{
    "name": "Furnizor 1 - 1688.com",
    "country": "China",
    "currency": "CNY",
    "is_active": true
}
```

---

## Utilizare

### Workflow Complet

```
1. Import Excel → 2. Matching Automat → 3. Validare Manuală → 4. Comparare Prețuri
```

### 1. Import Produse din Excel

#### Format Excel Așteptat

| Nume produs | Pret CNY | URL produs | URL imagine |
|-------------|----------|------------|-------------|
| 电子元件模块 | 12.50 | https://... | https://... |
| 传感器模块 | 8.30 | https://... | https://... |

#### Import via API

```bash
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/import/excel" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "supplier_id=1" \
  -F "file=@furnizor1_produse.xlsx"
```

#### Răspuns

```json
{
  "success": true,
  "batch_id": "import_20251001_005600_a1b2c3d4",
  "supplier_id": 1,
  "supplier_name": "Furnizor 1 - 1688.com",
  "total_rows": 150,
  "imported": 145,
  "skipped": 5,
  "errors": 0,
  "error_details": []
}
```

### 2. Rulare Matching Automat

#### Opțiune A: Matching Hibrid (RECOMANDAT)

Combină similaritate text (60%) + imagini (40%):

```bash
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/match/hybrid" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.75}'
```

#### Opțiune B: Matching Text Only

Bazat doar pe similaritate nume (chineza):

```bash
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/match/text" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.70}'
```

#### Opțiune C: Matching Image Only

Bazat doar pe similaritate imagini:

```bash
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/match/image" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.85}'
```

### 3. Vizualizare Grupuri de Matching

#### Listare Toate Grupurile

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/groups?limit=50" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Filtrare după Status

```bash
# Doar grupuri auto-matched (necesită validare)
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/groups?status=auto_matched" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Doar grupuri manual validate
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/groups?status=manual_matched" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Filtrare după Confidence Score

```bash
# Doar grupuri cu confidence > 0.80
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/groups?min_confidence=0.80" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Detalii Grup și Comparare Prețuri

#### Detalii Grup Specific

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/groups/123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Răspuns:
```json
{
  "id": 123,
  "group_name": "电子元件模块 5V 传感器",
  "group_name_en": "Electronic Component Module 5V Sensor",
  "product_count": 4,
  "min_price_cny": 8.30,
  "max_price_cny": 12.50,
  "avg_price_cny": 10.15,
  "best_supplier_id": 2,
  "confidence_score": 0.85,
  "matching_method": "hybrid",
  "status": "auto_matched",
  "products": [
    {
      "id": 456,
      "supplier_id": 2,
      "supplier_name": "Furnizor 2",
      "chinese_name": "电子元件模块",
      "price_cny": 8.30,
      "product_url": "https://...",
      "image_url": "https://..."
    },
    {
      "id": 457,
      "supplier_id": 1,
      "supplier_name": "Furnizor 1",
      "chinese_name": "传感器模块5V",
      "price_cny": 9.50,
      "product_url": "https://...",
      "image_url": "https://..."
    },
    // ... alte produse
  ]
}
```

#### Comparare Prețuri Detaliată

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/groups/123/price-comparison" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Răspuns:
```json
{
  "group_id": 123,
  "group_name": "电子元件模块 5V 传感器",
  "product_count": 4,
  "best_price_cny": 8.30,
  "worst_price_cny": 12.50,
  "avg_price_cny": 10.15,
  "savings_cny": 4.20,
  "savings_percent": 33.6,
  "products": [
    {
      "product_id": 456,
      "supplier_id": 2,
      "supplier_name": "Furnizor 2",
      "price_cny": 8.30,
      "chinese_name": "电子元件模块",
      "product_url": "https://...",
      "image_url": "https://..."
    },
    // ... sortate după preț crescător
  ]
}
```

### 5. Validare Manuală

#### Confirmare Grup (Matching Corect)

```bash
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/groups/123/confirm" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Respingere Grup (Matching Incorect)

```bash
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/groups/123/reject" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. Statistici Generale

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/stats" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Răspuns:
```json
{
  "total_products": 580,
  "matched_products": 420,
  "pending_products": 160,
  "total_groups": 105,
  "verified_groups": 45,
  "pending_groups": 60,
  "active_suppliers": 4,
  "matching_rate": 72.4
}
```

---

## API Reference

### Import Endpoints

| Endpoint | Method | Descriere |
|----------|--------|-----------|
| `/suppliers/matching/import/excel` | POST | Import produse din Excel |
| `/suppliers/matching/import/batches` | GET | Lista batch-uri import |
| `/suppliers/matching/import/summary` | GET | Sumar produse per furnizor |

### Matching Endpoints

| Endpoint | Method | Descriere |
|----------|--------|-----------|
| `/suppliers/matching/match/text` | POST | Matching bazat pe text |
| `/suppliers/matching/match/image` | POST | Matching bazat pe imagini |
| `/suppliers/matching/match/hybrid` | POST | Matching hibrid (recomandat) |

### Group Management Endpoints

| Endpoint | Method | Descriere |
|----------|--------|-----------|
| `/suppliers/matching/groups` | GET | Lista grupuri matching |
| `/suppliers/matching/groups/{id}` | GET | Detalii grup specific |
| `/suppliers/matching/groups/{id}/confirm` | POST | Confirmare grup |
| `/suppliers/matching/groups/{id}/reject` | POST | Respingere grup |
| `/suppliers/matching/groups/{id}/price-comparison` | GET | Comparare prețuri |

### Statistics Endpoints

| Endpoint | Method | Descriere |
|----------|--------|-----------|
| `/suppliers/matching/stats` | GET | Statistici generale |
| `/suppliers/matching/products` | GET | Lista produse raw |

---

## Algoritmi de Matching

### 1. Text Similarity

#### Normalizare Text
```python
# Elimină caractere speciale și zgomot
# Păstrează doar caractere chineze relevante
normalized = normalize_chinese_text("电子元件模块 5V 传感器")
# Output: "电子元件模块5v传感器"
```

#### Jaccard Similarity
```
Jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

Exemplu:
- Text A: "电子元件模块"
- Text B: "电子模块元件"
- Caractere comune: {电, 子, 元, 件, 模, 块}
- Jaccard = 6/6 = 1.0 (match perfect)

#### N-gram Similarity
```
Bigrams: "电子元件" → ["电子", "子元", "元件"]
Trigrams: "电子元件" → ["电子元", "子元件"]
```

#### Scor Final Text
```
text_score = 0.4 * jaccard + 0.4 * bigram + 0.2 * trigram
```

### 2. Image Similarity

#### Perceptual Hashing
```python
# Calculare hash perceptual (pHash)
# Rezistent la redimensionare, rotație, compresie
image_hash = calculate_perceptual_hash(image_url)
```

#### Hamming Distance
```python
# Distanța între două hash-uri
# 0 = identice, 64 = complet diferite
distance = hamming_distance(hash1, hash2)
similarity = 1 - (distance / 64)
```

### 3. Hybrid Matching (RECOMANDAT)

```
hybrid_score = (text_similarity * 0.6) + (image_similarity * 0.4)

if hybrid_score >= threshold:
    # Produsele sunt considerate match
    create_matching_group([product_a, product_b])
```

### Threshold-uri Recomandate

| Algoritm | Threshold Recomandat | Descriere |
|----------|---------------------|-----------|
| Text Only | 0.70 | Similaritate 70%+ în nume |
| Image Only | 0.85 | Imagini foarte similare |
| Hybrid | 0.75 | Combinație echilibrată |

---

## Best Practices

### 1. Pregătire Date Excel

✅ **DO:**
- Folosește nume consistente pentru coloane
- Asigură-te că prețurile sunt numerice
- Verifică că URL-urile sunt valide
- Include imagini de calitate

❌ **DON'T:**
- Nu lăsa celule goale în coloane obligatorii
- Nu folosi caractere speciale în nume fișiere
- Nu include produse duplicate în același Excel

### 2. Import Produse

✅ **DO:**
- Importă produse de la toți furnizorii înainte de matching
- Folosește batch_id pentru tracking
- Verifică statisticile după fiecare import

❌ **DON'T:**
- Nu rula matching cu produse de la un singur furnizor
- Nu ignora erorile de import

### 3. Matching

✅ **DO:**
- Începe cu matching hibrid (threshold 0.75)
- Validează manual grupurile cu confidence < 0.80
- Ajustează threshold-ul dacă ai prea multe/puține match-uri

❌ **DON'T:**
- Nu folosi threshold prea mic (< 0.60) - multe false positives
- Nu folosi threshold prea mare (> 0.90) - multe false negatives

### 4. Validare

✅ **DO:**
- Validează manual grupurile auto-matched
- Verifică imaginile produselor în grupuri
- Confirmă că specificațiile sunt similare

❌ **DON'T:**
- Nu confirma automat toate grupurile
- Nu ignora grupurile cu confidence scăzut

### 5. Monitorizare Prețuri

✅ **DO:**
- Rulează import periodic (săptămânal/lunar)
- Monitorizează istoric prețuri
- Setează alerte pentru schimbări mari de preț

❌ **DON'T:**
- Nu uita să actualizezi prețurile regulat
- Nu ignora tendințele de preț

---

## Exemple de Utilizare

### Exemplu 1: Import și Matching Complet

```bash
# 1. Import produse furnizor 1
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/import/excel" \
  -H "Authorization: Bearer $TOKEN" \
  -F "supplier_id=1" \
  -F "file=@furnizor1.xlsx"

# 2. Import produse furnizor 2
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/import/excel" \
  -H "Authorization: Bearer $TOKEN" \
  -F "supplier_id=2" \
  -F "file=@furnizor2.xlsx"

# 3. Import produse furnizor 3
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/import/excel" \
  -H "Authorization: Bearer $TOKEN" \
  -F "supplier_id=3" \
  -F "file=@furnizor3.xlsx"

# 4. Rulare matching hibrid
curl -X POST "http://localhost:8000/api/v1/suppliers/matching/match/hybrid" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.75}'

# 5. Verificare statistici
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/stats" \
  -H "Authorization: Bearer $TOKEN"

# 6. Listare grupuri pentru validare
curl -X GET "http://localhost:8000/api/v1/suppliers/matching/groups?status=auto_matched&min_confidence=0.70" \
  -H "Authorization: Bearer $TOKEN"
```

### Exemplu 2: Găsire Cel Mai Bun Preț

```python
import requests

# Autentificare
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "admin@example.com", "password": "secret"}
)
token = response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Obține toate grupurile
groups = requests.get(
    "http://localhost:8000/api/v1/suppliers/matching/groups",
    headers=headers
).json()

# Pentru fiecare grup, găsește cel mai bun preț
for group in groups:
    comparison = requests.get(
        f"http://localhost:8000/api/v1/suppliers/matching/groups/{group['id']}/price-comparison",
        headers=headers
    ).json()
    
    best_product = comparison["products"][0]  # Primul = cel mai ieftin
    
    print(f"Produs: {group['group_name']}")
    print(f"Cel mai bun furnizor: {best_product['supplier_name']}")
    print(f"Preț: {best_product['price_cny']} CNY")
    print(f"Economie: {comparison['savings_cny']} CNY ({comparison['savings_percent']:.1f}%)")
    print("---")
```

---

## Troubleshooting

### Problema: Import eșuează cu eroare "Missing columns"

**Soluție**: Verifică că Excel-ul are coloanele corecte:
```
Nume produs | Pret CNY | URL produs | URL imagine
```

Sau specifică mapping custom:
```python
column_mapping = {
    "chinese_name": "Product Name",
    "price_cny": "Price",
    "product_url": "Link",
    "image_url": "Image"
}
```

### Problema: Prea multe false positives (produse diferite grupate împreună)

**Soluție**: Crește threshold-ul:
```json
{"threshold": 0.80}  // în loc de 0.75
```

### Problema: Prea puține match-uri (produse similare nu sunt grupate)

**Soluție**: Scade threshold-ul:
```json
{"threshold": 0.65}  // în loc de 0.75
```

### Problema: Matching lent pentru multe produse

**Soluție**: 
1. Rulează matching în batch-uri mai mici
2. Folosește matching pe bază de imagini (mai rapid)
3. Optimizează indexurile database

---

## Roadmap Viitor

### Funcționalități Planificate

🔄 **În Dezvoltare:**
- [ ] Traducere automată chineza → română/engleză
- [ ] Computer vision pentru matching imagini (ResNet, CLIP)
- [ ] API pentru actualizare automată prețuri
- [ ] Dashboard React pentru management vizual
- [ ] Export rapoarte Excel cu comparații prețuri
- [ ] Notificări pentru schimbări mari de preț

🎯 **Viitor:**
- [ ] Machine learning pentru îmbunătățire matching
- [ ] Integrare directă cu API 1688.com
- [ ] Predicție tendințe prețuri
- [ ] Recomandări automate furnizor optim
- [ ] Multi-currency support (CNY, USD, EUR, RON)

---

## Suport

Pentru întrebări sau probleme:
- **Email**: support@magflow.ro
- **Documentation**: http://localhost:8000/docs
- **GitHub Issues**: [Link to repository]

---

**Versiune**: 1.0.0  
**Data**: 2025-10-01  
**Autor**: MagFlow ERP Development Team
