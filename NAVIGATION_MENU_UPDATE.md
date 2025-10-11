# Navigation Menu - Adding Low Stock Suppliers

## Overview

Pentru a face feature-ul Low Stock Suppliers usor accesibil, trebuie sa adaugi un link in meniul de navigare.

## Locatia recomandata

In meniul principal, sub sectiunea Products sau Inventory.

## Implementare in Layout.tsx

Fisier: admin-frontend/src/components/Layout.tsx

Adauga noul item in meniu:

```typescript
{
  key: 'low-stock-suppliers',
  label: 'Low Stock Suppliers',
  icon: <WarningOutlined />,
  path: '/low-stock-suppliers'
}
```

## Import iconite

```typescript
import { WarningOutlined } from '@ant-design/icons';
```

## Exemplu complet

```typescript
const menuItems = [
  {
    key: 'products',
    icon: <ShoppingOutlined />,
    label: 'Products',
    children: [
      {
        key: 'products-list',
        label: 'All Products',
        path: '/products'
      },
      {
        key: 'inventory',
        label: 'Inventory',
        path: '/inventory'
      },
      {
        key: 'low-stock-suppliers',
        label: 'Low Stock Suppliers',
        icon: <WarningOutlined />,
        path: '/low-stock-suppliers'
      }
    ]
  }
];
```

Ruta este deja configurata in App.tsx la path: /low-stock-suppliers
