# Google Sheets Product Import - Ghid de Configurare și Utilizare

## 📋 Prezentare Generală

Acest sistem permite importul automat al produselor din Google Sheets în MagFlow ERP și maparea lor automată către conturile eMAG MAIN și FBE pe baza SKU-ului.

## 🎯 Funcționalități

- ✅ Import automat produse din Google Sheets
- ✅ Mapare automată pe SKU către eMAG MAIN și FBE
- ✅ Interfață web pentru gestionare mapări
- ✅ Mapare manuală pentru produse nemapate automat
- ✅ Statistici detaliate despre mapări
- ✅ Istoric complet al importurilor

## 🔧 Configurare Inițială

### 1. Crearea Service Account în Google Cloud

1. Accesează [Google Cloud Console](https://console.cloud.google.com/)
2. Creează un proiect nou sau selectează unul existent
3. Activează **Google Sheets API**:
   - Mergi la "APIs & Services" > "Library"
   - Caută "Google Sheets API"
   - Click "Enable"

4. Creează Service Account:
   - Mergi la "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Completează detaliile și creează

5. Generează cheia JSON:
   - Click pe service account-ul creat
   - Mergi la tab-ul "Keys"
   - Click "Add Key" > "Create new key"
   - Selectează "JSON"
   - Descarcă fișierul

### 2. Configurare Fișier service_account.json

1. Redenumește fișierul descărcat în `service_account.json`
2. Plasează-l în directorul root al proiectului MagFlow:
   ```
   /Users/macos/anaconda3/envs/MagFlow/service_account.json
   ```

3. Verifică că fișierul conține:
   ```json
   {
     "type": "service_account",
     "project_id": "your-project-id",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...",
     "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
     "client_id": "...",
     "auth_uri": "https://accounts.google.com/o/oauth2/auth",
     "token_uri": "https://oauth2.googleapis.com/token",
     ...
   }
   ```

### 3. Partajare Google Sheets

1. Deschide Google Sheets-ul tău ("eMAG Stock")
2. Click pe butonul "Share"
3. Adaugă email-ul service account-ului (din `client_email` din JSON)
4. Acordă permisiuni de **Viewer** (citire)

## 📊 Structura Google Sheets

### Foaia "Products"

Coloanele necesare:

| Coloană | Descriere | Obligatoriu |
|---------|-----------|-------------|
| `SKU` | Codul SKU al produsului | ✅ Da |
| `Romanian_Name` | Numele produsului în română | ✅ Da |
| `Emag_FBE_RO_Price_RON` | Prețul produsului în RON | ❌ Nu |

**Exemplu:**

| SKU | Romanian_Name | Emag_FBE_RO_Price_RON |
|-----|---------------|----------------------|
| EMG140 | Modul amplificator audio stereo 2x15W cu TA2024 | 45.50 |
| CCA736 | Emulator de programare CC Debugger CC2530 | 32.00 |
| ADS206 | Placa dezvoltare ADS1015, 16 Bit, I2C | 28.90 |

### Configurare în Cod

Dacă ai nume diferite pentru spreadsheet sau foi, modifică în `app/services/google_sheets_service.py`:

```python
class GoogleSheetsConfig(BaseModel):
    sheet_name: str = "eMAG Stock"  # Numele spreadsheet-ului
    products_sheet_tab: str = "Products"  # Numele foii cu produse
    suppliers_sheet_tab: str = "Product_Suppliers"  # Opțional
```

## 🚀 Instalare Dependențe

```bash
# Instalează dependențele Python
pip install -r requirements.txt

# Sau instalează manual
pip install gspread>=5.12.0 oauth2client>=4.1.3
```

## 💾 Migrare Bază de Date

```bash
# Rulează migrarea pentru a crea tabelele necesare
cd /Users/macos/anaconda3/envs/MagFlow
alembic upgrade head
```

Aceasta va crea:
- Tabelul `app.product_mappings` - pentru mapări produse
- Tabelul `app.import_logs` - pentru istoric importuri

## 🖥️ Utilizare

### 1. Pornire Backend

```bash
./start_dev.sh backend
# sau
uvicorn app.main:app --reload --port 8000
```

### 2. Pornire Frontend

```bash
cd admin-frontend
npm run dev
```

### 3. Accesare Interfață Import

1. Deschide browser: http://localhost:5173
2. Login: `admin@example.com` / `secret`
3. Navighează la: **Products** > **Import from Google Sheets**
   - URL: http://localhost:5173/products/import

### 4. Import Produse

#### Pas 1: Test Conexiune
- Click pe butonul "Test Again" pentru a verifica conexiunea la Google Sheets
- Ar trebui să vezi mesajul "Google Sheets Connected"

#### Pas 2: Import
- Click pe "Import from Google Sheets"
- Confirmă în dialog
- Așteaptă finalizarea importului

#### Pas 3: Verificare Rezultate
- Vezi statisticile în dashboard:
  - **Total Products**: Număr total produse importate
  - **Fully Mapped**: Produse mapate la ambele conturi (MAIN și FBE)
  - **Partially Mapped**: Produse mapate doar la un cont
  - **Unmapped**: Produse nemapate

### 5. Mapare Manuală

Pentru produse care nu au fost mapate automat:

1. Filtrează după status: "Unmapped"
2. Click pe butonul "Map" pentru produsul dorit
3. Completează ID-urile produselor din eMAG:
   - **eMAG MAIN Product ID**: ID-ul din tabelul `emag_products_v2` pentru contul MAIN
   - **eMAG FBE Product ID**: ID-ul din tabelul `emag_products_v2` pentru contul FBE
4. Adaugă note (opțional)
5. Salvează

## 📡 API Endpoints

### Test Conexiune
```bash
GET /api/v1/products/sheets/test-connection
```

### Import Produse
```bash
POST /api/v1/products/import/google-sheets
Content-Type: application/json

{
  "auto_map": true
}
```

### Statistici Mapări
```bash
GET /api/v1/products/mappings/statistics
```

### Listă Mapări
```bash
GET /api/v1/products/mappings?filter_status=unmapped&limit=100
```

### Mapare Manuală
```bash
POST /api/v1/products/mappings/manual
Content-Type: application/json

{
  "local_sku": "EMG140",
  "emag_main_id": 123,
  "emag_fbe_id": 456,
  "notes": "Mapare manuală verificată"
}
```

### Istoric Importuri
```bash
GET /api/v1/products/import/history?limit=10
```

## 🔍 Cum Funcționează Maparea Automată

1. **Import din Google Sheets**:
   - Se citesc toate produsele din foaia "Products"
   - Se creează înregistrări în `product_mappings`

2. **Mapare Automată pe SKU**:
   - Pentru fiecare produs importat, se caută în `emag_products_v2`:
     - Produse cu `part_number` = SKU și `account_type` = "main"
     - Produse cu `part_number` = SKU și `account_type` = "fbe"
   
3. **Statusuri Mapare**:
   - **mapped**: Produsul a fost găsit și mapat
   - **not_found**: Nu s-a găsit produs cu acest SKU
   - **conflict**: Există multiple produse cu același SKU

4. **Confidence Score**:
   - `1.0` pentru mapare exactă pe SKU
   - Poate fi extins pentru mapare fuzzy pe nume

## 🗄️ Structura Bazei de Date

### Tabelul `product_mappings`

```sql
CREATE TABLE app.product_mappings (
    id SERIAL PRIMARY KEY,
    local_sku VARCHAR(100) UNIQUE NOT NULL,
    local_product_name VARCHAR(500) NOT NULL,
    local_price FLOAT,
    
    -- MAIN account
    emag_main_id INTEGER,
    emag_main_part_number VARCHAR(100),
    emag_main_status VARCHAR(50),
    
    -- FBE account
    emag_fbe_id INTEGER,
    emag_fbe_part_number VARCHAR(100),
    emag_fbe_status VARCHAR(50),
    
    -- Metadata
    mapping_confidence FLOAT,
    mapping_method VARCHAR(50),
    is_verified BOOLEAN DEFAULT FALSE,
    google_sheet_row INTEGER,
    google_sheet_data TEXT,
    last_imported_at TIMESTAMP,
    import_source VARCHAR(100),
    notes TEXT,
    has_conflicts BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabelul `import_logs`

```sql
CREATE TABLE app.import_logs (
    id SERIAL PRIMARY KEY,
    import_type VARCHAR(50) NOT NULL,
    source_name VARCHAR(200) NOT NULL,
    total_rows INTEGER DEFAULT 0,
    successful_imports INTEGER DEFAULT 0,
    failed_imports INTEGER DEFAULT 0,
    auto_mapped_main INTEGER DEFAULT 0,
    auto_mapped_fbe INTEGER DEFAULT 0,
    unmapped_products INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    status VARCHAR(50) DEFAULT 'in_progress',
    error_message TEXT,
    initiated_by VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🐛 Troubleshooting

### Eroare: "Failed to authenticate with Google Sheets API"

**Cauze posibile:**
- Fișierul `service_account.json` lipsește sau este invalid
- Permisiuni insuficiente pentru service account

**Soluții:**
1. Verifică că fișierul există în root-ul proiectului
2. Verifică că JSON-ul este valid
3. Regenerează cheia din Google Cloud Console

### Eroare: "Failed to open spreadsheet"

**Cauze posibile:**
- Spreadsheet-ul nu este partajat cu service account
- Numele spreadsheet-ului este greșit

**Soluții:**
1. Partajează spreadsheet-ul cu email-ul din `client_email`
2. Verifică numele în `GoogleSheetsConfig`

### Produse Nemapate Automat

**Cauze posibile:**
- SKU-ul din Google Sheets nu se potrivește cu cel din eMAG
- Produsele nu au fost sincronizate din eMAG

**Soluții:**
1. Verifică SKU-urile în ambele surse
2. Rulează sincronizarea eMAG: http://localhost:5173/emag
3. Folosește maparea manuală

### Eroare: "column does not exist"

**Cauză:**
- Migrarea bazei de date nu a fost rulată

**Soluție:**
```bash
alembic upgrade head
```

## 📈 Best Practices

1. **Backup înainte de import**:
   ```bash
   pg_dump -h localhost -p 5433 -U magflow_user magflow_db > backup.sql
   ```

2. **Test pe date limitate**:
   - Începe cu 10-20 produse pentru test
   - Verifică mapările
   - Apoi importă toate produsele

3. **Verificare regulată**:
   - Rulează importul periodic (zilnic/săptămânal)
   - Monitorizează produsele nemapate
   - Actualizează mapările manuale

4. **Sincronizare eMAG**:
   - Rulează sincronizarea eMAG înainte de import
   - Asigură-te că ai produsele actualizate în baza de date

## 🔐 Securitate

- ✅ Fișierul `service_account.json` este în `.gitignore`
- ✅ Nu partaja niciodată cheia service account
- ✅ Acordă doar permisiuni de citire pentru Google Sheets
- ✅ Rotează cheile periodic (la 90 zile)

## 📞 Suport

Pentru probleme sau întrebări:
1. Verifică logs-urile backend: `docker logs magflow-backend`
2. Verifică console-ul browser pentru erori frontend
3. Consultă documentația API: http://localhost:8000/docs

## 🎉 Succes!

Acum ai un sistem complet de import și mapare produse din Google Sheets către eMAG!
