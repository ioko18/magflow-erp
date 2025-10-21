import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { notification } from 'antd';
import { 
  CheckCircleOutlined, 
  ExclamationCircleOutlined, 
  InfoCircleOutlined, 
  CloseCircleOutlined
} from '@ant-design/icons';
import { notificationService, Notification as ApiNotification } from '../services/system/notificationService';
import { useAuth } from './AuthContext';

export interface NotificationItem {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  category: 'system' | 'emag' | 'orders' | 'users' | 'inventory' | 'sync' | 'payment' | 'shipping';
  priority: 'low' | 'medium' | 'high' | 'critical';
  actions?: Array<{
    label: string;
    action: () => void;
    type?: 'primary' | 'default' | 'danger';
  }>;
}

interface NotificationContextType {
  notifications: NotificationItem[];
  unreadCount: number;
  addNotification: (notification: Omit<NotificationItem, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  showToast: (type: 'success' | 'info' | 'warning' | 'error', title: string, message?: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [api, contextHolder] = notification.useNotification();
  const { isAuthenticated } = useAuth();

  // Convert API notification to NotificationItem
  const convertApiNotification = (apiNotif: ApiNotification): NotificationItem => ({
    id: apiNotif.id.toString(),
    type: apiNotif.type,
    title: apiNotif.title,
    message: apiNotif.message,
    timestamp: new Date(apiNotif.created_at),
    read: apiNotif.read,
    category: apiNotif.category,
    priority: apiNotif.priority,
  });

  // Load notifications from API when authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      setNotifications([]); // Clear notifications when not authenticated
      return;
    }

    const loadNotifications = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          console.log('No token available, skipping notification load');
          return;
        }
        
        const apiNotifications = await notificationService.getNotifications({ limit: 50 });
        setNotifications(apiNotifications.map(convertApiNotification));
      } catch (error: any) {
        // Only log if it's not an authentication error
        if (error?.response?.status !== 401) {
          console.error('Error loading notifications:', error);
        }
        // Silently fail - don't interrupt user experience
      }
    };

    // Small delay to ensure token is available
    const timer: ReturnType<typeof setTimeout> = setTimeout(loadNotifications, 100);
    return () => clearTimeout(timer);
  }, [isAuthenticated]);

  // Poll for new notifications every 30 seconds (only when authenticated)
  useEffect(() => {
    if (!isAuthenticated) return;

    let intervalId: ReturnType<typeof setInterval> | null = null;
    let consecutiveErrors = 0;
    const MAX_CONSECUTIVE_ERRORS = 3;

    const pollNotifications = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          console.log('No token available, stopping notification polling');
          if (intervalId) clearInterval(intervalId);
          return;
        }
        
        const apiNotifications = await notificationService.getNotifications({ limit: 50 });
        setNotifications(apiNotifications.map(convertApiNotification));
        consecutiveErrors = 0; // Reset error counter on success
      } catch (error: any) {
        consecutiveErrors++;
        
        // Stop polling after too many consecutive errors or on 401
        if (error?.response?.status === 401 || consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          console.log('Stopping notification polling due to authentication error or too many failures');
          if (intervalId) clearInterval(intervalId);
          return;
        }
        
        // Only log if it's not an authentication error
        if (error?.response?.status !== 401) {
          console.error('Error polling notifications:', error);
        }
      }
    };

    intervalId = setInterval(pollNotifications, 30000);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isAuthenticated]);

  const addNotification = useCallback((notificationData: Omit<NotificationItem, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: NotificationItem = {
      ...notificationData,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      read: false,
    };

    setNotifications(prev => [newNotification, ...prev.slice(0, 49)]); // Keep only last 50 notifications

    // Show toast notification
    showToast(newNotification.type, newNotification.title, newNotification.message);
  }, []);

  const markAsRead = useCallback(async (id: string) => {
    try {
      await notificationService.markAsRead(parseInt(id));
      setNotifications(prev => 
        prev.map(notification => 
          notification.id === id 
            ? { ...notification, read: true }
            : notification
        )
      );
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      await notificationService.markAllAsRead();
      setNotifications(prev => 
        prev.map(notification => ({ ...notification, read: true }))
      );
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  }, []);

  const removeNotification = useCallback(async (id: string) => {
    try {
      await notificationService.deleteNotification(parseInt(id));
      setNotifications(prev => prev.filter(notification => notification.id !== id));
    } catch (error) {
      console.error('Error removing notification:', error);
    }
  }, []);

  const clearAll = useCallback(async () => {
    try {
      await notificationService.deleteAllNotifications();
      setNotifications([]);
    } catch (error) {
      console.error('Error clearing all notifications:', error);
    }
  }, []);

  const showToast = useCallback((type: 'success' | 'info' | 'warning' | 'error', title: string, message?: string) => {
    const iconMap = {
      success: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      info: <InfoCircleOutlined style={{ color: '#1890ff' }} />,
      warning: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
      error: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
    };

    api[type]({
      message: title,
      description: message,
      icon: iconMap[type],
      duration: type === 'error' ? 6 : 4,
      placement: 'topRight',
      style: {
        marginTop: 70, // Account for header height
      },
    });
  }, [api]);

  const unreadCount = notifications.filter(n => !n.read).length;

  const value = {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    showToast,
  };

  return (
    <NotificationContext.Provider value={value}>
      {contextHolder}
      {children}
    </NotificationContext.Provider>
  );
};
