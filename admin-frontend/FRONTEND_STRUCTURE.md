# Frontend Structure - MagFlow ERP Admin
**Data: 2025-10-10**

## Structură Reorganizată

### Componente (`src/components/`)

```
components/
├── products/              # Componente pentru produse
│   ├── index.ts          # Barrel export
│   ├── ProductForm.tsx
│   ├── ProductFieldEditor.tsx
│   ├── ProductValidation.tsx
│   ├── ProductMeasurementsModal.tsx
│   ├── MatchingGroupCard.tsx
│   ├── QuickEditModal.tsx
│   ├── QuickOfferUpdate.tsx
│   ├── QuickOfferUpdateModal.tsx
│   ├── SKUHistoryDrawer.tsx
│   ├── PricingIntelligenceDrawer.tsx
│   ├── EANSearchModal.tsx
│   ├── CategoryBrowser.tsx
│   └── CategoryBrowserModal.tsx
│
├── suppliers/            # Componente pentru furnizori
│   ├── index.ts
│   ├── SupplierForm.tsx
│   └── DraggableSuppliersTable.tsx
│
├── common/              # Componente comune/reutilizabile
│   ├── index.ts
│   ├── AdvancedFilters.tsx
│   ├── BulkOperations.tsx
│   ├── BulkOperationsDrawer.tsx
│   ├── ExportImport.tsx
│   └── InlineEditCell.tsx
│
├── dashboard/           # Componente pentru dashboard
│   ├── index.ts
│   ├── DashboardCharts.tsx
│   ├── MonitoringDashboard.tsx
│   └── NotificationPanel.tsx
│
├── emag/               # Componente pentru eMAG
│   └── [13 componente existente]
│
├── Layout.tsx
├── ErrorBoundary.tsx
└── ProtectedRoute.tsx
```

### Services (`src/services/`)

```
services/
├── products/
│   ├── index.ts
│   └── productsApi.ts       # API complet pentru produse
│
├── suppliers/
│   ├── index.ts
│   └── suppliersApi.ts      # API complet pentru furnizori
│
├── orders/
│   ├── index.ts
│   └── ordersApi.ts         # API complet pentru comenzi
│
├── emag/
│   ├── index.ts
│   ├── emagAdvancedApi.ts
│   └── unifiedProductsApi.ts
│
├── system/
│   ├── index.ts
│   └── notificationService.ts
│
├── api.ts              # API general (axios instance)
└── apiClient.ts        # Client HTTP cu error handling
```

### Hooks (`src/hooks/`)

```
hooks/
├── products/
│   ├── index.ts
│   └── useProducts.ts       # State management pentru produse
│
├── suppliers/
│   ├── index.ts
│   └── useSuppliers.ts      # State management pentru furnizori
│
├── common/
│   ├── index.ts
│   ├── usePerformance.ts    # Monitoring performanță
│   ├── usePagination.ts     # Paginare reutilizabilă
│   └── useDebounce.ts       # Debounce pentru search
│
└── index.ts                 # Barrel export pentru toate hooks
```

## Ghid de Utilizare

### Import Componente

```typescript
// Înainte
import ProductForm from '../components/ProductForm';
import SupplierForm from '../components/SupplierForm';

// Acum
import { ProductForm } from '../components/products';
import { SupplierForm } from '../components/suppliers';
import { AdvancedFilters, BulkOperations } from '../components/common';
```

### Utilizare Hooks

```typescript
import { useProducts, usePagination, useDebounce } from '../hooks';

function ProductsPage() {
  const { 
    products, 
    loading, 
    error,
    createProduct, 
    updateProduct,
    deleteProduct,
    bulkUpdate,
    importProducts,
    exportProducts
  } = useProducts();
  
  const { pagination, setPage, setLimit } = usePagination(20);
  const debouncedSearch = useDebounce(searchTerm, 500);
  
  // ... rest of component
}
```

### Utilizare Services Direct

```typescript
import { productsApi } from '../services/products';
import { suppliersApi } from '../services/suppliers';
import { ordersApi } from '../services/orders';

// Fetch products
const products = await productsApi.getProducts({ 
  search: 'laptop',
  category_id: 5,
  page: 1,
  limit: 20
});

// Create product
const newProduct = await productsApi.createProduct({
  name: 'Laptop Dell',
  sku: 'DELL-001',
  price: 3500,
  stock: 10
});

// Bulk update
await productsApi.bulkUpdateProducts([
  { id: 1, data: { price: 3200 } },
  { id: 2, data: { stock: 15 } }
]);

// Import from file
await productsApi.importProducts(file, { supplier_id: 5 });

// Export to Excel
await productsApi.exportProducts({ category_id: 5 });
```

## Beneficii

### 1. Organizare Logică
- Componente grupate pe funcționalitate
- Separare clară a responsabilităților
- Structură intuitivă

### 2. Reutilizabilitate
- Hooks custom pentru logică comună
- Services API bine definite
- Componente modulare

### 3. Type Safety
- TypeScript interfaces pentru toate entitățile
- Type-safe API calls
- Autocomplete în IDE

### 4. Developer Experience
- Import-uri simple prin barrel exports
- Navigare rapidă în cod
- Pattern-uri consistente

## Best Practices

### 1. Componente
- Păstrați componentele mici și focusate
- Folosiți hooks pentru logică complexă
- Extrageți logica reutilizabilă în hooks custom

### 2. Services
- Toate API calls prin services
- Error handling consistent
- Type-safe responses

### 3. Hooks
- Un hook = o responsabilitate
- Hooks custom pentru logică reutilizabilă
- Folosiți hooks built-in React când e posibil

### 4. State Management
- Local state pentru UI
- Hooks pentru business logic
- Context pentru state global

## Note Tehnice

### Services API
Serviciile noi (`productsApi`, `suppliersApi`, `ordersApi`) sunt exemple de structură.
Pot necesita ajustări pentru a se potrivi cu API-ul backend actual.

### Hooks
Hooks-urile custom sunt pregătite pentru utilizare și pot fi extinse cu funcționalități noi.

### Migrare
Componentele existente pot fi migrate treptat la noua structură.
Nu este necesară migrarea imediată a tuturor componentelor.
