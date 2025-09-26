import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { notification } from 'antd';
import { 
  CheckCircleOutlined, 
  ExclamationCircleOutlined, 
  InfoCircleOutlined, 
  CloseCircleOutlined
} from '@ant-design/icons';

export interface NotificationItem {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  category: 'system' | 'emag' | 'orders' | 'users' | 'inventory';
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

  // Load notifications from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('magflow-notifications');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setNotifications(parsed.map((n: any) => ({
          ...n,
          timestamp: new Date(n.timestamp)
        })));
      } catch (error) {
        console.error('Error loading notifications:', error);
      }
    }
  }, []);

  // Save notifications to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('magflow-notifications', JSON.stringify(notifications));
  }, [notifications]);

  // Simulate real-time notifications
  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate random notifications for demo
      const randomNotifications = [
        {
          type: 'info' as const,
          title: 'eMAG Sync Complete',
          message: '1,275 products synchronized successfully',
          category: 'emag' as const,
          priority: 'medium' as const,
        },
        {
          type: 'warning' as const,
          title: 'Low Stock Alert',
          message: '3 products are running low on stock',
          category: 'inventory' as const,
          priority: 'high' as const,
        },
        {
          type: 'success' as const,
          title: 'New Order Received',
          message: 'Order #000123 from John Doe - 299.99 RON',
          category: 'orders' as const,
          priority: 'medium' as const,
        },
        {
          type: 'error' as const,
          title: 'System Error',
          message: 'Database connection timeout detected',
          category: 'system' as const,
          priority: 'critical' as const,
        }
      ];

      // 10% chance to add a notification every 30 seconds
      if (Math.random() < 0.1) {
        const randomNotification = randomNotifications[Math.floor(Math.random() * randomNotifications.length)];
        addNotification(randomNotification);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

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

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === id 
          ? { ...notification, read: true }
          : notification
      )
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(notification => ({ ...notification, read: true }))
    );
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
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
