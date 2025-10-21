/**
 * Suppliers API Service
 * 
 * Handles all supplier-related API calls
 */

import { apiClient } from '../apiClient';

export interface Supplier {
  id: number;
  name: string;
  code?: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SupplierProduct {
  id: number;
  supplier_id: number;
  product_id: number;
  supplier_sku: string;
  supplier_price: number;
  supplier_name?: string;
  chinese_name?: string;
  specifications?: Record<string, any>;
  is_matched?: boolean;
  confidence_score?: number;
}

export const suppliersApi = {
  /**
   * Get all suppliers
   */
  async getSuppliers(params?: { search?: string; is_active?: boolean }) {
    const queryParams = new URLSearchParams();
    if (params?.search) queryParams.append('search', params.search);
    if (params?.is_active !== undefined) queryParams.append('is_active', String(params.is_active));
    
    return await apiClient.get(`/suppliers?${queryParams.toString()}`);
  },

  /**
   * Get a single supplier by ID
   */
  async getSupplier(id: number) {
    return await apiClient.get(`/suppliers/${id}`);
  },

  /**
   * Create a new supplier
   */
  async createSupplier(supplier: Partial<Supplier>) {
    return await apiClient.post('/suppliers', supplier);
  },

  /**
   * Update an existing supplier
   */
  async updateSupplier(id: number, supplier: Partial<Supplier>) {
    return await apiClient.put(`/suppliers/${id}`, supplier);
  },

  /**
   * Delete a supplier
   */
  async deleteSupplier(id: number) {
    return await apiClient.delete(`/suppliers/${id}`);
  },

  /**
   * Get supplier products
   */
  async getSupplierProducts(supplierId: number, params?: { page?: number; limit?: number }) {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', String(params.page));
    if (params?.limit) queryParams.append('limit', String(params.limit));
    
    return await apiClient.get(`/suppliers/${supplierId}/products?${queryParams.toString()}`);
  },

  /**
   * Import supplier products
   */
  async importSupplierProducts(supplierId: number, file: File) {
    return await apiClient.uploadFile(`/suppliers/${supplierId}/import`, file);
  },

  /**
   * Match supplier products with catalog
   */
  async matchSupplierProducts(supplierId: number, options?: { auto_match?: boolean }) {
    return await apiClient.post(`/suppliers/${supplierId}/match`, options);
  },

  /**
   * Synchronize Chinese names for supplier products
   * Retroactively fixes products where Chinese name is in wrong field
   */
  async syncChineseNames(supplierId: number) {
    return await apiClient.post(`/suppliers/${supplierId}/products/sync-chinese-names`, {});
  },
};
