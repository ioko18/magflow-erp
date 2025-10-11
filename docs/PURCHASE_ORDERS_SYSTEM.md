# Purchase Orders System - Documentație Completă

## Prezentare Generală

Sistemul de Purchase Orders (PO) oferă o soluție centralizată pentru gestionarea comenzilor către furnizori, cu tracking complet al statusului, integrare cu inventarul și gestionarea produselor nerecepționate.

## Funcționalități Principale

### 1. **Gestionare Comenzi Furnizori**
- ✅ Creare comenzi cu linii multiple de produse
- ✅ Tracking status: `draft`, `sent`, `confirmed`, `partially_received`, `received`, `cancelled`
- ✅ Calcul automat al totalurilor și taxelor
- ✅ Suport pentru multiple valute
- ✅ Adrese de livrare și numere de tracking

### 2. **Integrare cu Stocul Existent**
- ✅ Afișare cantități comandate în așteptare în lista "Low Stock"
- ✅ Calcul automat: `adjusted_reorder_quantity` = `reorder_quantity` - `total_pending_quantity`
- ✅ Indicator vizual pentru produse cu comenzi active
- ✅ Detalii complete pentru fiecare comandă în așteptare

### 3. **Istoric Comenzi Furnizori**
- ✅ Tracking complet al tuturor modificărilor de status
- ✅ Audit trail cu user ID și timestamp
- ✅ Metadata JSON pentru informații suplimentare
- ✅ Vizualizare cronologică a evenimentelor

### 4. **Gestionare Produse Nereceptionate**
- ✅ Tracking automat al discrepanțelor între comandă și recepție
- ✅ Status: `pending`, `partial`, `resolved`, `cancelled`
- ✅ Follow-up dates pentru urmărire
- ✅ Rezolvare cu notițe detaliate

## Structura Bazei de Date

### Tabele Principale

#### `purchase_orders`
```sql
- id: INTEGER (PK)
- order_number: VARCHAR(50) UNIQUE
- supplier_id: INTEGER (FK -> suppliers.id)
- order_date: DATETIME
- expected_delivery_date: DATETIME
- actual_delivery_date: DATETIME
- status: VARCHAR(20) -- draft, sent, confirmed, partially_received, received, cancelled
- total_amount: NUMERIC(10,2)
- tax_amount: NUMERIC(10,2)
- discount_amount: NUMERIC(10,2)
- shipping_cost: NUMERIC(10,2)
- currency: VARCHAR(3)
- payment_terms: VARCHAR(100)
- notes: TEXT
- delivery_address: TEXT
- tracking_number: VARCHAR(100)
- cancelled_at: DATETIME
- cancelled_by: INTEGER
- cancellation_reason: TEXT
- created_by: INTEGER
- approved_by: INTEGER
- created_at: DATETIME
- updated_at: DATETIME
```

#### `purchase_order_lines`
```sql
- id: INTEGER (PK)
- purchase_order_id: INTEGER (FK -> purchase_orders.id)
- product_id: INTEGER (FK -> products.id)
- supplier_product_id: INTEGER (FK -> supplier_products_purchase.id)
- quantity: INTEGER
- unit_cost: NUMERIC(10,2)
- discount_percent: NUMERIC(5,2)
- tax_percent: NUMERIC(5,2)
- line_total: NUMERIC(10,2)
- received_quantity: INTEGER
- notes: VARCHAR(255)
- created_at: DATETIME
- updated_at: DATETIME
```

#### `purchase_order_unreceived_items`
```sql
- id: INTEGER (PK)
- purchase_order_id: INTEGER (FK -> purchase_orders.id)
- purchase_order_line_id: INTEGER (FK -> purchase_order_lines.id)
- product_id: INTEGER (FK -> products.id)
- ordered_quantity: INTEGER
- received_quantity: INTEGER
- unreceived_quantity: INTEGER
- expected_date: DATETIME
- follow_up_date: DATETIME
- status: VARCHAR(20) -- pending, partial, resolved, cancelled
- notes: TEXT
- resolution_notes: TEXT
- resolved_at: DATETIME
- resolved_by: INTEGER
- created_at: DATETIME
- updated_at: DATETIME
```

#### `purchase_order_history`
```sql
- id: INTEGER (PK)
- purchase_order_id: INTEGER (FK -> purchase_orders.id)
- action: VARCHAR(50)
- old_status: VARCHAR(20)
- new_status: VARCHAR(20)
- notes: TEXT
- changed_by: INTEGER
- changed_at: DATETIME
- metadata: JSONB
```

## API Endpoints

### Purchase Orders Management

#### 1. **List Purchase Orders**
```http
GET /api/v1/purchase-orders
```

**Query Parameters:**
- `skip`: int (default: 0) - Pagination offset
- `limit`: int (default: 100) - Results per page
- `status`: string - Filter by status
- `supplier_id`: int - Filter by supplier
- `search`: string - Search in order number, notes, supplier name

**Response:**
```json
{
  "status": "success",
  "data": {
    "orders": [
      {
        "id": 1,
        "order_number": "PO-20251011-0001",
        "supplier": {
          "id": 5,
          "name": "Supplier Name"
        },
        "order_date": "2025-10-11T10:00:00",
        "expected_delivery_date": "2025-10-25T10:00:00",
        "status": "sent",
        "total_amount": 5000.00,
        "currency": "RON",
        "total_items": 5,
        "total_ordered_quantity": 100,
        "total_received_quantity": 0,
        "is_fully_received": false,
        "is_partially_received": false
      }
    ],
    "pagination": {
      "total": 50,
      "skip": 0,
      "limit": 100,
      "has_more": false
    }
  }
}
```

#### 2. **Create Purchase Order**
```http
POST /api/v1/purchase-orders
```

**Request Body:**
```json
{
  "supplier_id": 5,
  "order_date": "2025-10-11T10:00:00",
  "expected_delivery_date": "2025-10-25T10:00:00",
  "currency": "RON",
  "payment_terms": "30 days",
  "notes": "Urgent order",
  "delivery_address": "Warehouse A, Street 123",
  "lines": [
    {
      "product_id": 100,
      "quantity": 50,
      "unit_cost": 25.50,
      "notes": "Red color"
    },
    {
      "product_id": 101,
      "quantity": 30,
      "unit_cost": 15.00
    }
  ]
}
```

**Response:**
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

#### 3. **Get Purchase Order Details**
```http
GET /api/v1/purchase-orders/{po_id}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "order_number": "PO-20251011-0001",
    "supplier": {
      "id": 5,
      "name": "Supplier Name",
      "email": "supplier@example.com",
      "phone": "+40123456789"
    },
    "order_date": "2025-10-11T10:00:00",
    "expected_delivery_date": "2025-10-25T10:00:00",
    "status": "sent",
    "total_amount": 1650.00,
    "currency": "RON",
    "lines": [
      {
        "id": 1,
        "product": {
          "id": 100,
          "name": "Product Name",
          "sku": "SKU-001",
          "image_url": "https://..."
        },
        "quantity": 50,
        "received_quantity": 0,
        "pending_quantity": 50,
        "unit_cost": 25.50,
        "line_total": 1275.00
      }
    ],
    "unreceived_items": [],
    "total_ordered_quantity": 80,
    "total_received_quantity": 0,
    "is_fully_received": false,
    "is_partially_received": false
  }
}
```

#### 4. **Update Purchase Order Status**
```http
PATCH /api/v1/purchase-orders/{po_id}/status
```

**Request Body:**
```json
{
  "status": "sent",
  "notes": "Order sent to supplier via email",
  "metadata": {
    "email_sent_at": "2025-10-11T10:30:00",
    "tracking_number": "TRACK123"
  }
}
```

#### 5. **Receive Purchase Order**
```http
POST /api/v1/purchase-orders/{po_id}/receive
```

**Request Body:**
```json
{
  "receipt_date": "2025-10-20T14:00:00",
  "supplier_invoice_number": "INV-2025-001",
  "supplier_invoice_date": "2025-10-20T00:00:00",
  "notes": "Partial delivery",
  "lines": [
    {
      "purchase_order_line_id": 1,
      "received_quantity": 45
    },
    {
      "purchase_order_line_id": 2,
      "received_quantity": 30
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "receipt_id": 1,
    "receipt_number": "RCP-20251020-0001",
    "total_received_quantity": 75,
    "message": "Receipt recorded successfully"
  }
}
```

#### 6. **Get Purchase Order History**
```http
GET /api/v1/purchase-orders/{po_id}/history
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "history": [
      {
        "id": 3,
        "action": "status_changed_to_sent",
        "old_status": "draft",
        "new_status": "sent",
        "notes": "Order sent to supplier",
        "changed_by": 1,
        "changed_at": "2025-10-11T10:30:00",
        "metadata": {"email_sent": true}
      },
      {
        "id": 1,
        "action": "created",
        "old_status": null,
        "new_status": "draft",
        "notes": "Purchase order created",
        "changed_by": 1,
        "changed_at": "2025-10-11T10:00:00"
      }
    ]
  }
}
```

### Unreceived Items Management

#### 7. **List Unreceived Items**
```http
GET /api/v1/purchase-orders/unreceived-items/list
```

**Query Parameters:**
- `status`: string - Filter by status (pending, partial, resolved, cancelled)
- `supplier_id`: int - Filter by supplier
- `skip`: int - Pagination offset
- `limit`: int - Results per page

**Response:**
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "purchase_order": {
          "id": 1,
          "order_number": "PO-20251011-0001"
        },
        "supplier": {
          "id": 5,
          "name": "Supplier Name"
        },
        "product": {
          "id": 100,
          "name": "Product Name",
          "sku": "SKU-001"
        },
        "ordered_quantity": 50,
        "received_quantity": 45,
        "unreceived_quantity": 5,
        "status": "partial",
        "notes": "Missing 5 units",
        "expected_date": "2025-10-25T00:00:00"
      }
    ],
    "pagination": {
      "total": 10,
      "skip": 0,
      "limit": 100,
      "has_more": false
    }
  }
}
```

#### 8. **Resolve Unreceived Item**
```http
PATCH /api/v1/purchase-orders/unreceived-items/{item_id}/resolve
```

**Request Body:**
```json
{
  "resolution_notes": "Supplier sent replacement shipment"
}
```

### Product Pending Orders

#### 9. **Get Pending Orders for Product**
```http
GET /api/v1/purchase-orders/products/{product_id}/pending-orders
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "product_id": 100,
    "pending_orders": [
      {
        "purchase_order_id": 1,
        "order_number": "PO-20251011-0001",
        "supplier_id": 5,
        "supplier_name": "Supplier Name",
        "ordered_quantity": 50,
        "received_quantity": 0,
        "pending_quantity": 50,
        "expected_delivery_date": "2025-10-25T00:00:00",
        "order_date": "2025-10-11T10:00:00",
        "status": "sent"
      }
    ],
    "total_pending_quantity": 50
  }
}
```

### Supplier Statistics

#### 10. **Get Supplier Order Statistics**
```http
GET /api/v1/purchase-orders/statistics/by-supplier/{supplier_id}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_orders": 25,
    "orders_by_status": {
      "draft": 2,
      "sent": 5,
      "confirmed": 3,
      "partially_received": 2,
      "received": 10,
      "cancelled": 3
    },
    "total_amount": 125000.00,
    "active_orders": 10
  }
}
```

## Integrare cu Low Stock

Endpoint-ul `/api/v1/inventory/low-stock-with-suppliers` a fost îmbunătățit cu următoarele câmpuri noi:

```json
{
  "product_id": 100,
  "name": "Product Name",
  "reorder_quantity": 100,
  "adjusted_reorder_quantity": 50,  // NEW: reorder_quantity - total_pending_quantity
  "pending_orders": [  // NEW: Lista comenzilor în așteptare
    {
      "purchase_order_id": 1,
      "order_number": "PO-20251011-0001",
      "ordered_quantity": 50,
      "received_quantity": 0,
      "pending_quantity": 50,
      "expected_delivery_date": "2025-10-25T00:00:00",
      "status": "sent"
    }
  ],
  "total_pending_quantity": 50,  // NEW: Total cantitate comandată
  "has_pending_orders": true  // NEW: Indicator vizual
}
```

**Summary Statistics:**
```json
{
  "summary": {
    "total_low_stock": 150,
    "products_with_pending_orders": 45,  // NEW
    "total_pending_quantity": 2500  // NEW
  }
}
```

## Flux de Lucru Recomandat

### 1. **Creare Comandă**
1. Utilizatorul selectează produse din lista "Low Stock"
2. Selectează furnizorul pentru fiecare produs
3. Sistemul creează PO cu status `draft`
4. Utilizatorul revizuiește și aprobă comanda

### 2. **Trimitere Comandă**
1. Utilizatorul marchează comanda ca `sent`
2. Sistemul înregistrează în istoric
3. Email/notificare către furnizor (opțional)

### 3. **Confirmare Comandă**
1. Furnizorul confirmă comanda
2. Status actualizat la `confirmed`
3. Data estimată de livrare actualizată

### 4. **Recepție Produse**
1. Produsele sosesc la depozit
2. Utilizatorul înregistrează recepția
3. Cantități actualizate automat
4. Status: `partially_received` sau `received`
5. Produse nerecepționate înregistrate automat

### 5. **Gestionare Produse Lipsă**
1. Sistem identifică automat discrepanțe
2. Creare înregistrare în `unreceived_items`
3. Follow-up cu furnizorul
4. Rezolvare și închidere

## Migrare Bază de Date

Pentru a aplica noile tabele, rulează:

```bash
# Verifică migrările disponibile
alembic current

# Aplică migrarea
alembic upgrade head

# Verifică că migrarea a fost aplicată
alembic current
```

## Testare

### 1. **Test Creare PO**
```bash
curl -X POST http://localhost:8000/api/v1/purchase-orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "supplier_id": 1,
    "lines": [
      {"product_id": 1, "quantity": 10, "unit_cost": 25.50}
    ]
  }'
```

### 2. **Test Low Stock cu PO**
```bash
curl http://localhost:8000/api/v1/inventory/low-stock-with-suppliers \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Recomandări Frontend

### Componente Necesare

1. **PurchaseOrderList** - Listă comenzi cu filtrare și căutare
2. **PurchaseOrderForm** - Formular creare/editare comandă
3. **PurchaseOrderDetails** - Detalii comandă cu istoric
4. **ReceiveOrderModal** - Modal pentru înregistrare recepție
5. **UnreceivedItemsList** - Listă produse nerecepționate
6. **LowStockEnhanced** - Low Stock cu indicatori PO

### Indicatori Vizuali Recomandați

- 🟢 **Verde**: Comandă confirmată, în termen
- 🟡 **Galben**: Comandă parțial recepționată
- 🔴 **Roșu**: Comandă întârziată
- ⏳ **Ceas**: Comandă în așteptare
- ✅ **Check**: Comandă finalizată

### Badge-uri pentru Low Stock

```jsx
{has_pending_orders && (
  <Badge color="blue">
    {total_pending_quantity} în comandă
  </Badge>
)}
```

## Securitate

- ✅ Toate endpoint-urile necesită autentificare
- ✅ User ID înregistrat pentru toate acțiunile
- ✅ Audit trail complet
- ✅ Validare date la nivel de API
- ✅ Protecție împotriva SQL injection

## Performance

- ✅ Indexuri pe coloanele frecvent căutate
- ✅ Paginare pentru toate listele
- ✅ Eager loading pentru relații
- ✅ Caching pentru statistici (recomandat)

## Limitări Cunoscute

1. Nu există suport pentru comenzi multi-valută în același PO
2. Tracking AWB este manual (nu există integrare cu curieri)
3. Nu există notificări automate către furnizori
4. Calculul costurilor nu include taxe vamale

## Dezvoltări Viitoare

- [ ] Integrare email pentru trimitere automată comenzi
- [ ] Notificări push pentru statusuri importante
- [ ] Dashboard analitic pentru performanța furnizorilor
- [ ] Predicție stoc bazată pe istoric comenzi
- [ ] Export PDF pentru comenzi
- [ ] Integrare cu sisteme contabilitate
- [ ] API webhook pentru actualizări status de la furnizori

## Suport

Pentru întrebări sau probleme:
- Verifică logs: `/var/log/magflow/`
- Contactează echipa de dezvoltare
- Documentație API: `/api/v1/docs`
