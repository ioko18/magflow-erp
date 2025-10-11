# 🔍 Purchase Orders - Analiză Completă și Plan de Remediere

## 📊 Situația Actuală Descoperită

### Problema Principală
Există **DOUĂ sisteme de Purchase Orders**:

1. **Sistemul EXISTENT în DB** (vechi):
   - Tabel: `purchase_orders` (18 coloane)
   - Tabel: `purchase_order_items` (14 coloane)
   - Structură diferită de modelele noastre

2. **Sistemul NOU implementat** (codul nostru):
   - Model: `PurchaseOrder` (așteaptă alte coloane)
   - Model: `PurchaseOrderLine` (așteaptă tabel `purchase_order_lines`)
   - Modele noi: `PurchaseOrderUnreceivedItem`, `PurchaseOrderHistory`

### Discrepanțe Identificate

#### Tabela `purchase_orders`

**În DB (existent):**
```sql
- id, order_number, supplier_id, status
- order_date, expected_delivery_date, actual_delivery_date
- total_value (double precision)
- currency, exchange_rate
- order_items (JSON)
- supplier_confirmation, internal_notes, attachments (JSON)
- quality_check_passed, quality_notes
- created_at, updated_at
```

**În Model (nostru):**
```python
- id, order_number, supplier_id, status
- order_date, expected_delivery_date, actual_delivery_date
- total_amount (Numeric 10,2)  # ≠ total_value
- tax_amount, discount_amount, shipping_cost
- currency, payment_terms, notes
- delivery_address, tracking_number
- cancelled_at, cancelled_by, cancellation_reason
- created_by, approved_by
- created_at, updated_at
```

#### Tabela Items/Lines

**În DB:**
- Nume: `purchase_order_items`
- Coloane: quantity_ordered, quantity_received, unit_price, total_price, etc.

**În Model:**
- Nume: `purchase_order_lines`
- Coloane: quantity, received_quantity, unit_cost, line_total, etc.

---

## 🎯 Opțiuni de Remediere

### Opțiunea 1: Adaptare la Structura Existentă (RECOMANDAT)

**Avantaje:**
- ✅ Nu distruge date existente
- ✅ Compatibil cu sistemul vechi
- ✅ Migrare mai simplă

**Dezavantaje:**
- ⚠️ Trebuie să modificăm modelele noastre
- ⚠️ Trebuie să adaptăm serviciile și API-urile

**Pași:**
1. Modifică modelele pentru a se potrivi cu structura DB
2. Adaugă doar coloanele noi care lipsesc
3. Creează doar tabelele noi (unreceived_items, history)
4. Adaptează serviciile pentru noua structură

### Opțiunea 2: Migrare Completă (COMPLEX)

**Avantaje:**
- ✅ Structură nouă, mai bună
- ✅ Conform cu design-ul nostru

**Dezavantaje:**
- ❌ Risc mare de pierdere date
- ❌ Necesită migrare date existente
- ❌ Timp de implementare mare

### Opțiunea 3: Sistem Paralel (NU RECOMANDAT)

**Avantaje:**
- ✅ Nu afectează sistemul vechi

**Dezavantaje:**
- ❌ Confuzie între sisteme
- ❌ Duplicare cod
- ❌ Probleme de integritate

---

## ✅ Soluția Recomandată: Opțiunea 1

### Pas 1: Modificare Modele

#### 1.1 Actualizare `PurchaseOrder`

```python
class PurchaseOrder(Base, TimestampMixin):
    """Purchase order model - adapted to existing schema."""
    
    __tablename__ = "purchase_orders"
    __table_args__ = {"schema": "app", "extend_existing": True}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("app.suppliers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    
    # Dates
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Financial - ADAPT TO EXISTING
    total_value: Mapped[float] = mapped_column(Float, nullable=False)  # NOT total_amount
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RON")
    exchange_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    
    # Existing fields
    order_items: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supplier_confirmation: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quality_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # NEW FIELDS TO ADD
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships - ADAPT TO EXISTING TABLE NAME
    order_items_rel: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        foreign_keys="[PurchaseOrderItem.purchase_order_id]"
    )
```

#### 1.2 Renumire `PurchaseOrderLine` → `PurchaseOrderItem`

```python
class PurchaseOrderItem(Base, TimestampMixin):
    """Purchase order item model - adapted to existing schema."""
    
    __tablename__ = "purchase_order_items"
    __table_args__ = {"schema": "app", "extend_existing": True}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(Integer, ForeignKey("app.purchase_orders.id"), nullable=False)
    supplier_product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("app.supplier_products.id"), nullable=True)
    local_product_id: Mapped[int] = mapped_column(Integer, ForeignKey("app.products.id"), nullable=False)
    
    # Quantities - ADAPT TO EXISTING NAMES
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    
    # Prices - ADAPT TO EXISTING NAMES
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Dates
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Quality
    quality_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="order_items_rel"
    )
```

### Pas 2: Migrare pentru Coloane Noi

```python
def upgrade():
    """Add only NEW columns and tables."""
    
    # Add NEW columns to existing purchase_orders table
    op.add_column('purchase_orders', 
        sa.Column('delivery_address', sa.Text(), nullable=True),
        schema='app'
    )
    op.add_column('purchase_orders', 
        sa.Column('tracking_number', sa.String(100), nullable=True),
        schema='app'
    )
    op.add_column('purchase_orders', 
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        schema='app'
    )
    op.add_column('purchase_orders', 
        sa.Column('cancelled_by', sa.Integer(), nullable=True),
        schema='app'
    )
    op.add_column('purchase_orders', 
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        schema='app'
    )
    
    # Create NEW tables
    op.create_table(
        'purchase_order_unreceived_items',
        # ... (folosește purchase_order_items_id în loc de purchase_order_lines_id)
    )
    
    op.create_table(
        'purchase_order_history',
        # ... (la fel)
    )
```

### Pas 3: Adaptare Servicii

Modifică `PurchaseOrderService` pentru a folosi:
- `total_value` în loc de `total_amount`
- `quantity_ordered` în loc de `quantity`
- `quantity_received` în loc de `received_quantity`
- `unit_price` în loc de `unit_cost`
- `order_items_rel` pentru relații

### Pas 4: Adaptare API

Modifică endpoint-urile pentru a returna:
- `total_value` (dar poate fi aliased ca `total_amount` în response)
- Mapare corectă a câmpurilor

---

## 📋 Plan de Implementare Pas cu Pas

### Faza 1: Backup și Pregătire
- [ ] Backup bază de date
- [ ] Documentare structură existentă
- [ ] Creare branch Git pentru modificări

### Faza 2: Modificare Modele
- [ ] Actualizare `PurchaseOrder` model
- [ ] Renumire `PurchaseOrderLine` → `PurchaseOrderItem`
- [ ] Actualizare `PurchaseOrderUnreceivedItem` (foreign keys)
- [ ] Actualizare `PurchaseOrderHistory`
- [ ] Test import modele

### Faza 3: Actualizare Migrare
- [ ] Modificare migrare pentru a adăuga doar coloane noi
- [ ] Creare tabele noi cu foreign keys corecte
- [ ] Test migrare pe DB de dev

### Faza 4: Adaptare Servicii
- [ ] Modificare `PurchaseOrderService`
- [ ] Adaptare metode pentru noile nume de câmpuri
- [ ] Test servicii

### Faza 5: Adaptare API
- [ ] Modificare endpoint-uri
- [ ] Mapare response-uri
- [ ] Test API în Swagger

### Faza 6: Testare Completă
- [ ] Test creare comandă
- [ ] Test recepție
- [ ] Test integrare Low Stock
- [ ] Test produse nerecepționate

---

## ⏱️ Estimare Timp

- **Faza 1:** 15 minute
- **Faza 2:** 45 minute
- **Faza 3:** 30 minute
- **Faza 4:** 60 minute
- **Faza 5:** 45 minute
- **Faza 6:** 60 minute

**Total:** ~4 ore

---

## 🎯 Decizie Necesară

**Întrebare pentru tine:**

Vrei să:

**A)** Adaptăm sistemul nostru la structura existentă? (Recomandat, ~4 ore)
- Păstrăm datele existente
- Compatibilitate cu sistemul vechi
- Risc minim

**B)** Creăm un sistem complet nou cu tabele noi? (~6-8 ore)
- Tabele: `purchase_orders_v2`, `purchase_order_lines_v2`
- Sistem independent
- Risc mediu

**C)** Facem migrare completă a datelor? (~8-10 ore)
- Transformăm structura veche în cea nouă
- Risc ridicat
- Necesită testare extensivă

---

## 💡 Recomandarea Mea

**Opțiunea A** - Adaptare la structura existentă

**Motivație:**
1. Cel mai rapid și mai sigur
2. Nu pierdem date existente
3. Compatibil cu cod existent
4. Putem implementa imediat

**Următorul Pas:**
Dacă ești de acord cu Opțiunea A, încep imediat implementarea pas cu pas.

---

**Data:** 11 Octombrie 2025, 21:30 UTC+03:00  
**Status:** 🔍 Analiză Completă | ⏳ Așteptare Decizie
