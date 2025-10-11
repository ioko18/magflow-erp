import React, { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { App } from 'antd';
import api from '../services/api';

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  role: string; // 'admin' | 'manager' | 'operator' | 'viewer'
  roles?: Array<{ id: number; name: string }>;
  permissions?: string[];
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loading: boolean; // Alias for isLoading
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const { message } = App.useApp();

  useEffect(() => {
    const initAuth = async () => {
      try {
        await checkAuth();
      } catch (error) {
        console.error('Auth initialization error:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await api.post('/auth/login', {
        username: email,
        password,
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const { access_token, refresh_token } = response.data;
      
      // Store the token in localStorage
      localStorage.setItem('access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }
      
      // Set the default Authorization header for all future requests
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      const authenticated = await checkAuth();

      if (!authenticated) {
        throw new Error('Unable to confirm authentication after login');
      }
      message.success('Login successful!');
      
      // Redirect to the dashboard or the page the user was trying to access
      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (error: any) {
      console.error('Login error:', error);
      message.error(error.response?.data?.detail || 'Login failed. Please try again.');
      throw error;
    }
  };

  const logout = () => {
    // Clear the token from localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    
    // Remove the Authorization header
    delete api.defaults.headers.common['Authorization'];
    
    setUser(null);
    message.success('Logged out successfully');
    navigate('/login');
  };

  const checkAuth = async (): Promise<boolean> => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      setUser(null);
      return false;
    }

    try {
      // Set the token in the headers for this request
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      // Fetch the current user
      const response = await api.get('/users/me');
      setUser(response.data);
      return true;
    } catch (error) {
      console.error('Auth check failed:', error);
      // If the token is invalid, clear it
      localStorage.removeItem('access_token');
      setUser(null);
      return false;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        loading: isLoading, // Alias
        login,
        logout,
        checkAuth,
      }}
    >
      {!isLoading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
