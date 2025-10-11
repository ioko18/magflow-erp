# Purchase Orders - Pași Manuali pentru Deployment

## 🎯 Status Curent

✅ **Backend:** Complet implementat și verificat  
✅ **Cod:** Curat, fără erori de linting  
⚠️ **Deployment:** Necesită pași manuali din cauza configurației Docker

---

## 🐳 Situația Actuală

**PostgreSQL rulează în Docker:**
- Container: `magflow_db`
- Port: `5433` (mapare externă)
- Status: ✅ Running și Healthy

**Problema:**
- Alembic încearcă să se conecteze la hostname `db` (intern Docker)
- Trebuie să rulezi migrarea din interiorul containerului sau să modifici temporar configurația

---

## 🚀 Opțiuni de Deployment

### **Opțiunea 1: Rulare Migrare în Docker (RECOMANDAT)**

Aceasta este cea mai simplă metodă și nu necesită modificări de configurație.

```bash
cd /Users/macos/anaconda3/envs/MagFlow

# 1. Verifică că toate containerele rulează
docker-compose ps

# 2. Rulează migrarea în containerul app
docker-compose exec app alembic upgrade head

# Sau dacă containerul app nu rulează:
docker-compose run --rm app alembic upgrade head
```

**Verificare:**
```bash
# Verifică versiunea curentă
docker-compose exec app alembic current

# Ar trebui să vezi:
# 20251011_enhanced_po (head)
```

---

### **Opțiunea 2: Rulare Migrare Local (cu modificare temporară)**

Dacă preferi să rulezi local, trebuie să modifici temporar configurația.

#### **Pas 2.1: Backup .env**
```bash
cp .env .env.backup
```

#### **Pas 2.2: Modifică .env temporar**
```bash
# Editează .env și schimbă:
DB_HOST=db          # Schimbă în: localhost
DB_PORT=5432        # Schimbă în: 5433
```

Sau cu sed:
```bash
sed -i.bak 's/DB_HOST=db/DB_HOST=localhost/' .env
sed -i.bak 's/DB_PORT=5432/DB_PORT=5433/' .env
```

#### **Pas 2.3: Rulează Migrarea**
```bash
alembic upgrade head
```

#### **Pas 2.4: Restaurează .env**
```bash
mv .env.backup .env
# Sau:
git checkout .env
```

---

### **Opțiunea 3: Verificare Manuală în PostgreSQL**

Dacă vrei să verifici că totul este OK înainte de migrare:

```bash
# Conectează-te la PostgreSQL
docker exec -it magflow_db psql -U app -d magflow

# În psql, verifică tabelele existente:
\dt app.purchase*

# Ar trebui să vezi:
# app.purchase_orders
# app.purchase_order_lines
# app.purchase_receipts
# app.purchase_receipt_lines

# Ieși din psql:
\q
```

---

## 📋 Checklist Deployment

### **Înainte de Migrare**
- [ ] PostgreSQL container rulează (`docker ps | grep postgres`)
- [ ] Backup bază de date (opțional dar recomandat)
  ```bash
  docker exec magflow_db pg_dump -U app magflow > backup_before_po_migration.sql
  ```

### **Rulare Migrare**
- [ ] Alege opțiunea 1 sau 2 de mai sus
- [ ] Rulează `alembic upgrade head`
- [ ] Verifică că migrarea a reușit:
  ```bash
  docker-compose exec app alembic current
  # Output: 20251011_enhanced_po (head)
  ```

### **Verificare Post-Migrare**
- [ ] Verifică că tabelele noi există:
  ```bash
  docker exec -it magflow_db psql -U app -d magflow -c "\dt app.purchase_order*"
  ```
  
  Ar trebui să vezi:
  - `app.purchase_orders` (existent, cu coloane noi)
  - `app.purchase_order_lines` (existent)
  - `app.purchase_order_unreceived_items` (NOU)
  - `app.purchase_order_history` (NOU)

- [ ] Verifică coloanele noi în `purchase_orders`:
  ```bash
  docker exec -it magflow_db psql -U app -d magflow -c "\d app.purchase_orders"
  ```
  
  Ar trebui să vezi coloanele noi:
  - `delivery_address`
  - `tracking_number`
  - `actual_delivery_date`
  - `cancelled_at`
  - `cancelled_by`
  - `cancellation_reason`

---

## 🖥️ Pornire Server

### **Opțiunea A: Docker (RECOMANDAT)**

```bash
# Pornește toate serviciile
docker-compose up -d

# Verifică logs
docker-compose logs -f app

# Testează
curl http://localhost:8000/api/v1/health/
```

### **Opțiunea B: Local**

```bash
# Modifică .env pentru localhost (vezi Opțiunea 2 mai sus)
# Apoi:
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧪 Testare în Swagger UI

### **1. Deschide Swagger UI**
```bash
open http://localhost:8000/api/v1/docs
```

### **2. Autentificare**
- Click pe "Authorize" (butonul cu lacăt)
- Introdu token-ul JWT
- Click "Authorize"

### **3. Testează Endpoint-urile Purchase Orders**

#### **Test 1: Listă Comenzi**
```
GET /api/v1/purchase-orders
```
- Click "Try it out"
- Click "Execute"
- Verifică response (ar trebui să fie listă goală inițial)

#### **Test 2: Listă Low Stock cu PO**
```
GET /api/v1/inventory/low-stock-with-suppliers
```
- Verifică că response-ul conține câmpurile noi:
  - `pending_orders`
  - `total_pending_quantity`
  - `adjusted_reorder_quantity`
  - `has_pending_orders`

#### **Test 3: Creare Comandă (dacă ai date de test)**
```
POST /api/v1/purchase-orders
```
Body:
```json
{
  "supplier_id": 1,
  "lines": [
    {
      "product_id": 1,
      "quantity": 50,
      "unit_cost": 25.50
    }
  ]
}
```

---

## 🎨 Implementare Frontend

### **Prioritizare Implementare**

#### **Săptămâna 1 - Esențial (MVP)**
1. **PurchaseOrderList** - Listă comenzi
   - Filtrare după status, furnizor
   - Paginare
   - Sortare
   
2. **PurchaseOrderForm** - Formular creare
   - Selectare furnizor
   - Adăugare linii produse
   - Calcul automat totaluri

3. **LowStockWithPO** - Integrare Low Stock
   - Badge pentru produse cu comenzi
   - Tooltip cu detalii comenzi
   - Indicator `adjusted_reorder_quantity`

#### **Săptămâna 2 - Important**
4. **PurchaseOrderDetails** - Detalii comandă
   - Afișare informații complete
   - Istoric modificări
   - Acțiuni (update status, receive)

5. **ReceiveOrderModal** - Recepție produse
   - Input cantități recepționate
   - Validare
   - Tracking automat produse lipsă

6. **PurchaseOrderStatusBadge** - Indicatori vizuali
   - Culori pentru fiecare status
   - Iconițe
   - Tooltips

#### **Săptămâna 3 - Nice to Have**
7. **UnreceivedItemsList** - Produse lipsă
8. **PurchaseOrderHistory** - Istoric detaliat
9. **Dashboard** - Statistici și rapoarte

### **Resurse Disponibile**

📗 **Ghid Complet Frontend:**
```
docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md
```

Conține:
- ✅ TypeScript types complete
- ✅ API client gata de folosit
- ✅ Componente React cu cod complet
- ✅ Exemple practice
- ✅ Best practices
- ✅ Testing

### **Quick Start Frontend**

```bash
cd admin-frontend

# 1. Creează fișierele TypeScript types
# Copiază din docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md
# Secțiunea "1. TypeScript Types"

# 2. Creează API client
# Copiază din docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md
# Secțiunea "2. API Client"

# 3. Creează prima componentă
# Începe cu PurchaseOrderList
# Cod complet în ghid

# 4. Adaugă routing
# Vezi secțiunea "4. Routing" din ghid

# 5. Testează
npm run dev
```

---

## 🐛 Troubleshooting

### **Eroare: Cannot connect to database**

**Cauză:** Configurația .env folosește hostname Docker `db`

**Soluție:**
- Opțiunea 1: Rulează migrarea în Docker (recomandat)
- Opțiunea 2: Modifică temporar .env pentru localhost:5433

### **Eroare: Migration already exists**

**Verificare:**
```bash
docker-compose exec app alembic current
```

**Dacă migrarea e deja aplicată:**
- Nu face nimic, totul e OK!

**Dacă nu e aplicată:**
```bash
docker-compose exec app alembic upgrade head
```

### **Eroare: Table already exists**

**Cauză:** Migrarea a fost rulată parțial

**Soluție:**
```bash
# Rollback
docker-compose exec app alembic downgrade -1

# Re-aplică
docker-compose exec app alembic upgrade head
```

### **Server nu pornește**

**Verificare:**
```bash
docker-compose logs app
```

**Cauze comune:**
- Port 8000 deja folosit
- Erori în cod (verifică logs)
- Probleme de conectare la DB

---

## ✅ Checklist Final

### **Backend**
- [ ] PostgreSQL container rulează
- [ ] Migrare aplicată cu succes
- [ ] Tabele noi create
- [ ] Server pornit
- [ ] Swagger UI accesibil
- [ ] Endpoint-uri PO funcționează
- [ ] Integrare Low Stock funcționează

### **Frontend**
- [ ] Types TypeScript create
- [ ] API client implementat
- [ ] Componente esențiale create
- [ ] Routing configurat
- [ ] Testare UI completă

---

## 📞 Comenzi Utile

### **Docker**
```bash
# Status containere
docker-compose ps

# Logs
docker-compose logs -f app

# Restart
docker-compose restart app

# Shell în container
docker-compose exec app bash
```

### **Database**
```bash
# Conectare PostgreSQL
docker exec -it magflow_db psql -U app -d magflow

# Backup
docker exec magflow_db pg_dump -U app magflow > backup.sql

# Restore
docker exec -i magflow_db psql -U app -d magflow < backup.sql
```

### **Alembic**
```bash
# În Docker
docker-compose exec app alembic current
docker-compose exec app alembic upgrade head
docker-compose exec app alembic history

# Local (după modificare .env)
alembic current
alembic upgrade head
alembic history
```

---

## 🎉 Succes!

După ce ai urmat acești pași, vei avea:

✅ **Backend funcțional** - Toate endpoint-urile PO disponibile  
✅ **Integrare Low Stock** - Cantități comandate vizibile  
✅ **Bază de date** - Tabele noi create  
✅ **API documentat** - Swagger UI funcțional  
✅ **Gata pentru frontend** - Toate API-urile pregătite

**Următorul pas:** Implementează componentele frontend folosind ghidul din `docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md`

---

**Data:** 11 Octombrie 2025  
**Versiune:** 1.0.1  
**Status:** 📋 Ghid Manual Deployment
