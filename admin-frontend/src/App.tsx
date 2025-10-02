import React from 'react'
import { App as AntApp } from 'antd'
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
import Dashboard from './pages/Dashboard'
import EmagProductSyncV2 from './pages/EmagProductSyncV2'
import EmagProductPublishing from './pages/EmagProductPublishing'
import EmagAWB from './pages/EmagAWB'
import EmagEAN from './pages/EmagEAN'
import EmagInvoices from './pages/EmagInvoices'
import EmagAddresses from './pages/EmagAddresses'
import Products from './pages/Products'
import Orders from './pages/Orders'
import Customers from './pages/Customers'
import Users from './pages/Users'
import Settings from './pages/Settings'
import Login from './pages/Login'
import SupplierMatching from './pages/SupplierMatching'
import Suppliers from './pages/Suppliers'
import SupplierProducts from './pages/SupplierProducts'
import ProductImport from './pages/ProductImport'
import Inventory from './pages/Inventory'

const AuthProviderWrapper: React.FC = () => {
  return (
    <AuthProvider>
      <Outlet />
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
    <Layout>
      <Outlet />
    </Layout>
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
              path: '*',
              element: <Navigate to="/" replace />,
            },
          ],
        },
      ],
    },
  ],
  {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    },
  }
)

function App() {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <AntApp>
          <RouterProvider
            router={router}
            future={{
              v7_startTransition: true,
            }}
          />
        </AntApp>
      </NotificationProvider>
    </ThemeProvider>
  )
}

export default App
