# 🚀 Purchase Orders - Instrucțiuni Finale de Deployment

## ⚠️ Situație Actuală

**Problemă Identificată:** Există 2 branch-uri separate de migrări Alembic:
- `20251011_enhanced_po` (Purchase Orders - NOU)
- `97aa49837ac6` (Product Relationships - existent)

**Soluție:** Trebuie să creăm o migrare de merge pentru a uni cele două branch-uri.

---

## 🔧 Soluție Rapidă - Merge Migrations

### Opțiunea 1: Merge Automat (RECOMANDAT)

```bash
cd /Users/macos/anaconda3/envs/MagFlow

# Creează migrare de merge
docker-compose exec app alembic merge -m "merge purchase orders and product relationships" heads

# Rulează migrarea
docker-compose exec app alembic upgrade head

# Verifică
docker-compose exec app alembic current
```

**Output așteptat după merge:**
```
Generating /app/alembic/versions/xxxxx_merge_purchase_orders_and_product_relationships.py ... done
```

**Output așteptat după upgrade:**
```
INFO  [alembic.runtime.migration] Running upgrade 20251011_enhanced_po, 97aa49837ac6 -> xxxxx, merge purchase orders and product relationships
```

---

### Opțiunea 2: Merge Manual

Dacă opțiunea 1 nu funcționează, creează manual fișierul de merge:

```bash
# 1. Creează fișierul de merge
cat > alembic/versions/$(date +%Y%m%d%H%M%S)_merge_heads.py << 'EOF'
"""Merge heads: purchase orders and product relationships

Revision ID: merge_po_pr_20251011
Revises: 20251011_enhanced_po, 97aa49837ac6
Create Date: 2025-10-11 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_po_pr_20251011'
down_revision = ('20251011_enhanced_po', '97aa49837ac6')
branch_labels = None
depends_on = None

def upgrade():
    """Merge migrations - no changes needed."""
    pass

def downgrade():
    """Downgrade - no changes needed."""
    pass
EOF

# 2. Rulează migrarea
docker-compose exec app alembic upgrade head
```

---

## ✅ Verificare Post-Migrare

### 1. Verifică Versiunea Curentă
```bash
docker-compose exec app alembic current
```

**Output așteptat:**
```
merge_po_pr_20251011 (head)
```

### 2. Verifică Tabelele Noi
```bash
docker exec -it magflow_db psql -U app -d magflow -c "\dt app.purchase_order*"
```

**Output așteptat:**
```
                        List of relations
 Schema |              Name                | Type  | Owner
--------+----------------------------------+-------+-------
 app    | purchase_orders                  | table | app
 app    | purchase_order_lines             | table | app
 app    | purchase_order_unreceived_items  | table | app    <- NOU
 app    | purchase_order_history           | table | app    <- NOU
```

### 3. Verifică Coloanele Noi
```bash
docker exec -it magflow_db psql -U app -d magflow -c "\d app.purchase_orders" | grep -E "(delivery_address|tracking_number|cancelled)"
```

**Output așteptat:**
```
 delivery_address       | text                        |           |          |
 tracking_number        | character varying(100)      |           |          |
 actual_delivery_date   | timestamp without time zone |           |          |
 cancelled_at           | timestamp without time zone |           |          |
 cancelled_by           | integer                     |           |          |
 cancellation_reason    | text                        |           |          |
```

---

## 🖥️ Pornire/Restart Server

### Serverul Rulează Deja!

Containerul `magflow_app` este deja pornit și healthy. Nu trebuie să faci nimic!

```bash
# Verificare status
docker-compose ps app

# Output:
# NAME          IMAGE         COMMAND    SERVICE   CREATED     STATUS
# magflow_app   magflow-app   ...        app       3 hours ago Up 3 hours (healthy)
```

### Dacă Vrei să Restartezi (Opțional)

```bash
# Restart pentru a încărca noile modele
docker-compose restart app

# Verifică logs
docker-compose logs -f app
```

---

## 🧪 Testare în Swagger UI

### 1. Deschide Swagger UI

```bash
open http://localhost:8000/api/v1/docs
```

Sau accesează manual: `http://localhost:8000/api/v1/docs`

### 2. Autentificare

**Obține Token JWT:**

Dacă nu ai un token, creează unul:

```bash
# Opțiunea A: Prin API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Opțiunea B: Prin Swagger UI
# 1. Scroll la /api/v1/auth/login
# 2. Click "Try it out"
# 3. Introdu credentials
# 4. Click "Execute"
# 5. Copiază token-ul din response
```

**Autentifică-te în Swagger:**
1. Click pe butonul "Authorize" (🔒 sus-dreapta)
2. Introdu: `Bearer YOUR_TOKEN_HERE`
3. Click "Authorize"
4. Click "Close"

### 3. Testează Endpoint-urile Purchase Orders

#### Test 1: Listă Comenzi (ar trebui să fie goală inițial)
```
GET /api/v1/purchase-orders
```
1. Găsește endpoint-ul în listă
2. Click "Try it out"
3. Click "Execute"
4. Verifică Response Code: `200`
5. Verifică Response Body:
```json
{
  "status": "success",
  "data": {
    "orders": [],
    "pagination": {
      "total": 0,
      "skip": 0,
      "limit": 100,
      "has_more": false
    }
  }
}
```

#### Test 2: Low Stock cu Purchase Orders
```
GET /api/v1/inventory/low-stock-with-suppliers
```
1. Găsește endpoint-ul
2. Click "Try it out"
3. Click "Execute"
4. Verifică că response-ul conține câmpurile noi:

```json
{
  "status": "success",
  "data": {
    "products": [
      {
        "product_id": 1,
        "name": "Product Name",
        "reorder_quantity": 100,
        "adjusted_reorder_quantity": 100,     // NOU ✅
        "pending_orders": [],                  // NOU ✅
        "total_pending_quantity": 0,           // NOU ✅
        "has_pending_orders": false,           // NOU ✅
        "suppliers": [...]
      }
    ],
    "summary": {
      "products_with_pending_orders": 0,      // NOU ✅
      "total_pending_quantity": 0             // NOU ✅
    }
  }
}
```

#### Test 3: Creare Comandă (Opțional - dacă ai date de test)

**Verifică mai întâi că ai un furnizor și produse:**
```bash
# Verifică furnizori
docker exec -it magflow_db psql -U app -d magflow -c "SELECT id, name FROM app.suppliers LIMIT 5;"

# Verifică produse
docker exec -it magflow_db psql -U app -d magflow -c "SELECT id, name, sku FROM app.products LIMIT 5;"
```

**Apoi creează o comandă de test:**
```
POST /api/v1/purchase-orders
```

Request Body:
```json
{
  "supplier_id": 1,
  "order_date": "2025-10-11T21:00:00",
  "expected_delivery_date": "2025-10-25T10:00:00",
  "currency": "RON",
  "notes": "Test order from Swagger UI",
  "lines": [
    {
      "product_id": 1,
      "quantity": 50,
      "unit_cost": 25.50
    }
  ]
}
```

**Response așteptat:**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "order_number": "PO-20251011-0001",
    "message": "Purchase order created successfully"
  }
}
```

---

## 🎨 Implementare Frontend

### Pregătire

Toate resursele necesare sunt în:
```
docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md
```

### Quick Start

```bash
cd admin-frontend

# 1. Creează directorul pentru types
mkdir -p src/types

# 2. Creează fișierul purchaseOrder.ts
# Copiază conținutul din docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md
# Secțiunea "1. TypeScript Types"

# 3. Creează directorul pentru API
mkdir -p src/api

# 4. Creează fișierul purchaseOrders.ts
# Copiază conținutul din docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md
# Secțiunea "2. API Client"

# 5. Creează directorul pentru componente
mkdir -p src/components/purchase-orders

# 6. Începe cu prima componentă: PurchaseOrderList
# Cod complet în docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md
# Secțiunea "3.2 PurchaseOrderList"
```

### Prioritizare Implementare

**Săptămâna 1 - MVP (Minimum Viable Product):**
1. ✅ `PurchaseOrderList.tsx` - Listă comenzi
2. ✅ `PurchaseOrderStatusBadge.tsx` - Badge-uri status
3. ✅ `LowStockWithPO.tsx` - Integrare Low Stock

**Săptămâna 2 - Core Features:**
4. ✅ `PurchaseOrderForm.tsx` - Formular creare
5. ✅ `PurchaseOrderDetails.tsx` - Detalii comandă
6. ✅ `ReceiveOrderModal.tsx` - Modal recepție

**Săptămâna 3 - Advanced Features:**
7. ✅ `UnreceivedItemsList.tsx` - Produse lipsă
8. ✅ `PurchaseOrderHistory.tsx` - Istoric
9. ✅ Dashboard și statistici

---

## 📊 Verificare Completă

### Checklist Final

#### Backend ✅
- [x] PostgreSQL container rulează
- [ ] Migrare merge creată
- [ ] Migrare aplicată cu succes
- [ ] Tabele noi verificate
- [x] Server pornit (deja rulează)
- [ ] Swagger UI accesibil
- [ ] Endpoint-uri PO funcționează
- [ ] Integrare Low Stock funcționează

#### Frontend ⏳
- [ ] Types TypeScript create
- [ ] API client implementat
- [ ] Componente esențiale create
- [ ] Routing configurat
- [ ] Testare UI completă

---

## 🐛 Troubleshooting

### Eroare: "Multiple head revisions"
**Cauză:** Două branch-uri separate de migrări

**Soluție:** Urmează Opțiunea 1 sau 2 de mai sus pentru merge

### Eroare: "Table already exists"
**Cauză:** Migrarea a fost rulată parțial

**Soluție:**
```bash
# Verifică ce tabele există
docker exec -it magflow_db psql -U app -d magflow -c "\dt app.purchase_order*"

# Dacă tabelele noi există deja, marchează migrarea ca aplicată
docker-compose exec app alembic stamp head
```

### Server nu răspunde
**Verificare:**
```bash
docker-compose ps app
docker-compose logs app | tail -50
```

**Restart:**
```bash
docker-compose restart app
```

---

## 📞 Comenzi Utile

### Alembic
```bash
# Heads
docker-compose exec app alembic heads

# Current
docker-compose exec app alembic current

# History
docker-compose exec app alembic history

# Upgrade
docker-compose exec app alembic upgrade head

# Downgrade
docker-compose exec app alembic downgrade -1
```

### Database
```bash
# Conectare
docker exec -it magflow_db psql -U app -d magflow

# Verificare tabele
docker exec -it magflow_db psql -U app -d magflow -c "\dt app.purchase*"

# Backup
docker exec magflow_db pg_dump -U app magflow > backup_$(date +%Y%m%d).sql
```

### Docker
```bash
# Status
docker-compose ps

# Logs
docker-compose logs -f app

# Restart
docker-compose restart app

# Rebuild (dacă ai modificat cod)
docker-compose up -d --build app
```

---

## 🎉 Success!

După ce ai urmat acești pași, vei avea:

✅ **Migrare aplicată** - Tabele noi create în DB  
✅ **Server funcțional** - Toate endpoint-urile disponibile  
✅ **API testat** - Verificat în Swagger UI  
✅ **Gata pentru frontend** - Toate resursele pregătite

**Următorul pas:** Implementează frontend-ul folosind ghidul complet din `docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md`

---

**Data:** 11 Octombrie 2025, 21:00 UTC+03:00  
**Status:** 📋 Instrucțiuni Finale  
**Acțiune Necesară:** Merge migrations + Test în Swagger UI
