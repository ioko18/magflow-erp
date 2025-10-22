/**
 * Type-Safe API Client for MagFlow ERP
 * 
 * This client provides type-safe access to the backend API using
 * TypeScript types generated from the OpenAPI schema.
 * 
 * Usage:
 *   import { apiClient } from '@/api/client';
 *   
 *   const products = await apiClient.products.list();
 *   const product = await apiClient.products.get(123);
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// When types are generated, uncomment this:
// import type { components, paths } from './types/api';

import type {
  Product,
  Order,
  Supplier,
} from '../types/models';

import type {
  CreatePurchaseOrderRequest,
  UpdatePurchaseOrderStatusRequest,
  ReceivePurchaseOrderRequest,
  ResolveUnreceivedItemRequest,
} from '../types/purchaseOrder';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Base API client configuration
 */
class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = API_BASE_URL) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 seconds
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Token expired, try to refresh
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            try {
              const response = await this.post<{ access_token: string; refresh_token: string }>('/auth/refresh', {
                refresh_token: refreshToken,
              });
              const newToken = response.data.access_token;
              localStorage.setItem('access_token', newToken);
              
              // Retry original request
              error.config.headers.Authorization = `Bearer ${newToken}`;
              return this.client.request(error.config);
            } catch (refreshError) {
              // Refresh failed, logout user
              localStorage.removeItem('access_token');
              localStorage.removeItem('refresh_token');
              window.location.href = '/login';
            }
          } else {
            // No refresh token, logout
            localStorage.removeItem('access_token');
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Generic GET request
   */
  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.get<T>(url, config);
  }

  /**
   * Generic POST request
   */
  async post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, config);
  }

  /**
   * Generic PUT request
   */
  async put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, config);
  }

  /**
   * Generic PATCH request
   */
  async patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(url, data, config);
  }

  /**
   * Generic DELETE request
   */
  async delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, config);
  }
}

// Create singleton instance
const baseClient = new APIClient();

/**
 * Products API
 */
export const productsAPI = {
  /**
   * List all products
   */
  list: async (params?: { skip?: number; limit?: number; search?: string }) => {
    const response = await baseClient.get('/products', { params });
    return response.data;
  },

  /**
   * Get a single product by ID
   */
  get: async (id: number) => {
    const response = await baseClient.get(`/products/${id}`);
    return response.data;
  },

  /**
   * Create a new product
   */
  create: async (data: Omit<Product, 'id' | 'created_at' | 'updated_at'>) => {
    const response = await baseClient.post('/products', data);
    return response.data;
  },

  /**
   * Update a product
   */
  update: async (id: number, data: Partial<Omit<Product, 'id' | 'created_at' | 'updated_at'>>) => {
    const response = await baseClient.put(`/products/${id}`, data);
    return response.data;
  },

  /**
   * Delete a product
   */
  delete: async (id: number) => {
    const response = await baseClient.delete(`/products/${id}`);
    return response.data;
  },
};

/**
 * Orders API
 */
export const ordersAPI = {
  list: async (params?: { skip?: number; limit?: number; status?: string }) => {
    const response = await baseClient.get('/orders', { params });
    return response.data;
  },

  get: async (id: number) => {
    const response = await baseClient.get(`/orders/${id}`);
    return response.data;
  },

  create: async (data: Omit<Order, 'id' | 'created_at' | 'updated_at'>) => {
    const response = await baseClient.post('/orders', data);
    return response.data;
  },

  update: async (id: number, data: Partial<Omit<Order, 'id' | 'created_at' | 'updated_at'>>) => {
    const response = await baseClient.put(`/orders/${id}`, data);
    return response.data;
  },
};

/**
 * Suppliers API
 */
export const suppliersAPI = {
  list: async (params?: { skip?: number; limit?: number }) => {
    const response = await baseClient.get('/suppliers', { params });
    return response.data;
  },

  get: async (id: number) => {
    const response = await baseClient.get(`/suppliers/${id}`);
    return response.data;
  },

  create: async (data: Omit<Supplier, 'id' | 'created_at' | 'updated_at'>) => {
    const response = await baseClient.post('/suppliers', data);
    return response.data;
  },

  update: async (id: number, data: Partial<Omit<Supplier, 'id' | 'created_at' | 'updated_at'>>) => {
    const response = await baseClient.put(`/suppliers/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    const response = await baseClient.delete(`/suppliers/${id}`);
    return response.data;
  },
};

/**
 * eMAG API
 */
export const emagAPI = {
  products: {
    sync: async () => {
      const response = await baseClient.post('/emag/sync/products');
      return response.data;
    },
    
    list: async (params?: { page?: number; itemsPerPage?: number }) => {
      const response = await baseClient.get('/emag/products', { params });
      return response.data;
    },
  },

  orders: {
    sync: async () => {
      const response = await baseClient.post('/emag/sync/orders');
      return response.data;
    },
    
    list: async (params?: { page?: number; itemsPerPage?: number }) => {
      const response = await baseClient.get('/emag/orders', { params });
      return response.data;
    },
  },
};

/**
 * Auth API
 */
export const authAPI = {
  login: async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await baseClient.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  logout: async () => {
    const response = await baseClient.post('/auth/logout');
    return response.data;
  },

  me: async () => {
    const response = await baseClient.get('/users/me');
    return response.data;
  },

  refresh: async (refreshToken: string) => {
    const response = await baseClient.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },
};

/**
 * Purchase Orders API
 */
export const purchaseOrdersAPI = {
  list: async (params?: { skip?: number; limit?: number; status?: string; supplier_id?: number; search?: string }) => {
    const response = await baseClient.get('/purchase-orders', { params });
    return response.data;
  },

  get: async (id: number) => {
    const response = await baseClient.get(`/purchase-orders/${id}`);
    return response.data;
  },

  create: async (data: CreatePurchaseOrderRequest) => {
    const response = await baseClient.post('/purchase-orders', data);
    return response.data;
  },

  updateStatus: async (id: number, data: UpdatePurchaseOrderStatusRequest) => {
    const response = await baseClient.patch(`/purchase-orders/${id}/status`, data);
    return response.data;
  },

  receive: async (id: number, data: ReceivePurchaseOrderRequest) => {
    const response = await baseClient.post(`/purchase-orders/${id}/receive`, data);
    return response.data;
  },

  getHistory: async (id: number) => {
    const response = await baseClient.get(`/purchase-orders/${id}/history`);
    return response.data;
  },

  getUnreceivedItems: async (params?: { skip?: number; limit?: number; status?: string }) => {
    const response = await baseClient.get('/purchase-orders/unreceived-items/list', { params });
    return response.data;
  },

  resolveUnreceivedItem: async (itemId: number, data: ResolveUnreceivedItemRequest) => {
    const response = await baseClient.patch(`/purchase-orders/unreceived-items/${itemId}/resolve`, data);
    return response.data;
  },

  getSupplierStatistics: async (supplierId: number) => {
    const response = await baseClient.get(`/purchase-orders/statistics/by-supplier/${supplierId}`);
    return response.data;
  },

  getPendingOrdersForProduct: async (productId: number) => {
    const response = await baseClient.get(`/purchase-orders/products/${productId}/pending-orders`);
    return response.data;
  },
};

/**
 * Combined API client
 */
export const apiClient = {
  products: productsAPI,
  orders: ordersAPI,
  suppliers: suppliersAPI,
  emag: emagAPI,
  auth: authAPI,
  purchaseOrders: purchaseOrdersAPI,
  
  // Direct access to base client for custom requests
  raw: baseClient,
};

export default apiClient;
