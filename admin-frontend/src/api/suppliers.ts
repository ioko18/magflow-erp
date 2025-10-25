/**
 * Suppliers API Service
 * Handles all supplier-related API calls including price updates
 */

import apiClient from './client';

export interface SupplierProductUpdateData {
  supplier_price?: number;
  supplier_product_name?: string;
  supplier_product_chinese_name?: string | null;
  supplier_product_url?: string;
  supplier_currency?: string;
  supplier_product_specification?: string | null;
}

export interface ApiResponse<T> {
  status: string;
  data: T;
  message?: string;
}

export const suppliersApi = {
  /**
   * Update supplier product details (price, name, URL, currency)
   */
  updateSupplierProduct: async (
    supplierId: number,
    productId: number,
    updateData: SupplierProductUpdateData
  ) => {
    const response = await apiClient.raw.patch<ApiResponse<{
      message: string;
      product_id: number;
      updated_fields: string[];
    }>>(`/suppliers/${supplierId}/products/${productId}`, updateData);
    return response.data;
  },

  /**
   * Update supplier product price from Google Sheets
   */
  updateSheetSupplierPrice: async (
    sheetId: number,
    newPrice: number
  ) => {
    const response = await apiClient.raw.patch<ApiResponse<{
      message: string;
      sheet_id: number;
      updated_price: number;
      updated_fields: string[];
    }>>(`/suppliers/sheets/${sheetId}`, {
      price_cny: newPrice
    });
    return response.data;
  },

  /**
   * Update supplier sheet specification from Google Sheets
   */
  updateSheetSupplierSpecification: async (
    sheetId: number,
    specification: string | null
  ) => {
    const response = await apiClient.raw.patch<ApiResponse<{
      message: string;
      sheet_id: number;
      updated_fields: string[];
    }>>(`/suppliers/sheets/${sheetId}`, {
      supplier_product_specification: specification
    });
    return response.data;
  },

  /**
   * Update supplier sheet chinese name from Google Sheets
   */
  updateSheetSupplierChineseName: async (
    sheetId: number,
    chineseName: string | null
  ) => {
    const response = await apiClient.raw.patch<ApiResponse<{
      message: string;
      sheet_id: number;
      updated_fields: string[];
    }>>(`/suppliers/sheets/${sheetId}`, {
      supplier_product_chinese_name: chineseName
    });
    return response.data;
  },
};

export const {
  updateSupplierProduct,
  updateSheetSupplierPrice,
  updateSheetSupplierSpecification,
  updateSheetSupplierChineseName,
} = suppliersApi;
