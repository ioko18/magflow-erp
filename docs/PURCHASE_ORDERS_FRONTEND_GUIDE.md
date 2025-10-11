# Purchase Orders - Ghid Integrare Frontend

## Prezentare Generală

Acest ghid oferă instrucțiuni detaliate pentru integrarea sistemului de Purchase Orders în frontend-ul MagFlow ERP.

## Structura Componentelor Recomandate

```
admin-frontend/src/
├── components/
│   ├── purchase-orders/
│   │   ├── PurchaseOrderList.tsx          # Listă comenzi
│   │   ├── PurchaseOrderForm.tsx          # Formular creare/editare
│   │   ├── PurchaseOrderDetails.tsx       # Detalii comandă
│   │   ├── PurchaseOrderStatusBadge.tsx   # Badge status
│   │   ├── ReceiveOrderModal.tsx          # Modal recepție
│   │   ├── UnreceivedItemsList.tsx        # Listă produse lipsă
│   │   └── PurchaseOrderHistory.tsx       # Istoric modificări
│   └── inventory/
│       └── LowStockWithPO.tsx             # Low Stock îmbunătățit
├── api/
│   └── purchaseOrders.ts                  # API client
└── types/
    └── purchaseOrder.ts                   # TypeScript types
```

## 1. TypeScript Types

Creează fișierul `src/types/purchaseOrder.ts`:

```typescript
export type PurchaseOrderStatus = 
  | 'draft' 
  | 'sent' 
  | 'confirmed' 
  | 'partially_received' 
  | 'received' 
  | 'cancelled';

export type UnreceivedItemStatus = 
  | 'pending' 
  | 'partial' 
  | 'resolved' 
  | 'cancelled';

export interface PurchaseOrderLine {
  id?: number;
  product_id: number;
  product?: {
    id: number;
    name: string;
    sku: string;
    image_url?: string;
  };
  quantity: number;
  received_quantity?: number;
  pending_quantity?: number;
  unit_cost: number;
  discount_percent?: number;
  tax_percent?: number;
  line_total?: number;
  notes?: string;
}

export interface PurchaseOrder {
  id?: number;
  order_number?: string;
  supplier_id: number;
  supplier?: {
    id: number;
    name: string;
    email?: string;
    phone?: string;
  };
  order_date: string;
  expected_delivery_date?: string;
  actual_delivery_date?: string;
  status: PurchaseOrderStatus;
  total_amount: number;
  tax_amount?: number;
  discount_amount?: number;
  shipping_cost?: number;
  currency: string;
  payment_terms?: string;
  notes?: string;
  delivery_address?: string;
  tracking_number?: string;
  lines: PurchaseOrderLine[];
  unreceived_items?: UnreceivedItem[];
  total_ordered_quantity?: number;
  total_received_quantity?: number;
  is_fully_received?: boolean;
  is_partially_received?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UnreceivedItem {
  id: number;
  purchase_order: {
    id: number;
    order_number: string;
  };
  supplier: {
    id: number;
    name: string;
  };
  product: {
    id: number;
    name: string;
    sku: string;
  };
  ordered_quantity: number;
  received_quantity: number;
  unreceived_quantity: number;
  status: UnreceivedItemStatus;
  notes?: string;
  expected_date?: string;
  follow_up_date?: string;
}

export interface PurchaseOrderHistory {
  id: number;
  action: string;
  old_status?: string;
  new_status?: string;
  notes?: string;
  changed_by: number;
  changed_at: string;
  metadata?: Record<string, any>;
}

export interface PendingOrder {
  purchase_order_id: number;
  order_number: string;
  supplier_id: number;
  supplier_name: string;
  ordered_quantity: number;
  received_quantity: number;
  pending_quantity: number;
  expected_delivery_date?: string;
  order_date: string;
  status: PurchaseOrderStatus;
}

export interface LowStockProductWithPO {
  product_id: number;
  name: string;
  sku: string;
  chinese_name?: string;
  image_url?: string;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  minimum_stock: number;
  reorder_point: number;
  reorder_quantity: number;
  adjusted_reorder_quantity: number;  // NEW
  stock_status: 'out_of_stock' | 'critical' | 'low_stock' | 'in_stock';
  suppliers: any[];
  pending_orders: PendingOrder[];  // NEW
  total_pending_quantity: number;  // NEW
  has_pending_orders: boolean;  // NEW
}
```

## 2. API Client

Creează fișierul `src/api/purchaseOrders.ts`:

```typescript
import axios from 'axios';
import { PurchaseOrder, UnreceivedItem, PurchaseOrderHistory } from '@/types/purchaseOrder';

const API_BASE = '/api/v1';

export const purchaseOrdersApi = {
  // List purchase orders
  list: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    supplier_id?: number;
    search?: string;
  }) => {
    const response = await axios.get(`${API_BASE}/purchase-orders`, { params });
    return response.data;
  },

  // Create purchase order
  create: async (data: Partial<PurchaseOrder>) => {
    const response = await axios.post(`${API_BASE}/purchase-orders`, data);
    return response.data;
  },

  // Get purchase order details
  get: async (id: number) => {
    const response = await axios.get(`${API_BASE}/purchase-orders/${id}`);
    return response.data;
  },

  // Update purchase order status
  updateStatus: async (id: number, status: string, notes?: string, metadata?: any) => {
    const response = await axios.patch(`${API_BASE}/purchase-orders/${id}/status`, {
      status,
      notes,
      metadata,
    });
    return response.data;
  },

  // Receive purchase order
  receive: async (id: number, receiptData: {
    receipt_date?: string;
    supplier_invoice_number?: string;
    supplier_invoice_date?: string;
    notes?: string;
    lines: Array<{
      purchase_order_line_id: number;
      received_quantity: number;
    }>;
  }) => {
    const response = await axios.post(`${API_BASE}/purchase-orders/${id}/receive`, receiptData);
    return response.data;
  },

  // Get purchase order history
  getHistory: async (id: number) => {
    const response = await axios.get(`${API_BASE}/purchase-orders/${id}/history`);
    return response.data;
  },

  // List unreceived items
  listUnreceivedItems: async (params?: {
    status?: string;
    supplier_id?: number;
    skip?: number;
    limit?: number;
  }) => {
    const response = await axios.get(`${API_BASE}/purchase-orders/unreceived-items/list`, { params });
    return response.data;
  },

  // Resolve unreceived item
  resolveUnreceivedItem: async (itemId: number, resolutionNotes: string) => {
    const response = await axios.patch(
      `${API_BASE}/purchase-orders/unreceived-items/${itemId}/resolve`,
      { resolution_notes: resolutionNotes }
    );
    return response.data;
  },

  // Get pending orders for product
  getPendingOrdersForProduct: async (productId: number) => {
    const response = await axios.get(
      `${API_BASE}/purchase-orders/products/${productId}/pending-orders`
    );
    return response.data;
  },

  // Get supplier statistics
  getSupplierStatistics: async (supplierId: number) => {
    const response = await axios.get(
      `${API_BASE}/purchase-orders/statistics/by-supplier/${supplierId}`
    );
    return response.data;
  },
};
```

## 3. Componente UI

### 3.1 PurchaseOrderStatusBadge

```tsx
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { PurchaseOrderStatus } from '@/types/purchaseOrder';

interface Props {
  status: PurchaseOrderStatus;
}

const statusConfig: Record<PurchaseOrderStatus, { label: string; color: string }> = {
  draft: { label: 'Draft', color: 'gray' },
  sent: { label: 'Trimis', color: 'blue' },
  confirmed: { label: 'Confirmat', color: 'green' },
  partially_received: { label: 'Parțial Recepționat', color: 'yellow' },
  received: { label: 'Recepționat', color: 'green' },
  cancelled: { label: 'Anulat', color: 'red' },
};

export const PurchaseOrderStatusBadge: React.FC<Props> = ({ status }) => {
  const config = statusConfig[status];
  
  return (
    <Badge variant={config.color as any}>
      {config.label}
    </Badge>
  );
};
```

### 3.2 PurchaseOrderList

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Table } from '@/components/ui/table';
import { PurchaseOrderStatusBadge } from './PurchaseOrderStatusBadge';
import { purchaseOrdersApi } from '@/api/purchaseOrders';
import { PurchaseOrder } from '@/types/purchaseOrder';
import { Plus, Search } from 'lucide-react';

export const PurchaseOrderList: React.FC = () => {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [pagination, setPagination] = useState({ skip: 0, limit: 50, total: 0 });

  useEffect(() => {
    loadOrders();
  }, [search, statusFilter, pagination.skip]);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const response = await purchaseOrdersApi.list({
        skip: pagination.skip,
        limit: pagination.limit,
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setOrders(response.data.orders);
      setPagination(prev => ({ ...prev, total: response.data.pagination.total }));
    } catch (error) {
      console.error('Error loading orders:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Comenzi Furnizori</h1>
        <Button onClick={() => navigate('/purchase-orders/new')}>
          <Plus className="mr-2 h-4 w-4" />
          Comandă Nouă
        </Button>
      </div>

      <div className="flex gap-4">
        <div className="flex-1">
          <Input
            placeholder="Caută după număr comandă, furnizor..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            icon={<Search className="h-4 w-4" />}
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={setStatusFilter}
          placeholder="Toate statusurile"
        >
          <option value="">Toate</option>
          <option value="draft">Draft</option>
          <option value="sent">Trimis</option>
          <option value="confirmed">Confirmat</option>
          <option value="partially_received">Parțial Recepționat</option>
          <option value="received">Recepționat</option>
          <option value="cancelled">Anulat</option>
        </Select>
      </div>

      <Table>
        <thead>
          <tr>
            <th>Număr Comandă</th>
            <th>Furnizor</th>
            <th>Data Comandă</th>
            <th>Livrare Estimată</th>
            <th>Status</th>
            <th>Total</th>
            <th>Progres</th>
            <th>Acțiuni</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id} onClick={() => navigate(`/purchase-orders/${order.id}`)}>
              <td className="font-medium">{order.order_number}</td>
              <td>{order.supplier?.name}</td>
              <td>{new Date(order.order_date).toLocaleDateString('ro-RO')}</td>
              <td>
                {order.expected_delivery_date
                  ? new Date(order.expected_delivery_date).toLocaleDateString('ro-RO')
                  : '-'}
              </td>
              <td>
                <PurchaseOrderStatusBadge status={order.status} />
              </td>
              <td>
                {order.total_amount.toFixed(2)} {order.currency}
              </td>
              <td>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{
                        width: `${
                          (order.total_received_quantity! / order.total_ordered_quantity!) * 100
                        }%`,
                      }}
                    />
                  </div>
                  <span className="text-sm text-gray-600">
                    {order.total_received_quantity}/{order.total_ordered_quantity}
                  </span>
                </div>
              </td>
              <td>
                <Button variant="ghost" size="sm">
                  Detalii
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600">
          Afișare {pagination.skip + 1}-{Math.min(pagination.skip + pagination.limit, pagination.total)} din {pagination.total}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={pagination.skip === 0}
            onClick={() => setPagination(prev => ({ ...prev, skip: Math.max(0, prev.skip - prev.limit) }))}
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            disabled={pagination.skip + pagination.limit >= pagination.total}
            onClick={() => setPagination(prev => ({ ...prev, skip: prev.skip + prev.limit }))}
          >
            Următor
          </Button>
        </div>
      </div>
    </div>
  );
};
```

### 3.3 LowStockWithPO (Enhanced)

```tsx
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Tooltip } from '@/components/ui/tooltip';
import { Clock, CheckCircle } from 'lucide-react';
import { LowStockProductWithPO } from '@/types/purchaseOrder';

interface Props {
  product: LowStockProductWithPO;
}

export const LowStockProductRow: React.FC<Props> = ({ product }) => {
  return (
    <tr>
      <td>{product.name}</td>
      <td>{product.available_quantity}</td>
      <td>{product.reorder_quantity}</td>
      
      {/* NEW: Pending Orders Column */}
      <td>
        {product.has_pending_orders ? (
          <Tooltip content={
            <div className="space-y-2">
              {product.pending_orders.map((order) => (
                <div key={order.purchase_order_id} className="text-sm">
                  <div className="font-medium">{order.order_number}</div>
                  <div>Furnizor: {order.supplier_name}</div>
                  <div>Cantitate: {order.pending_quantity}</div>
                  <div>
                    Livrare: {order.expected_delivery_date 
                      ? new Date(order.expected_delivery_date).toLocaleDateString('ro-RO')
                      : 'N/A'}
                  </div>
                </div>
              ))}
            </div>
          }>
            <Badge variant="blue" className="cursor-help">
              <Clock className="mr-1 h-3 w-3" />
              {product.total_pending_quantity} în comandă
            </Badge>
          </Tooltip>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      
      {/* NEW: Adjusted Reorder Quantity */}
      <td>
        <div className="flex items-center gap-2">
          <span className={product.adjusted_reorder_quantity > 0 ? 'text-orange-600 font-medium' : 'text-green-600'}>
            {product.adjusted_reorder_quantity}
          </span>
          {product.adjusted_reorder_quantity === 0 && (
            <CheckCircle className="h-4 w-4 text-green-600" />
          )}
        </div>
      </td>
      
      <td>
        {/* Supplier selection and other actions */}
      </td>
    </tr>
  );
};
```

### 3.4 ReceiveOrderModal

```tsx
import React, { useState } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { purchaseOrdersApi } from '@/api/purchaseOrders';
import { PurchaseOrder } from '@/types/purchaseOrder';

interface Props {
  order: PurchaseOrder;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ReceiveOrderModal: React.FC<Props> = ({ order, open, onClose, onSuccess }) => {
  const [receivedQuantities, setReceivedQuantities] = useState<Record<number, number>>({});
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleReceive = async () => {
    setLoading(true);
    try {
      const lines = Object.entries(receivedQuantities).map(([lineId, quantity]) => ({
        purchase_order_line_id: parseInt(lineId),
        received_quantity: quantity,
      }));

      await purchaseOrdersApi.receive(order.id!, {
        supplier_invoice_number: invoiceNumber,
        notes,
        lines,
      });

      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error receiving order:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <div className="space-y-4">
        <h2 className="text-xl font-bold">Recepționare Comandă {order.order_number}</h2>

        <div>
          <label className="block text-sm font-medium mb-1">Număr Factură Furnizor</label>
          <Input
            value={invoiceNumber}
            onChange={(e) => setInvoiceNumber(e.target.value)}
            placeholder="INV-2025-001"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium">Cantități Recepționate</label>
          {order.lines.map((line) => (
            <div key={line.id} className="flex items-center gap-4 p-3 border rounded">
              <div className="flex-1">
                <div className="font-medium">{line.product?.name}</div>
                <div className="text-sm text-gray-600">
                  Comandat: {line.quantity} | Recepționat anterior: {line.received_quantity || 0}
                </div>
              </div>
              <Input
                type="number"
                min="0"
                max={line.quantity - (line.received_quantity || 0)}
                value={receivedQuantities[line.id!] || 0}
                onChange={(e) =>
                  setReceivedQuantities({
                    ...receivedQuantities,
                    [line.id!]: parseInt(e.target.value) || 0,
                  })
                }
                className="w-24"
              />
            </div>
          ))}
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Notițe</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full border rounded p-2"
            rows={3}
            placeholder="Observații despre recepție..."
          />
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Anulează
          </Button>
          <Button onClick={handleReceive} disabled={loading}>
            {loading ? 'Se procesează...' : 'Recepționează'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
```

## 4. Routing

Adaugă în `src/App.tsx` sau router-ul principal:

```tsx
import { PurchaseOrderList } from '@/components/purchase-orders/PurchaseOrderList';
import { PurchaseOrderForm } from '@/components/purchase-orders/PurchaseOrderForm';
import { PurchaseOrderDetails } from '@/components/purchase-orders/PurchaseOrderDetails';
import { UnreceivedItemsList } from '@/components/purchase-orders/UnreceivedItemsList';

// În routes:
{
  path: '/purchase-orders',
  element: <PurchaseOrderList />,
},
{
  path: '/purchase-orders/new',
  element: <PurchaseOrderForm />,
},
{
  path: '/purchase-orders/:id',
  element: <PurchaseOrderDetails />,
},
{
  path: '/purchase-orders/unreceived',
  element: <UnreceivedItemsList />,
},
```

## 5. Navigație

Adaugă în meniul principal:

```tsx
<NavItem icon={<ShoppingCart />} to="/purchase-orders">
  Comenzi Furnizori
</NavItem>
<NavItem icon={<AlertTriangle />} to="/purchase-orders/unreceived">
  Produse Lipsă
</NavItem>
```

## 6. Notificări și Alerte

### Badge pentru produse lipsă în meniu:

```tsx
const [unreceivedCount, setUnreceivedCount] = useState(0);

useEffect(() => {
  const fetchUnreceivedCount = async () => {
    const response = await purchaseOrdersApi.listUnreceivedItems({ status: 'pending' });
    setUnreceivedCount(response.data.pagination.total);
  };
  fetchUnreceivedCount();
}, []);

<NavItem icon={<AlertTriangle />} to="/purchase-orders/unreceived">
  Produse Lipsă
  {unreceivedCount > 0 && (
    <Badge variant="red" className="ml-2">{unreceivedCount}</Badge>
  )}
</NavItem>
```

## 7. Best Practices

### 7.1 Error Handling

```tsx
try {
  await purchaseOrdersApi.create(orderData);
  toast.success('Comanda a fost creată cu succes!');
} catch (error) {
  if (error.response?.status === 400) {
    toast.error(error.response.data.detail);
  } else {
    toast.error('A apărut o eroare. Vă rugăm încercați din nou.');
  }
}
```

### 7.2 Loading States

```tsx
{loading ? (
  <div className="flex justify-center p-8">
    <Spinner size="lg" />
  </div>
) : (
  <Table data={orders} />
)}
```

### 7.3 Optimistic Updates

```tsx
const updateStatus = async (orderId: number, newStatus: string) => {
  // Update UI immediately
  setOrders(orders.map(o => 
    o.id === orderId ? { ...o, status: newStatus } : o
  ));

  try {
    await purchaseOrdersApi.updateStatus(orderId, newStatus);
  } catch (error) {
    // Revert on error
    loadOrders();
    toast.error('Eroare la actualizare status');
  }
};
```

## 8. Testing

### Unit Tests

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { PurchaseOrderStatusBadge } from './PurchaseOrderStatusBadge';

describe('PurchaseOrderStatusBadge', () => {
  it('renders correct label for sent status', () => {
    render(<PurchaseOrderStatusBadge status="sent" />);
    expect(screen.getByText('Trimis')).toBeInTheDocument();
  });

  it('applies correct color class', () => {
    const { container } = render(<PurchaseOrderStatusBadge status="confirmed" />);
    expect(container.firstChild).toHaveClass('bg-green-100');
  });
});
```

## 9. Performance Optimization

### Memoization

```tsx
const MemoizedOrderRow = React.memo(({ order }) => (
  <tr>
    {/* ... */}
  </tr>
), (prevProps, nextProps) => {
  return prevProps.order.id === nextProps.order.id &&
         prevProps.order.status === nextProps.order.status;
});
```

### Lazy Loading

```tsx
const PurchaseOrderDetails = React.lazy(() => 
  import('./components/purchase-orders/PurchaseOrderDetails')
);

<Suspense fallback={<Spinner />}>
  <PurchaseOrderDetails />
</Suspense>
```

## 10. Accessibility

```tsx
<button
  aria-label="Recepționează comandă"
  aria-describedby="order-details"
  onClick={handleReceive}
>
  Recepționează
</button>

<div id="order-details" className="sr-only">
  Comandă {order.order_number} de la {order.supplier.name}
</div>
```

## Resurse Suplimentare

- [Documentație API completă](./PURCHASE_ORDERS_SYSTEM.md)
- [Shadcn/ui Components](https://ui.shadcn.com/)
- [React Query pentru caching](https://tanstack.com/query/latest)
- [Zod pentru validare](https://zod.dev/)

## Suport

Pentru întrebări sau probleme:
- Verifică console-ul browser pentru erori
- Testează endpoint-urile în Postman/Swagger
- Contactează echipa de backend pentru probleme API
