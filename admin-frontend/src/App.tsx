import React, { Suspense, lazy } from 'react'
import { App as AntApp, Spin } from 'antd'
import {
  createBrowserRouter,
  RouterProvider,
  Outlet,
  Navigate,
} from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { NotificationProvider } from './contexts/NotificationContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

// Eager load critical pages
import Dashboard from './pages/system/Dashboard'
import Login from './pages/Login'

// Lazy load other pages
const EmagProductSyncV2 = lazy(() => import('./pages/emag/EmagProductSyncV2'))
const EmagProductPublishing = lazy(() => import('./pages/emag/EmagProductPublishing'))
const EmagAWB = lazy(() => import('./pages/emag/EmagAWB'))
const EmagEAN = lazy(() => import('./pages/emag/EmagEAN'))
const EmagInvoices = lazy(() => import('./pages/emag/EmagInvoices'))
const EmagAddresses = lazy(() => import('./pages/emag/EmagAddresses'))
const Products = lazy(() => import('./pages/products/Products'))
const Orders = lazy(() => import('./pages/orders/Orders'))
const Customers = lazy(() => import('./pages/orders/Customers'))
const Users = lazy(() => import('./pages/system/Users'))
const Settings = lazy(() => import('./pages/system/Settings'))
const NotificationSettings = lazy(() => import('./pages/system/NotificationSettings'))
const SupplierMatching = lazy(() => import('./pages/suppliers/SupplierMatching'))
const Suppliers = lazy(() => import('./pages/suppliers/Suppliers'))
const SupplierProducts = lazy(() => import('./pages/suppliers/SupplierProducts'))
const SupplierProductsSheet = lazy(() => import('./pages/suppliers/SupplierProductsSheet'))
const ProductImport = lazy(() => import('./pages/products/ProductImport'))
const Inventory = lazy(() => import('./pages/products/Inventory'))
const LowStockSuppliers = lazy(() => import('./pages/products/LowStockSuppliers'))
const ProductMatchingSuggestions = lazy(() => import('./pages/products/ProductMatchingSuggestions'))

// Purchase Orders
const PurchaseOrderListModern = lazy(() => import('./components/purchase-orders/PurchaseOrderListModern'))
const PurchaseOrderForm = lazy(() => import('./components/purchase-orders/PurchaseOrderForm'))
const PurchaseOrderDetails = lazy(() => import('./components/purchase-orders/PurchaseOrderDetails'))
const UnreceivedItemsList = lazy(() => import('./components/purchase-orders/UnreceivedItemsList'))

// Loading component
const PageLoader = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    minHeight: '400px',
    flexDirection: 'column',
    gap: '16px'
  }}>
    <Spin size="large" />
    <div style={{ color: '#666', fontSize: '16px' }}>Se încarcă...</div>
  </div>
)

const AuthProviderWrapper: React.FC = () => {
  return (
    <AuthProvider>
      <NotificationProvider>
        <Outlet />
      </NotificationProvider>
    </AuthProvider>
  );
};

const AppLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>; // Or a loading spinner
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <ErrorBoundary>
      <Layout>
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </Layout>
    </ErrorBoundary>
  );
}

const router = createBrowserRouter(
  [
    {
      element: <AuthProviderWrapper />,
      children: [
        {
          path: '/login',
          element: <Login />,
        },
        {
          path: '/',
          element: <AppLayout />,
          children: [
            {
              index: true,
              element: <Dashboard />,
            },
            {
              path: 'dashboard',
              element: <Dashboard />,
            },
            {
              path: 'emag',
              element: <Navigate to="/emag/sync-v2" replace />,
            },
            {
              path: 'emag/sync-v2',
              element: <EmagProductSyncV2 />,
            },
            {
              path: 'emag/publishing',
              element: <EmagProductPublishing />,
            },
            {
              path: 'emag/awb',
              element: <EmagAWB />,
            },
            {
              path: 'emag/ean',
              element: <EmagEAN />,
            },
            {
              path: 'emag/invoices',
              element: <EmagInvoices />,
            },
            {
              path: 'emag/addresses',
              element: <EmagAddresses />,
            },
            {
              path: 'products',
              element: <Products />,
            },
            {
              path: 'inventory',
              element: <Inventory />,
            },
            {
              path: 'low-stock-suppliers',
              element: <LowStockSuppliers />,
            },
            {
              path: 'product-matching-suggestions',
              element: <ProductMatchingSuggestions />,
            },
            {
              path: 'orders',
              element: <Orders />,
            },
            {
              path: 'customers',
              element: <Customers />,
            },
            {
              path: 'suppliers',
              element: <Suppliers />,
            },
            {
              path: 'suppliers/products',
              element: <SupplierProducts />,
            },
            {
              path: 'suppliers/products-sheet',
              element: <SupplierProductsSheet />,
            },
            {
              path: 'suppliers/matching',
              element: <SupplierMatching />,
            },
            {
              path: 'products/import',
              element: <ProductImport />,
            },
            {
              path: 'users',
              element: <Users />,
            },
            {
              path: 'settings',
              element: <Settings />,
            },
            {
              path: 'notification-settings',
              element: <NotificationSettings />,
            },
            // Purchase Orders routes
            {
              path: 'purchase-orders',
              element: <PurchaseOrderListModern />,
            },
            {
              path: 'purchase-orders/new',
              element: <PurchaseOrderForm />,
            },
            {
              path: 'purchase-orders/unreceived',
              element: <UnreceivedItemsList />,
            },
            {
              path: 'purchase-orders/:id',
              element: <PurchaseOrderDetails />,
            },
            {
              path: '*',
              element: <Navigate to="/" replace />,
            },
          ],
        },
      ],
    },
  ],
)

function App() {
  return (
    <ThemeProvider>
      <AntApp>
        <RouterProvider router={router} />
      </AntApp>
    </ThemeProvider>
  )
}

export default App
