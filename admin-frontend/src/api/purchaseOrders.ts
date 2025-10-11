/**
 * Purchase Orders API Client
 * Handles all API calls for the Purchase Orders system
 * 
 * FIXED: Now uses the centralized APIClient with proper authentication
 */

import { apiClient } from './client';
import type {
  PurchaseOrder,
  PurchaseOrderListParams,
  CreatePurchaseOrderRequest,
  UpdatePurchaseOrderStatusRequest,
  ReceivePurchaseOrderRequest,
  UnreceivedItem,
  UnreceivedItemsListParams,
  ResolveUnreceivedItemRequest,
  PurchaseOrderHistory,
  SupplierStatistics,
  PendingOrder,
  ApiResponse,
} from '../types/purchaseOrder';

export const purchaseOrdersApi = {
  /**
   * List purchase orders with optional filters
   */
  list: async (params?: PurchaseOrderListParams) => {
    const response = await apiClient.raw.get<ApiResponse<{
      orders: PurchaseOrder[];
      pagination: {
        total: number;
        skip: number;
        limit: number;
        has_more: boolean;
      };
    }>>('/purchase-orders', { params });
    return response.data;
  },

  /**
   * Create a new purchase order
   */
  create: async (data: CreatePurchaseOrderRequest) => {
    const response = await apiClient.raw.post<ApiResponse<{
      id: number;
      order_number: string;
      message: string;
    }>>('/purchase-orders', data);
    return response.data;
  },

  /**
   * Get purchase order details by ID
   */
  get: async (id: number) => {
    const response = await apiClient.raw.get<ApiResponse<{
      purchase_order: PurchaseOrder;
    }>>(`/purchase-orders/${id}`);
    return response.data;
  },

  /**
   * Update purchase order status
   */
  updateStatus: async (id: number, data: UpdatePurchaseOrderStatusRequest) => {
    const response = await apiClient.raw.patch<ApiResponse<{
      id: number;
      order_number: string;
      status: string;
      message: string;
    }>>(`/purchase-orders/${id}/status`, data);
    return response.data;
  },

  /**
   * Receive purchase order items
   */
  receive: async (id: number, data: ReceivePurchaseOrderRequest) => {
    const response = await apiClient.raw.post<ApiResponse<{
      receipt_id: number;
      receipt_number: string;
      total_received_quantity: number;
      message: string;
    }>>(`/purchase-orders/${id}/receive`, data);
    return response.data;
  },

  /**
   * Get purchase order history
   */
  getHistory: async (id: number) => {
    const response = await apiClient.raw.get<ApiResponse<{
      history: PurchaseOrderHistory[];
    }>>(`/purchase-orders/${id}/history`);
    return response.data;
  },

  /**
   * List unreceived items
   */
  getUnreceivedItems: async (params?: UnreceivedItemsListParams) => {
    const response = await apiClient.raw.get<ApiResponse<{
      items: UnreceivedItem[];
      pagination: {
        total: number;
        skip: number;
        limit: number;
        has_more: boolean;
      };
    }>>('/purchase-orders/unreceived-items/list', { params });
    return response.data;
  },

  /**
   * Resolve an unreceived item
   */
  resolveUnreceivedItem: async (itemId: number, data: ResolveUnreceivedItemRequest) => {
    const response = await apiClient.raw.patch<ApiResponse<{
      id: number;
      status: string;
      message: string;
    }>>(`/purchase-orders/unreceived-items/${itemId}/resolve`, data);
    return response.data;
  },

  /**
   * Get supplier order statistics
   */
  getSupplierStatistics: async (supplierId: number) => {
    const response = await apiClient.raw.get<ApiResponse<SupplierStatistics>>(
      `/purchase-orders/statistics/by-supplier/${supplierId}`
    );
    return response.data;
  },

  /**
   * Get pending orders for a specific product
   */
  getPendingOrdersForProduct: async (productId: number) => {
    const response = await apiClient.raw.get<ApiResponse<{
      product_id: number;
      pending_orders: PendingOrder[];
      total_pending_quantity: number;
    }>>(`/purchase-orders/products/${productId}/pending-orders`);
    return response.data;
  },

  /**
   * Bulk create purchase order drafts from low stock supplier selections
   */
  bulkCreateDrafts: async (selectedProducts: Array<{
    product_id: number;
    sku: string;
    supplier_id: string;
    supplier_name: string;
    reorder_quantity: number;
  }>) => {
    const response = await apiClient.raw.post<ApiResponse<{
      created_orders: Array<{
        id: number;
        order_number: string;
        supplier_name: string;
        supplier_id: number;
        total_products: number;
        total_quantity: number;
        status: string;
      }>;
      total_orders_created: number;
      errors: Array<{ supplier: string; error: string }>;
      message: string;
    }>>('/purchase-orders/bulk-create-drafts', {
      selected_products: selectedProducts
    });
    return response.data;
  },
};

// Export individual functions for convenience
export const {
  list: listPurchaseOrders,
  create: createPurchaseOrder,
  get: getPurchaseOrder,
  updateStatus: updatePurchaseOrderStatus,
  receive: receivePurchaseOrder,
  getHistory: getPurchaseOrderHistory,
  getUnreceivedItems,
  resolveUnreceivedItem,
  getSupplierStatistics,
  getPendingOrdersForProduct,
  bulkCreateDrafts,
} = purchaseOrdersApi;

export default purchaseOrdersApi;
