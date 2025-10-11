# 🚀 Purchase Orders Frontend - Pași Concreți de Implementare

## 📋 Rezumat Executiv

**Backend Status:** ✅ 100% Complet și Funcțional  
**Frontend Status:** ⏳ 0% - Gata de implementare  
**Timp Estimat:** 5-8 zile (34-46 ore)  
**Documentație:** ✅ Completă în `docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md`

---

## 🎯 Ziua 1: Setup și MVP (6-8 ore)

### Dimineața (3-4 ore)

#### Pas 1.1: Setup Structură (15 min)
```bash
cd admin-frontend/src

# Creează directoare
mkdir -p components/purchase-orders
mkdir -p api
mkdir -p types

# Verifică
ls -la components/purchase-orders
ls -la api
ls -la types
```

#### Pas 1.2: TypeScript Types (30 min)
```bash
# Creează fișierul
touch src/types/purchaseOrder.ts
```

**Copiază conținutul din:**
`docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md` - Secțiunea "1. TypeScript Types" (liniile 28-150)

**Verificare:**
```bash
# Testează import
echo "import { PurchaseOrder } from './types/purchaseOrder';" | npx tsc --noEmit
```

#### Pas 1.3: API Client (1 oră)
```bash
# Creează fișierul
touch src/api/purchaseOrders.ts
```

**Copiază conținutul din:**
`docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md` - Secțiunea "2. API Client" (liniile 152-300)

**Modifică:**
- Actualizează `API_BASE` cu URL-ul corect
- Adaugă axios interceptors pentru autentificare

**Testare:**
```typescript
// Test în browser console
import { purchaseOrdersApi } from './api/purchaseOrders';
purchaseOrdersApi.list().then(console.log);
```

#### Pas 1.4: PurchaseOrderStatusBadge (1 oră)
```bash
touch src/components/purchase-orders/PurchaseOrderStatusBadge.tsx
```

**Copiază conținutul din:**
`docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md` - Secțiunea "3.1 PurchaseOrderStatusBadge"

**Customizează:**
- Culori conform design system
- Iconițe (Lucide React sau similar)

### După-amiaza (3-4 ore)

#### Pas 1.5: PurchaseOrderList (4 ore)
```bash
touch src/components/purchase-orders/PurchaseOrderList.tsx
```

**Copiază conținutul din:**
`docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md` - Secțiunea "3.2 PurchaseOrderList"

**Implementează:**
- Tabel cu comenzi
- Filtrare (status, furnizor, date)
- Paginare
- Sortare
- Acțiuni (view, edit, delete)

**Testare:**
```bash
npm run dev
# Accesează /purchase-orders
```

#### Pas 1.6: Routing (30 min)
```typescript
// În App.tsx sau router
import PurchaseOrderList from './components/purchase-orders/PurchaseOrderList';

// Adaugă route
<Route path="/purchase-orders" element={<PurchaseOrderList />} />
```

**Adaugă în meniu:**
```typescript
{
  label: 'Purchase Orders',
  icon: ShoppingCart,
  path: '/purchase-orders'
}
```

### **Checkpoint Ziua 1:**
- ✅ Types create
- ✅ API client funcțional
- ✅ Badge component
- ✅ Listă comenzi funcțională
- ✅ Routing configurat

---

## 🎯 Ziua 2: Integrare Low Stock (4-6 ore)

### Pas 2.1: LowStockWithPO Component (4 ore)
```bash
touch src/components/inventory/LowStockWithPO.tsx
```

**Obiectiv:** Îmbunătățește componenta Low Stock existentă

**Modificări necesare:**

1. **Update API call:**
```typescript
// Folosește endpoint-ul îmbunătățit
const response = await axios.get('/api/v1/inventory/low-stock-with-suppliers');
```

2. **Adaugă câmpuri noi în interface:**
```typescript
interface LowStockProduct {
  // ... câmpuri existente
  pending_orders?: PendingOrder[];
  total_pending_quantity?: number;
  adjusted_reorder_quantity?: number;
  has_pending_orders?: boolean;
}
```

3. **Afișare indicator vizual:**
```typescript
{product.has_pending_orders && (
  <Badge color="blue">
    {product.total_pending_quantity} în comandă
  </Badge>
)}
```

4. **Tooltip cu detalii comenzi:**
```typescript
<Tooltip>
  <TooltipTrigger>
    <InfoIcon />
  </TooltipTrigger>
  <TooltipContent>
    {product.pending_orders?.map(order => (
      <div key={order.order_number}>
        {order.order_number}: {order.pending_quantity} buc
      </div>
    ))}
  </TooltipContent>
</Tooltip>
```

5. **Calcul cantitate ajustată:**
```typescript
const quantityToOrder = product.adjusted_reorder_quantity || product.reorder_quantity;
```

### Pas 2.2: Testare Integrare (1 oră)
```bash
# Test scenarii:
# 1. Produs fără comenzi - afișare normală
# 2. Produs cu comenzi - afișare badge și tooltip
# 3. Calcul corect adjusted_reorder_quantity
```

### **Checkpoint Ziua 2:**
- ✅ Low Stock îmbunătățit
- ✅ Indicator vizual comenzi
- ✅ Tooltip detalii
- ✅ Calcul cantitate ajustată

---

## 🎯 Ziua 3-4: Core Features (12-16 ore)

### Ziua 3: Formular Creare (6-8 ore)

#### Pas 3.1: PurchaseOrderForm (6-8 ore)
```bash
touch src/components/purchase-orders/PurchaseOrderForm.tsx
```

**Copiază conținutul din:**
`docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md` - Secțiunea "3.3 PurchaseOrderForm"

**Implementează:**

1. **Selectare furnizor** (1 oră)
```typescript
<Select
  options={suppliers}
  onChange={setSelectedSupplier}
  placeholder="Selectează furnizor"
/>
```

2. **Adăugare linii produse** (2 ore)
```typescript
const [lines, setLines] = useState<PurchaseOrderLine[]>([]);

const addLine = () => {
  setLines([...lines, {
    product_id: 0,
    quantity: 1,
    unit_cost: 0
  }]);
};
```

3. **Calcul automat totaluri** (1 oră)
```typescript
const calculateTotal = () => {
  return lines.reduce((sum, line) => {
    return sum + (line.quantity * line.unit_cost);
  }, 0);
};
```

4. **Validare** (1 oră)
```typescript
const validate = () => {
  if (!selectedSupplier) return 'Selectează furnizor';
  if (lines.length === 0) return 'Adaugă cel puțin un produs';
  // ... alte validări
};
```

5. **Submit** (1 oră)
```typescript
const handleSubmit = async () => {
  const data = {
    supplier_id: selectedSupplier.id,
    order_date: new Date().toISOString(),
    lines: lines
  };
  await purchaseOrdersApi.create(data);
  navigate('/purchase-orders');
};
```

### Ziua 4: Detalii și Recepție (6-8 ore)

#### Pas 4.1: PurchaseOrderDetails (4-6 ore)
```bash
touch src/components/purchase-orders/PurchaseOrderDetails.tsx
```

**Copiază conținutul din:**
`docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md` - Secțiunea "3.4 PurchaseOrderDetails"

**Implementează:**
1. Afișare informații comandă
2. Tabel cu linii produse
3. Istoric modificări
4. Acțiuni (update status, receive)

#### Pas 4.2: ReceiveOrderModal (3-4 ore)
```bash
touch src/components/purchase-orders/ReceiveOrderModal.tsx
```

**Implementează:**
1. Modal cu formular recepție
2. Input cantități recepționate per produs
3. Validare (cantitate <= cantitate comandată)
4. Submit și tracking automat discrepanțe

### **Checkpoint Ziua 3-4:**
- ✅ Formular creare funcțional
- ✅ Detalii comandă complete
- ✅ Modal recepție funcțional
- ✅ Tracking automat discrepanțe

---

## 🎯 Ziua 5-6: Advanced Features (8-12 ore)

### Ziua 5: Produse Nerecepționate (4-6 ore)

#### Pas 5.1: UnreceivedItemsList (4-6 ore)
```bash
touch src/components/purchase-orders/UnreceivedItemsList.tsx
```

**Implementează:**
1. Tabel cu produse lipsă
2. Filtrare (status, furnizor)
3. Sortare
4. Acțiuni (rezolvare, follow-up)
5. Modal rezolvare

### Ziua 6: Istoric și Statistici (4-6 ore)

#### Pas 6.1: PurchaseOrderHistory (2-3 ore)
```bash
touch src/components/purchase-orders/PurchaseOrderHistory.tsx
```

**Implementează:**
1. Timeline evenimente
2. Filtrare
3. Export

#### Pas 6.2: Dashboard/Statistici (2-3 ore)
```bash
touch src/components/purchase-orders/PurchaseOrderDashboard.tsx
```

**Implementează:**
1. Statistici per furnizor
2. Grafice (Chart.js sau Recharts)
3. KPIs (comenzi active, valoare totală, etc.)

### **Checkpoint Ziua 5-6:**
- ✅ Listă produse lipsă
- ✅ Istoric modificări
- ✅ Dashboard statistici

---

## 🎯 Ziua 7-8: Testing și Polish (6-8 ore)

### Ziua 7: Testing (4 ore)

#### Pas 7.1: Unit Tests
```bash
# Test componente
npm run test

# Test API client
npm run test:api
```

#### Pas 7.2: Integration Tests
```bash
# Test flow complet:
# 1. Creare comandă
# 2. Update status
# 3. Recepție
# 4. Verificare produse lipsă
```

#### Pas 7.3: E2E Tests (opțional)
```bash
# Playwright sau Cypress
npm run test:e2e
```

### Ziua 8: Polish și Documentation (2-4 ore)

#### Pas 8.1: UI/UX Improvements
- Animații
- Loading states
- Error handling
- Success messages
- Responsive design

#### Pas 8.2: Code Review
- Refactoring
- Performance optimization
- Accessibility (a11y)

#### Pas 8.3: Documentation
```markdown
# Creează README.md pentru componente
# Documentează API usage
# Adaugă comentarii în cod
```

### **Checkpoint Final:**
- ✅ Toate componentele testate
- ✅ Bug-uri rezolvate
- ✅ UI/UX polish
- ✅ Documentație completă
- ✅ Code review done
- ✅ Gata pentru deploy

---

## 📊 Checklist Complet

### Setup (Ziua 1 - Dimineață)
- [ ] Creat structură directoare
- [ ] Creat `types/purchaseOrder.ts`
- [ ] Creat `api/purchaseOrders.ts`
- [ ] Testat API client
- [ ] Creat `PurchaseOrderStatusBadge`

### MVP (Ziua 1 - După-amiază)
- [ ] Creat `PurchaseOrderList`
- [ ] Adăugat routing
- [ ] Adăugat în meniu
- [ ] Testat listă comenzi

### Integrare (Ziua 2)
- [ ] Actualizat `LowStockWithPO`
- [ ] Adăugat indicator vizual
- [ ] Adăugat tooltip detalii
- [ ] Testat integrare

### Core Features (Ziua 3-4)
- [ ] Creat `PurchaseOrderForm`
- [ ] Creat `PurchaseOrderDetails`
- [ ] Creat `ReceiveOrderModal`
- [ ] Testat flow complet

### Advanced (Ziua 5-6)
- [ ] Creat `UnreceivedItemsList`
- [ ] Creat `PurchaseOrderHistory`
- [ ] Creat Dashboard/Statistici
- [ ] Testat funcționalități avansate

### Finalizare (Ziua 7-8)
- [ ] Unit tests
- [ ] Integration tests
- [ ] UI/UX polish
- [ ] Code review
- [ ] Documentation
- [ ] Deploy

---

## 🔧 Comenzi Utile

### Development
```bash
# Start dev server
npm run dev

# Type check
npm run type-check

# Lint
npm run lint

# Format
npm run format
```

### Testing
```bash
# Run tests
npm run test

# Test coverage
npm run test:coverage

# E2E tests
npm run test:e2e
```

### Build
```bash
# Build production
npm run build

# Preview build
npm run preview
```

---

## 📞 Resurse

### Documentație
- **Backend API:** `docs/PURCHASE_ORDERS_SYSTEM.md`
- **Frontend Guide:** `docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md`
- **Analiză:** `PURCHASE_ORDERS_IMPLEMENTATION_ANALYSIS.md`

### API
- **Swagger UI:** http://localhost:8000/docs
- **Base URL:** http://localhost:8000/api/v1

### Cod Exemplu
Toate componentele au cod complet în:
`docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md`

---

## 🎉 Success Criteria

### Funcționalitate
- ✅ Toate componentele funcționează
- ✅ API integration corectă
- ✅ Validare și error handling
- ✅ Loading states

### Calitate
- ✅ Type safety (TypeScript)
- ✅ Tests (>80% coverage)
- ✅ Accessibility (WCAG 2.1)
- ✅ Performance (Lighthouse >90)

### UX
- ✅ Responsive design
- ✅ Intuitive navigation
- ✅ Clear feedback
- ✅ Fast loading

---

**Data:** 11 Octombrie 2025, 21:25 UTC+03:00  
**Status:** 📋 Plan Detaliat Gata  
**Următorul Pas:** Începe cu Ziua 1 - Setup
