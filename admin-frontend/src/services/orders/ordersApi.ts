/**
 * Orders API Service
 * 
 * Handles all order-related API calls
 */

import { apiClient } from '../apiClient';

export interface Order {
  id: number;
  order_number: string;
  customer_id?: number;
  customer_name?: string;
  status: string;
  total_amount: number;
  payment_status?: string;
  shipping_address?: string;
  created_at?: string;
  updated_at?: string;
}

export interface OrderFilters {
  search?: string;
  status?: string;
  payment_status?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}

export const ordersApi = {
  /**
   * Get all orders with optional filters
   */
  async getOrders(filters?: OrderFilters) {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    return await apiClient.get(`/orders?${params.toString()}`);
  },

  /**
   * Get a single order by ID
   */
  async getOrder(id: number) {
    return await apiClient.get(`/orders/${id}`);
  },

  /**
   * Update order status
   */
  async updateOrderStatus(id: number, status: string) {
    return await apiClient.patch(`/orders/${id}/status`, { status });
  },

  /**
   * Cancel an order
   */
  async cancelOrder(id: number, reason?: string) {
    return await apiClient.post(`/orders/${id}/cancel`, { reason });
  },

  /**
   * Get order invoices
   */
  async getOrderInvoices(orderId: number) {
    return await apiClient.get(`/orders/${orderId}/invoices`);
  },
};
