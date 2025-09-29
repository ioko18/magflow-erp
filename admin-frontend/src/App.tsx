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
import EmagSync from './pages/EmagSync'
import Products from './pages/Products'
import Orders from './pages/Orders'
import Customers from './pages/Customers'
import Users from './pages/Users'
import Settings from './pages/Settings'
import Login from './pages/Login'

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
              element: <EmagSync />,
            },
            {
              path: 'products',
              element: <Products />,
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
