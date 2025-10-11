/**
 * Centralized API Client
 * 
 * Provides type-safe API calls with automatic error handling and logging.
 */

import api from './api';
import { logError } from '../utils/errorLogger';

interface ApiResponse<T> {
  status: string;
  data: T;
  message?: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

class ApiClient {
  /**
   * GET request with error handling
   */
  async get<T>(url: string, params?: Record<string, any>): Promise<T> {
    try {
      const response = await api.get<ApiResponse<T>>(url, { params });
      return response.data.data;
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'GET', url });
      throw error;
    }
  }

  /**
   * POST request with error handling
   */
  async post<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await api.post<ApiResponse<T>>(url, data);
      return response.data.data;
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'POST', url });
      throw error;
    }
  }

  /**
   * PUT request with error handling
   */
  async put<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await api.put<ApiResponse<T>>(url, data);
      return response.data.data;
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'PUT', url });
      throw error;
    }
  }

  /**
   * PATCH request with error handling
   */
  async patch<T>(url: string, data?: any): Promise<T> {
    try {
      const response = await api.patch<ApiResponse<T>>(url, data);
      return response.data.data;
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'PATCH', url });
      throw error;
    }
  }

  /**
   * DELETE request with error handling
   */
  async delete<T>(url: string): Promise<T> {
    try {
      const response = await api.delete<ApiResponse<T>>(url);
      return response.data.data;
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'DELETE', url });
      throw error;
    }
  }

  /**
   * GET paginated data
   */
  async getPaginated<T>(
    url: string,
    page: number = 1,
    pageSize: number = 20,
    params?: Record<string, any>
  ): Promise<PaginatedResponse<T>> {
    try {
      const response = await api.get<ApiResponse<PaginatedResponse<T>>>(url, {
        params: {
          page,
          page_size: pageSize,
          ...params,
        },
      });
      return response.data.data;
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'GET_PAGINATED', url });
      throw error;
    }
  }

  /**
   * Upload file
   */
  async uploadFile<T>(url: string, file: File, additionalData?: Record<string, any>): Promise<T> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      if (additionalData) {
        Object.entries(additionalData).forEach(([key, value]) => {
          formData.append(key, String(value));
        });
      }

      const response = await api.post<ApiResponse<T>>(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      return response.data.data;
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'UPLOAD', url });
      throw error;
    }
  }

  /**
   * Download file
   */
  async downloadFile(url: string, filename: string): Promise<void> {
    try {
      const response = await api.get(url, {
        responseType: 'blob',
      });

      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      logError(error, { component: 'ApiClient', action: 'DOWNLOAD', url });
      throw error;
    }
  }
}

export const apiClient = new ApiClient();

// Convenience exports for common endpoints
export const performanceApi = {
  getOverview: () => apiClient.get('/performance/overview'),
  getEndpoints: (limit = 20) => apiClient.get('/performance/endpoints', { limit }),
  getSlowest: (limit = 10) => apiClient.get('/performance/slowest', { limit }),
  reset: () => apiClient.delete('/performance/reset'),
};

export const sessionApi = {
  getStatistics: () => apiClient.get('/sessions/statistics'),
  getActiveUsers: (minutes = 30) => apiClient.get('/sessions/active-users', { minutes }),
  getUserSessions: (userId: number) => apiClient.get(`/sessions/user/${userId}/sessions`),
  invalidateSession: (sessionId: string) => apiClient.delete(`/sessions/session/${sessionId}`),
  cleanup: (hours = 24) => apiClient.post('/sessions/cleanup', { hours }),
};

export const migrationApi = {
  getHealth: () => apiClient.get('/migrations/health'),
  getStatistics: () => apiClient.get('/migrations/statistics'),
  getSuggestions: () => apiClient.get('/migrations/suggestions'),
  createBackup: () => apiClient.post('/migrations/backup'),
  validate: () => apiClient.get('/migrations/validate'),
  getDashboard: () => apiClient.get('/migrations/dashboard'),
};
