/**
 * Products API Service
 * 
 * Handles all product-related API calls
 */

import { apiClient } from '../apiClient';

export interface Product {
  id: number;
  name: string;
  sku: string;
  price: number;
  stock: number;
  category_id?: number;
  supplier_id?: number;
  chinese_name?: string;
  specifications?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ProductFilters {
  search?: string;
  category_id?: number;
  supplier_id?: number;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  page?: number;
  limit?: number;
}

export const productsApi = {
  /**
   * Get all products with optional filters
   */
  async getProducts(filters?: ProductFilters) {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    return await apiClient.get(`/products?${params.toString()}`);
  },

  /**
   * Get a single product by ID
   */
  async getProduct(id: number) {
    return await apiClient.get(`/products/${id}`);
  },

  /**
   * Create a new product
   */
  async createProduct(product: Partial<Product>) {
    return await apiClient.post('/products', product);
  },

  /**
   * Update an existing product
   */
  async updateProduct(id: number, product: Partial<Product>) {
    return await apiClient.put(`/products/${id}`, product);
  },

  /**
   * Delete a product
   */
  async deleteProduct(id: number) {
    return await apiClient.delete(`/products/${id}`);
  },

  /**
   * Bulk update products
   */
  async bulkUpdateProducts(updates: Array<{ id: number; data: Partial<Product> }>) {
    return await apiClient.post('/products/bulk-update', { updates });
  },

  /**
   * Import products from file
   */
  async importProducts(file: File, options?: { supplier_id?: number }) {
    return await apiClient.uploadFile('/products/import', file, options);
  },

  /**
   * Export products to Excel
   */
  async exportProducts(filters?: ProductFilters) {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    return await apiClient.get(`/products/export?${params.toString()}`);
  },
};
