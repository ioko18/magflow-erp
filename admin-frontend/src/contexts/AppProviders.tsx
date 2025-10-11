/**
 * App Providers
 * 
 * Centralized provider wrapper for all React contexts
 */

import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { App as AntdApp, ConfigProvider } from 'antd';
import roRO from 'antd/locale/ro_RO';
import { AuthProvider } from './AuthContext';
import { NotificationProvider } from './NotificationContext';
import { ThemeProvider } from './ThemeContext';

interface AppProvidersProps {
  children: React.ReactNode;
}

/**
 * Ant Design theme configuration
 */
const antdTheme = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    borderRadius: 6,
    fontSize: 14,
  },
};

/**
 * Centralized provider wrapper
 * 
 * Wraps the app with all necessary providers in the correct order:
 * 1. BrowserRouter - Routing
 * 2. ConfigProvider - Ant Design configuration
 * 3. AntdApp - Ant Design App component (message, notification, modal)
 * 4. ThemeProvider - Custom theme context
 * 5. AuthProvider - Authentication context
 * 6. NotificationProvider - Notification context
 */
export const AppProviders: React.FC<AppProvidersProps> = ({ children }) => {
  return (
    <BrowserRouter>
      <ConfigProvider locale={roRO} theme={antdTheme}>
        <AntdApp>
          <ThemeProvider>
            <AuthProvider>
              <NotificationProvider>
                {children}
              </NotificationProvider>
            </AuthProvider>
          </ThemeProvider>
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
};

/**
 * Usage in main.tsx:
 * 
 * import { AppProviders } from './contexts/AppProviders';
 * 
 * ReactDOM.createRoot(document.getElementById('root')!).render(
 *   <React.StrictMode>
 *     <AppProviders>
 *       <App />
 *     </AppProviders>
 *   </React.StrictMode>
 * );
 */
