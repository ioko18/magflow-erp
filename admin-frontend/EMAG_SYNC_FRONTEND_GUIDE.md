# eMAG Product Sync - Frontend Guide

## 📱 Pagini Disponibile

### 1. **EmagProductSync** (Original - `/emag`)
Pagina originală de sincronizare, folosește endpoint-urile vechi `/emag/enhanced/`.

**Caracteristici:**
- Sincronizare bazică MAIN + FBE
- Monitorizare progres
- Tabel produse
- Istoric sincronizări

### 2. **EmagProductSyncV2** (Nou - `/emag/sync-v2`) ⭐
Pagină complet refăcută care integrează noul sistem de sincronizare.

**Caracteristici Noi:**
- ✅ **Test Conexiune API** - Verificare conexiune pentru fiecare cont
- ✅ **Moduri de Sincronizare**:
  - Full - Sincronizare completă
  - Incremental - Doar produse modificate (recomandat)
  - Selective - Cu filtre specifice
- ✅ **Strategii Rezolvare Conflicte**:
  - eMAG Priority (recomandat)
  - Local Priority
  - Newest Wins
  - Manual Resolution
- ✅ **Opțiuni Avansate**:
  - Selectare conturi (MAIN, FBE, Both)
  - Configurare max pages
  - Items per page
  - Include/exclude inactive products
  - Async/Sync execution
- ✅ **Statistici Detaliate**:
  - Total produse per cont
  - Status sincronizare în timp real
  - Istoric complet cu detalii
- ✅ **UI/UX Îmbunătățit**:
  - Design modern și intuitiv
  - Feedback vizual clar
  - Notificări informative
  - Progress tracking în timp real

## 🚀 Cum să Folosești Noua Pagină

### Pas 1: Accesare
Navigați la: `http://localhost:5173/emag/sync-v2`

### Pas 2: Test Conexiune
1. Click pe **"Test Connection"** pentru contul MAIN
2. Click pe **"Test Connection"** pentru contul FBE
3. Verificați că ambele conexiuni sunt OK (✓ Connected)

### Pas 3: Configurare Sincronizare
1. Click pe **"Sync Options"**
2. Selectați:
   - **Account Type**: Both (pentru ambele conturi)
   - **Sync Mode**: Incremental (recomandat pentru uz zilnic)
   - **Conflict Strategy**: eMAG Priority (recomandat)
   - **Max Pages**: 10 (pentru test rapid) sau null (pentru tot)
   - **Run in Background**: ON (recomandat)
3. Click **"OK"** pentru a salva

### Pas 4: Start Sincronizare
1. Click pe butonul mare **"Start Incremental Sync - BOTH"**
2. Monitorizați progresul în card-ul "Sync in Progress"
3. Așteptați finalizarea (veți primi notificare)

### Pas 5: Verificare Rezultate
1. Tab **"Synced Products"**: Vezi produsele sincronizate
2. Tab **"Sync History"**: Vezi istoricul sincronizărilor
3. Folosiți filtrele pentru căutare și sortare

## 📊 Interfață Utilizator

### Header
- **Title**: eMAG Product Sync V2
- **Auto-refresh Toggle**: ON/OFF pentru refresh automat statistici
- **Sync Options Button**: Configurare opțiuni sincronizare
- **Refresh Button**: Refresh manual date

### Statistics Cards (4 carduri)
1. **Total Products**: Total produse sincronizate
2. **MAIN Account**: Produse din contul MAIN
3. **FBE Account**: Produse din contul FBE
4. **Sync Status**: Status curent (Syncing/Idle) + ultima sincronizare

### Connection Tests Card
- Test conexiune pentru fiecare cont
- Indicatori vizuali: ✓ Connected / ✗ Failed
- Alert informativ

### Current Sync Card (vizibil doar în timpul sincronizării)
- Progress bar animat
- Statistici în timp real:
  - Operation type
  - Processed items / Total items
  - Start time
- Auto-refresh la 3 secunde

### Sync Controls Card (vizibil când nu rulează sincronizare)
- Buton mare pentru start sincronizare
- Alert cu configurația curentă:
  - Mode
  - Accounts
  - Max Pages
  - Conflict Strategy
  - Execution type

### Tabs
#### Tab 1: Synced Products
- **Filtre**:
  - Search by name or SKU
  - Filter by Account (MAIN/FBE)
- **Actions**:
  - Export CSV
- **Tabel**:
  - SKU (copyable)
  - Actions (view details)
  - Product Name
  - Account (tag colorat)
  - Price
  - Stock (tag colorat)
  - Status (Active/Inactive)
  - Sync Status
  - Last Synced
- **Paginare**:
  - 10, 20, 50, 100 items per page
  - Total count
  - Navigation

#### Tab 2: Sync History
- Timeline cu toate sincronizările
- Pentru fiecare sync:
  - Account type (tag colorat)
  - Status (tag colorat)
  - Timestamp
  - Operation
  - Statistics: Total, Created, Updated, Failed
  - Duration

### Modals

#### Sync Options Modal
- **Account Type**: Radio buttons (Both/MAIN/FBE)
- **Sync Mode**: Radio buttons cu iconițe
  - Incremental (⚡)
  - Full (💾)
  - Selective (💡)
- **Conflict Strategy**: Dropdown
- **Max Pages**: Number input
- **Items per Page**: Number input (10-100)
- **Include Inactive**: Switch
- **Run in Background**: Switch
- **Info Alerts**: Descrieri pentru fiecare opțiune

#### Product Details Drawer
- Informații complete despre produs:
  - ID (copyable)
  - eMAG ID
  - SKU (copyable)
  - Name
  - Account
  - Price
  - Stock
  - Status
  - Sync Status
  - Timestamps (Last Synced, Created, Updated)

## 🎨 Design & UX

### Culori
- **MAIN Account**: Albastru (#1890ff)
- **FBE Account**: Verde (#722ed1)
- **Success**: Verde (#52c41a)
- **Error**: Roșu (#ff4d4f)
- **Warning**: Portocaliu (#faad14)
- **Processing**: Albastru (#1890ff)

### Iconițe
- 🌐 CloudSyncOutlined - Sync general
- 🔄 SyncOutlined - Sync în progres
- ✓ CheckCircleOutlined - Success
- ✗ CloseCircleOutlined - Error
- 🚀 RocketOutlined - Start sync
- ⚙️ SettingOutlined - Opțiuni
- 💾 DatabaseOutlined - Database
- 🔌 ApiOutlined - API
- 📡 WifiOutlined - Conexiune
- 🔒 SafetyOutlined - Securitate
- 💡 BulbOutlined - Selective
- ⚡ ThunderboltOutlined - Incremental
- 🕐 HistoryOutlined - Istoric

### Notificări
- **Success**: Verde, 3-5 secunde
- **Error**: Roșu, 5 secunde sau persistent
- **Info**: Albastru, 3 secunde
- **Warning**: Portocaliu, 5 secunde

## 🔧 Configurare Recomandată

### Pentru Uz Zilnic
```javascript
{
  account_type: 'both',
  mode: 'incremental',
  max_pages: null,  // toate paginile
  items_per_page: 100,
  include_inactive: false,
  conflict_strategy: 'emag_priority',
  run_async: true
}
```

### Pentru Test Rapid
```javascript
{
  account_type: 'main',
  mode: 'incremental',
  max_pages: 2,  // doar 2 pagini
  items_per_page: 100,
  include_inactive: false,
  conflict_strategy: 'emag_priority',
  run_async: false
}
```

### Pentru Sincronizare Completă Inițială
```javascript
{
  account_type: 'both',
  mode: 'full',
  max_pages: null,  // toate
  items_per_page: 100,
  include_inactive: true,
  conflict_strategy: 'emag_priority',
  run_async: true
}
```

## 📡 API Endpoints Folosite

### Noi (V2)
- `GET /api/v1/emag/products/statistics` - Statistici
- `GET /api/v1/emag/products/status` - Status sincronizare
- `GET /api/v1/emag/products/products` - Lista produse
- `POST /api/v1/emag/products/sync` - Start sincronizare
- `POST /api/v1/emag/products/test-connection` - Test conexiune

### Vechi (Original)
- `GET /api/v1/emag/enhanced/status` - Status
- `GET /api/v1/emag/enhanced/products/sync-progress` - Progres
- `GET /api/v1/emag/enhanced/products/all` - Produse
- `POST /api/v1/emag/enhanced/sync/all-products` - Sync
- `POST /api/v1/emag/enhanced/sync/stop` - Stop sync

## 🐛 Troubleshooting

### Problema: "Failed to connect to eMAG API"
**Soluție:**
1. Verificați credențialele în `.env`
2. Verificați IP whitelist în eMAG seller portal
3. Testați conexiunea manual

### Problema: "Sync hangs at 0%"
**Soluție:**
1. Verificați logs backend
2. Verificați că Celery worker rulează
3. Refresh pagina și reîncercați

### Problema: "Products not showing"
**Soluție:**
1. Verificați filtrele active
2. Refresh tab-ul Products
3. Verificați că sincronizarea s-a finalizat cu succes

### Problema: "Rate limit exceeded"
**Soluție:**
1. Reduceți `max_pages`
2. Creșteți delay între requests în backend
3. Așteptați câteva minute și reîncercați

## 🔄 Auto-Refresh

### Statistics
- **Interval**: 30 secunde
- **Condiție**: Auto-refresh ON
- **Date**: Total products, products by account

### Sync Status
- **Interval**: 3 secunde
- **Condiție**: Sync în progres
- **Date**: Current sync progress, recent syncs

## 📱 Responsive Design

Pagina este complet responsive:
- **Desktop** (>1200px): Layout complet cu toate coloanele
- **Tablet** (768-1200px): Layout adaptat, 2 coloane
- **Mobile** (<768px): Layout vertical, 1 coloană

## 🎯 Best Practices

1. **Testați conexiunea** înainte de fiecare sincronizare
2. **Folosiți Incremental mode** pentru sincronizări regulate
3. **Activați Auto-refresh** pentru monitoring în timp real
4. **Rulați în background** (async) pentru sincronizări mari
5. **Verificați istoricul** pentru a identifica probleme
6. **Exportați CSV** periodic pentru backup
7. **Monitorizați statisticile** pentru a detecta anomalii

## 🚀 Următorii Pași

Pentru îmbunătățiri viitoare:
- [ ] Grafice și charts pentru statistici
- [ ] Filtrare avansată în tabel
- [ ] Bulk actions pe produse
- [ ] Notificări push pentru sincronizări
- [ ] Export în multiple formate (Excel, JSON)
- [ ] Comparare între MAIN și FBE
- [ ] Conflict resolution UI pentru manual mode

---

**Versiune**: 2.0.0  
**Data**: 2025-10-01  
**Status**: Production Ready ✅
