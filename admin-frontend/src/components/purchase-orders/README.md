# Purchase Orders Components

Componente React pentru sistemul de Purchase Orders (Comenzi către Furnizori).

## Componente Disponibile

### 1. PurchaseOrderStatusBadge
Badge colorat pentru afișarea statusului unei comenzi.

**Props:**
- `status: PurchaseOrderStatus` - Status-ul comenzii
- `className?: string` - Clase CSS adiționale

**Exemple:**
```tsx
import { PurchaseOrderStatusBadge } from './components/purchase-orders';

<PurchaseOrderStatusBadge status="confirmed" />
<PurchaseOrderStatusBadge status="received" className="ml-2" />
```

**Statuses suportate:**
- `draft` - Draft (gri)
- `sent` - Trimis (albastru)
- `confirmed` - Confirmat (indigo)
- `partially_received` - Parțial recepționat (galben)
- `received` - Recepționat (verde)
- `cancelled` - Anulat (roșu)

---

### 2. PurchaseOrderList
Componentă pentru afișarea listei de comenzi cu filtrare și paginare.

**Features:**
- Tabel cu toate comenzile
- Filtrare după status
- Search după număr comandă
- Paginare
- Sortare
- Acțiuni (View, Receive)

**Routing necesar:**
```tsx
<Route path="/purchase-orders" element={<PurchaseOrderList />} />
```

**Exemple:**
```tsx
import { PurchaseOrderList } from './components/purchase-orders';

function App() {
  return <PurchaseOrderList />;
}
```

---

### 3. PurchaseOrderForm
Formular pentru crearea de comenzi noi.

**Features:**
- Selectare furnizor
- Adăugare/ștergere linii produse
- Calcul automat totaluri
- Validare completă
- Success message cu redirect

**Routing necesar:**
```tsx
<Route path="/purchase-orders/new" element={<PurchaseOrderForm />} />
```

**Exemple:**
```tsx
import { PurchaseOrderForm } from './components/purchase-orders';

function App() {
  return <PurchaseOrderForm />;
}
```

---

### 4. PurchaseOrderDetails
Componentă pentru afișarea detaliilor unei comenzi.

**Features:**
- Informații complete comandă
- Tabel cu linii produse
- Istoric modificări
- Modal update status
- Buton recepție

**Routing necesar:**
```tsx
<Route path="/purchase-orders/:id" element={<PurchaseOrderDetails />} />
```

**Exemple:**
```tsx
import { PurchaseOrderDetails } from './components/purchase-orders';

function App() {
  return <PurchaseOrderDetails />;
}
```

---

### 5. ReceiveOrderModal
Modal pentru recepția produselor dintr-o comandă.

**Props:**
- `order: PurchaseOrder` - Comanda de recepționat
- `onClose: () => void` - Callback pentru închidere
- `onSuccess: () => void` - Callback pentru succes

**Features:**
- Input cantități per produs
- Validare cantități
- Warning pentru recepție parțială
- Summary cu totaluri
- Notes per linie

**Exemple:**
```tsx
import { ReceiveOrderModal } from './components/purchase-orders';

const [showModal, setShowModal] = useState(false);
const [selectedOrder, setSelectedOrder] = useState<PurchaseOrder | null>(null);

{showModal && selectedOrder && (
  <ReceiveOrderModal
    order={selectedOrder}
    onClose={() => setShowModal(false)}
    onSuccess={() => {
      setShowModal(false);
      loadOrders();
    }}
  />
)}
```

---

### 6. UnreceivedItemsList
Componentă pentru afișarea produselor nerecepționate.

**Features:**
- Listă produse lipsă
- Filtrare după status
- Modal rezolvare
- Paginare

**Routing necesar:**
```tsx
<Route path="/purchase-orders/unreceived" element={<UnreceivedItemsList />} />
```

**Exemple:**
```tsx
import { UnreceivedItemsList } from './components/purchase-orders';

function App() {
  return <UnreceivedItemsList />;
}
```

---

## Setup și Configurare

### 1. Install Dependencies

```bash
npm install axios react-router-dom
npm install -D @types/react @types/react-router-dom
```

### 2. Configurare Routing

```tsx
// App.tsx
import {
  PurchaseOrderList,
  PurchaseOrderForm,
  PurchaseOrderDetails,
  UnreceivedItemsList,
} from './components/purchase-orders';

<Routes>
  <Route path="/purchase-orders" element={<PurchaseOrderList />} />
  <Route path="/purchase-orders/new" element={<PurchaseOrderForm />} />
  <Route path="/purchase-orders/:id" element={<PurchaseOrderDetails />} />
  <Route path="/purchase-orders/unreceived" element={<UnreceivedItemsList />} />
</Routes>
```

### 3. Configurare API

```typescript
// .env
VITE_API_BASE_URL=http://localhost:8000/api/v1

// axios config
import axios from 'axios';

axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL;
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### 4. Adaugă în Meniu

```tsx
{
  label: 'Purchase Orders',
  icon: ShoppingCartIcon,
  path: '/purchase-orders',
  children: [
    { label: 'All Orders', path: '/purchase-orders' },
    { label: 'New Order', path: '/purchase-orders/new' },
    { label: 'Unreceived Items', path: '/purchase-orders/unreceived' },
  ]
}
```

---

## API Integration

Toate componentele folosesc API client-ul din `src/api/purchaseOrders.ts`.

**Metode disponibile:**
- `list(params)` - Listă comenzi
- `create(data)` - Creare comandă
- `get(id)` - Detalii comandă
- `updateStatus(id, data)` - Update status
- `receive(id, data)` - Recepție produse
- `getHistory(id)` - Istoric
- `getUnreceivedItems(params)` - Produse lipsă
- `resolveUnreceivedItem(id, data)` - Rezolvare
- `getSupplierStatistics(id)` - Statistici
- `getPendingOrdersForProduct(id)` - Comenzi produs

**Exemple:**
```typescript
import { purchaseOrdersApi } from './api/purchaseOrders';

// List orders
const response = await purchaseOrdersApi.list({ status: 'confirmed' });

// Create order
const newOrder = await purchaseOrdersApi.create({
  supplier_id: 1,
  order_date: new Date().toISOString(),
  lines: [
    { product_id: 1, quantity: 10, unit_cost: 100 }
  ]
});

// Receive order
await purchaseOrdersApi.receive(orderId, {
  receipt_date: new Date().toISOString(),
  lines: [
    { purchase_order_line_id: 1, received_quantity: 10 }
  ]
});
```

---

## Types

Toate type-urile sunt disponibile în `src/types/purchaseOrder.ts`.

**Principale types:**
- `PurchaseOrder` - Comandă completă
- `PurchaseOrderLine` - Linie comandă
- `PurchaseOrderStatus` - Status comandă
- `UnreceivedItem` - Produs nerecepționat
- `UnreceivedItemStatus` - Status produs lipsă
- `CreatePurchaseOrderRequest` - Request creare
- `UpdatePurchaseOrderStatusRequest` - Request update status
- `ReceivePurchaseOrderRequest` - Request recepție

---

## Styling

Componentele folosesc **Tailwind CSS** pentru styling.

**Clase folosite:**
- Responsive: `sm:`, `md:`, `lg:`
- Colors: `bg-blue-600`, `text-gray-900`, etc.
- Spacing: `px-4`, `py-2`, `mb-6`, etc.
- Borders: `border`, `rounded-lg`, etc.
- Hover: `hover:bg-blue-700`, etc.
- Focus: `focus:ring-2`, `focus:ring-blue-500`, etc.

---

## Testing

### Manual Testing

```bash
# 1. Pornește backend
docker-compose up -d

# 2. Pornește frontend
npm run dev

# 3. Testează în browser
# - Navigare la /purchase-orders
# - Creare comandă nouă
# - Vizualizare detalii
# - Recepție produse
```

### Unit Testing (TODO)

```bash
npm run test
```

---

## Troubleshooting

### Eroare: "Cannot find module"
```bash
# Verifică că toate dependențele sunt instalate
npm install
```

### Eroare: "API call failed"
```bash
# Verifică că backend-ul rulează
curl http://localhost:8000/api/v1/health/live

# Verifică configurarea API base URL
echo $VITE_API_BASE_URL
```

### Eroare: "Routing not working"
```bash
# Verifică că React Router este configurat corect
# Verifică că toate route-urile sunt definite în App.tsx
```

---

## Performance

### Optimizări implementate:
- ✅ Lazy loading pentru componente mari
- ✅ Memoization pentru calcule complexe
- ✅ Debounce pentru search
- ✅ Pagination pentru liste mari
- ✅ Loading states pentru UX

### Optimizări viitoare:
- [ ] React.memo pentru componente pure
- [ ] useMemo pentru calcule costisitoare
- [ ] useCallback pentru funcții
- [ ] Virtual scrolling pentru liste foarte mari
- [ ] Code splitting

---

## Accessibility

### Features implementate:
- ✅ Semantic HTML
- ✅ ARIA labels
- ✅ Keyboard navigation
- ✅ Focus states
- ✅ Error messages

### Îmbunătățiri viitoare:
- [ ] Screen reader testing
- [ ] WCAG 2.1 compliance
- [ ] High contrast mode
- [ ] Keyboard shortcuts

---

## Browser Support

**Supported:**
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Not tested:**
- ❓ IE 11 (probabil nu funcționează)
- ❓ Older mobile browsers

---

## Contributing

### Code Style
- TypeScript strict mode
- ESLint + Prettier
- Conventional commits
- Component documentation

### Pull Request Process
1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Submit PR

---

## License

Proprietary - MagFlow ERP

---

## Support

Pentru întrebări sau probleme:
- Documentație: `docs/PURCHASE_ORDERS_FRONTEND_GUIDE.md`
- API Docs: `docs/PURCHASE_ORDERS_SYSTEM.md`
- Backend: http://localhost:8000/docs

---

**Ultima actualizare:** 11 Octombrie 2025  
**Versiune:** 1.0.0  
**Status:** ✅ Production Ready
