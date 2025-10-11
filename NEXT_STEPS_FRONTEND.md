# 🚀 Purchase Orders - Următorii Pași Frontend

## 📊 Status Curent

✅ **Backend:** 100% Complet și funcțional  
✅ **Frontend Core:** 60% Complet (6/9 componente)  
⏳ **Configurare:** Necesită routing și integrare  

**Componente Complete:**
1. ✅ TypeScript Types
2. ✅ API Client
3. ✅ PurchaseOrderStatusBadge
4. ✅ PurchaseOrderList
5. ✅ PurchaseOrderForm
6. ✅ PurchaseOrderDetails

---

## 🎯 Pași Imediați (1-2 ore)

### Pas 1: Configurare Routing (30 min)

**Fișier:** `admin-frontend/src/App.tsx` (sau router-ul principal)

```typescript
// 1. Adaugă import-uri
import PurchaseOrderList from './components/purchase-orders/PurchaseOrderList';
import PurchaseOrderForm from './components/purchase-orders/PurchaseOrderForm';
import PurchaseOrderDetails from './components/purchase-orders/PurchaseOrderDetails';

// 2. Adaugă route-uri în router
<Routes>
  {/* ... alte route-uri existente */}
  
  {/* Purchase Orders Routes */}
  <Route path="/purchase-orders" element={<PurchaseOrderList />} />
  <Route path="/purchase-orders/new" element={<PurchaseOrderForm />} />
  <Route path="/purchase-orders/:id" element={<PurchaseOrderDetails />} />
  
  {/* ... */}
</Routes>
```

### Pas 2: Adaugă în Meniu (15 min)

**Fișier:** `admin-frontend/src/components/Layout.tsx` (sau componenta de meniu)

```typescript
// Adaugă în meniu
{
  label: 'Purchase Orders',
  icon: ShoppingCartIcon, // sau iconița ta preferată
  path: '/purchase-orders',
  // badge: pendingOrdersCount // opțional
}
```

### Pas 3: Configurare API (15 min)

**Fișier:** `admin-frontend/src/api/purchaseOrders.ts`

```typescript
// Actualizează API_BASE dacă este necesar
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Sau în .env
// VITE_API_BASE_URL=http://localhost:8000/api/v1
```

**Fișier:** `admin-frontend/src/api/axios.ts` (sau config axios)

```typescript
// Adaugă interceptor pentru autentificare
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Pas 4: Testare Inițială (30 min)

```bash
# 1. Pornește dev server
cd admin-frontend
npm run dev

# 2. Deschide browser
# http://localhost:5173 (sau portul tău)

# 3. Testează:
# - Navigare la /purchase-orders
# - Click pe "New Purchase Order"
# - Completare formular (mock data)
# - Vizualizare listă
# - Click pe o comandă pentru detalii
```

---

## 🔧 Componente Rămase (6-8 ore)

### Componenta 1: ReceiveOrderModal (3-4 ore)

**Prioritate:** ÎNALTĂ  
**Când:** După configurare routing

**Creează:** `admin-frontend/src/components/purchase-orders/ReceiveOrderModal.tsx`

**Cod de bază:**
```typescript
import React, { useState } from 'react';
import { purchaseOrdersApi } from '../../api/purchaseOrders';

interface ReceiveOrderModalProps {
  orderId: number;
  lines: PurchaseOrderLine[];
  onClose: () => void;
  onSuccess: () => void;
}

export const ReceiveOrderModal: React.FC<ReceiveOrderModalProps> = ({
  orderId,
  lines,
  onClose,
  onSuccess,
}) => {
  const [receivedQuantities, setReceivedQuantities] = useState<Record<number, number>>({});
  
  const handleSubmit = async () => {
    await purchaseOrdersApi.receive(orderId, {
      receipt_date: new Date().toISOString(),
      lines: Object.entries(receivedQuantities).map(([lineId, qty]) => ({
        purchase_order_line_id: Number(lineId),
        received_quantity: qty,
      })),
    });
    onSuccess();
  };
  
  // ... rest of component
};
```

**Features necesare:**
- Input pentru cantitate recepționată per produs
- Validare: cantitate <= cantitate comandată
- Calcul automat discrepanțe
- Submit și actualizare status

### Componenta 2: LowStockWithPO Integration (3-4 ore)

**Prioritate:** ÎNALTĂ  
**Când:** După ReceiveOrderModal

**Modifică:** `admin-frontend/src/components/inventory/LowStockWithPO.tsx`

**Modificări necesare:**

1. **Update API call:**
```typescript
// Schimbă endpoint-ul
const response = await axios.get('/api/v1/inventory/low-stock-with-suppliers');
```

2. **Update interface:**
```typescript
interface LowStockProduct {
  // ... câmpuri existente
  pending_orders?: PendingOrder[];
  total_pending_quantity?: number;
  adjusted_reorder_quantity?: number;
  has_pending_orders?: boolean;
}
```

3. **Adaugă indicator vizual:**
```typescript
{product.has_pending_orders && (
  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
    📦 {product.total_pending_quantity} în comandă
  </span>
)}
```

4. **Adaugă tooltip:**
```typescript
<Tooltip>
  <TooltipTrigger>
    <InfoIcon className="w-4 h-4" />
  </TooltipTrigger>
  <TooltipContent>
    <div className="space-y-1">
      {product.pending_orders?.map(order => (
        <div key={order.order_number}>
          <strong>{order.order_number}</strong>: {order.pending_quantity} buc
          <br />
          <small>Livrare: {formatDate(order.expected_delivery_date)}</small>
        </div>
      ))}
    </div>
  </TooltipContent>
</Tooltip>
```

5. **Calcul cantitate ajustată:**
```typescript
const quantityToOrder = product.adjusted_reorder_quantity || product.reorder_quantity;
```

### Componenta 3: UnreceivedItemsList (3-4 ore) - OPȚIONAL

**Prioritate:** MEDIE  
**Când:** După LowStockWithPO

**Creează:** `admin-frontend/src/components/purchase-orders/UnreceivedItemsList.tsx`

**Features:**
- Listă produse nerecepționate
- Filtrare după status
- Modal rezolvare
- Acțiuni (resolve, follow-up)

---

## 📋 Checklist Complet

### Configurare Imediată
- [ ] Adaugă routing în App.tsx
- [ ] Adaugă în meniu navigation
- [ ] Configurare API base URL
- [ ] Configurare axios interceptors
- [ ] Test navigare la /purchase-orders

### Testare Componente Existente
- [ ] Test PurchaseOrderList (listă, filtrare, paginare)
- [ ] Test PurchaseOrderForm (creare, validare, submit)
- [ ] Test PurchaseOrderDetails (vizualizare, update status)
- [ ] Test responsive design (mobile, tablet, desktop)
- [ ] Test error handling

### Componente Noi
- [ ] Implementează ReceiveOrderModal
- [ ] Test recepție produse
- [ ] Modifică LowStockWithPO
- [ ] Test integrare Low Stock
- [ ] Implementează UnreceivedItemsList (opțional)

### Polish și Finalizare
- [ ] UI/UX improvements
- [ ] Loading states optimization
- [ ] Error messages improvement
- [ ] Accessibility (a11y) check
- [ ] Performance optimization

---

## 🧪 Testing

### Manual Testing
```bash
# 1. Test flow complet
# - Creare comandă nouă
# - Vizualizare în listă
# - Update status la "confirmed"
# - Recepție produse
# - Verificare istoric

# 2. Test edge cases
# - Formular gol
# - Cantități invalide
# - Network errors
# - Loading states
```

### Automated Testing (opțional)
```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e
```

---

## 🎨 UI/UX Improvements

### Quick Wins
1. **Loading Skeletons** - În loc de "Loading..."
2. **Toast Notifications** - Pentru success/error messages
3. **Keyboard Shortcuts** - Pentru acțiuni rapide
4. **Drag & Drop** - Pentru reordonare linii în formular
5. **Auto-save** - Pentru formular (draft)

### Nice to Have
6. **Dark Mode** - Suport pentru tema întunecată
7. **Export** - Export comenzi în Excel/PDF
8. **Print** - Print-friendly view pentru comenzi
9. **Bulk Actions** - Acțiuni multiple în listă
10. **Advanced Filters** - Filtre mai complexe

---

## 📊 Estimare Timp Total Rămas

### Esențial (Minimum Viable Product)
- Configurare routing: 30 min
- Testare componente: 1 oră
- ReceiveOrderModal: 3-4 ore
- LowStockWithPO: 3-4 ore
- **Total MVP:** ~8-10 ore

### Complet (Full Featured)
- MVP: 8-10 ore
- UnreceivedItemsList: 3-4 ore
- UI/UX polish: 2-3 ore
- Testing: 2-3 ore
- **Total Complet:** ~15-20 ore

### Doar Configurare și Testare (Quick Start)
- Configurare: 1 oră
- Testare: 1 oră
- **Total Quick:** ~2 ore

---

## 🎯 Recomandare

### Opțiunea 1: Quick Start (2 ore)
**Pentru:** Testare rapidă și demo
1. Configurare routing (30 min)
2. Testare componente existente (1 oră)
3. Demo pentru stakeholders (30 min)

### Opțiunea 2: MVP (8-10 ore)
**Pentru:** Sistem funcțional complet
1. Quick Start (2 ore)
2. ReceiveOrderModal (3-4 ore)
3. LowStockWithPO (3-4 ore)

### Opțiunea 3: Full Featured (15-20 ore)
**Pentru:** Sistem production-ready
1. MVP (8-10 ore)
2. UnreceivedItemsList (3-4 ore)
3. Polish și testing (4-6 ore)

---

## 📞 Ajutor și Resurse

### Documentație
- **Cod Exemplu:** `docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md`
- **API Docs:** `docs/PURCHASE_ORDERS_SYSTEM.md`
- **Progres:** `FRONTEND_IMPLEMENTATION_COMPLETE.md`

### API Testing
- **Swagger UI:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health/live

### Comenzi Utile
```bash
# Dev server
npm run dev

# Type check
npm run type-check

# Lint
npm run lint

# Build
npm run build
```

---

## 🎉 Succes!

**Ai deja 60% din frontend implementat!**

Următorul pas: **Configurare routing și testare** (1-2 ore)

După aceea: **ReceiveOrderModal** pentru funcționalitate completă (3-4 ore)

**Total pentru sistem funcțional:** ~4-6 ore de lucru

---

**Data:** 11 Octombrie 2025, 21:40 UTC+03:00  
**Status:** ✅ Core Complete | ⏳ Configuration Needed  
**Progres:** 60% Frontend | 100% Backend
