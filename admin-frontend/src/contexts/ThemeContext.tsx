import React, { createContext, useContext, useState, useEffect } from 'react';
import { ConfigProvider, theme } from 'antd';

interface ThemeContextType {
  isDarkMode: boolean;
  toggleTheme: () => void;
  themeConfig: any;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('magflow-theme');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    localStorage.setItem('magflow-theme', JSON.stringify(isDarkMode));
    // Update CSS custom properties for theme
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  const lightTheme = {
    token: {
      colorPrimary: '#1890ff',
      borderRadius: 6,
      colorBgContainer: '#ffffff',
      colorBgElevated: '#ffffff',
      colorBgLayout: '#f5f5f5',
      colorText: '#000000d9',
      colorTextSecondary: '#00000073',
      colorBorder: '#d9d9d9',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
    },
    components: {
      Layout: {
        bodyBg: '#f5f5f5',
        headerBg: '#ffffff',
        siderBg: '#001529',
      },
      Menu: {
        darkItemBg: '#001529',
        darkItemSelectedBg: '#1890ff',
        darkItemHoverBg: '#1890ff20',
      },
      Card: {
        colorBgContainer: '#ffffff',
        boxShadowTertiary: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)',
      },
      Table: {
        colorBgContainer: '#ffffff',
        headerBg: '#fafafa',
      }
    }
  };

  const darkTheme = {
    algorithm: theme.darkAlgorithm,
    token: {
      colorPrimary: '#1890ff',
      borderRadius: 6,
      colorBgContainer: '#1f1f1f',
      colorBgElevated: '#262626',
      colorBgLayout: '#141414',
      colorText: '#ffffffd9',
      colorTextSecondary: '#ffffff73',
      colorBorder: '#424242',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.45)',
    },
    components: {
      Layout: {
        bodyBg: '#141414',
        headerBg: '#1f1f1f',
        siderBg: '#001529',
      },
      Menu: {
        darkItemBg: '#001529',
        darkItemSelectedBg: '#1890ff',
        darkItemHoverBg: '#1890ff20',
      },
      Card: {
        colorBgContainer: '#1f1f1f',
        boxShadowTertiary: '0 1px 2px 0 rgba(0, 0, 0, 0.16), 0 1px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px 0 rgba(0, 0, 0, 0.09)',
      },
      Table: {
        colorBgContainer: '#1f1f1f',
        headerBg: '#262626',
      },
      Input: {
        colorBgContainer: '#262626',
      },
      Select: {
        colorBgContainer: '#262626',
      }
    }
  };

  const themeConfig = isDarkMode ? darkTheme : lightTheme;

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleTheme, themeConfig }}>
      <ConfigProvider theme={themeConfig}>
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
};
