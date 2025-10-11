/**
 * Notification Service
 * 
 * Handles all API calls related to notifications and notification settings.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface Notification {
  id: number;
  user_id: number;
  type: 'success' | 'info' | 'warning' | 'error';
  category: 'system' | 'emag' | 'orders' | 'users' | 'inventory' | 'sync' | 'payment' | 'shipping';
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  data?: any;
  action_url?: string;
  action_label?: string;
  read: boolean;
  read_at?: string;
  created_at: string;
  expires_at?: string;
}

export interface NotificationSettings {
  id: number;
  user_id: number;
  enabled: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  category_preferences: Record<string, Record<string, boolean>>;
  min_priority: 'low' | 'medium' | 'high' | 'critical';
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  auto_delete_enabled: boolean;
  auto_delete_days: number;
  digest_enabled: boolean;
  digest_frequency: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationStatistics {
  total: number;
  unread: number;
  read: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
}

class NotificationService {
  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('No authentication token found');
    }
    return {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    };
  }

  /**
   * Get all notifications for the current user
   */
  async getNotifications(params?: {
    unread_only?: boolean;
    category?: string;
    priority?: string;
    limit?: number;
    offset?: number;
  }): Promise<Notification[]> {
    const response = await axios.get(
      `${API_BASE_URL}/notifications/`,
      {
        ...this.getAuthHeaders(),
        params,
      }
    );
    return response.data;
  }

  /**
   * Get unread notification count
   */
  async getUnreadCount(): Promise<number> {
    const response = await axios.get(
      `${API_BASE_URL}/notifications/unread-count`,
      this.getAuthHeaders()
    );
    return response.data.unread_count;
  }

  /**
   * Get notification statistics
   */
  async getStatistics(): Promise<NotificationStatistics> {
    const response = await axios.get(
      `${API_BASE_URL}/notifications/statistics`,
      this.getAuthHeaders()
    );
    return response.data;
  }

  /**
   * Get a specific notification by ID
   */
  async getNotification(id: number): Promise<Notification> {
    const response = await axios.get(
      `${API_BASE_URL}/notifications/${id}`,
      this.getAuthHeaders()
    );
    return response.data;
  }

  /**
   * Mark a notification as read
   */
  async markAsRead(id: number): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/notifications/${id}/read`,
      {},
      this.getAuthHeaders()
    );
  }

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(): Promise<{ count: number }> {
    const response = await axios.post(
      `${API_BASE_URL}/notifications/mark-all-read`,
      {},
      this.getAuthHeaders()
    );
    return response.data;
  }

  /**
   * Delete a notification
   */
  async deleteNotification(id: number): Promise<void> {
    await axios.delete(
      `${API_BASE_URL}/notifications/${id}`,
      this.getAuthHeaders()
    );
  }

  /**
   * Delete all notifications
   */
  async deleteAllNotifications(): Promise<{ count: number }> {
    const response = await axios.delete(
      `${API_BASE_URL}/notifications/`,
      this.getAuthHeaders()
    );
    return response.data;
  }

  /**
   * Get notification settings for the current user
   */
  async getSettings(): Promise<NotificationSettings> {
    const response = await axios.get(
      `${API_BASE_URL}/notifications/settings/me`,
      this.getAuthHeaders()
    );
    return response.data;
  }

  /**
   * Update notification settings
   */
  async updateSettings(settings: Partial<NotificationSettings>): Promise<NotificationSettings> {
    const response = await axios.put(
      `${API_BASE_URL}/notifications/settings/me`,
      settings,
      this.getAuthHeaders()
    );
    return response.data;
  }

  /**
   * Reset notification settings to defaults
   */
  async resetSettings(): Promise<NotificationSettings> {
    const response = await axios.post(
      `${API_BASE_URL}/notifications/settings/reset`,
      {},
      this.getAuthHeaders()
    );
    return response.data.settings;
  }

  /**
   * Create a new notification (admin only or for self)
   */
  async createNotification(notification: {
    title: string;
    message: string;
    type?: 'success' | 'info' | 'warning' | 'error';
    category?: string;
    priority?: string;
    data?: any;
    action_url?: string;
    action_label?: string;
  }): Promise<Notification> {
    const response = await axios.post(
      `${API_BASE_URL}/notifications/create`,
      notification,
      this.getAuthHeaders()
    );
    return response.data;
  }
}

export const notificationService = new NotificationService();
export default notificationService;
