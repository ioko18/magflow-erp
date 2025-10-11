/**
 * Unified Products API Service
 * 
 * Provides functions to interact with the unified products endpoint
 * that combines eMAG (MAIN + FBE) and local products.
 */

import api from '../api';

export interface UnifiedProduct {
  id: string;
  sku: string;
  name: string;
  source: 'emag_main' | 'emag_fbe' | 'local';
  account_type: string;
  price?: number;
  currency?: string;
  stock_quantity?: number;
  is_active: boolean;
  status: string;
  brand?: string;
  category_name?: string;
  last_synced_at?: string;
  sync_status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface UnifiedProductsResponse {
  products: UnifiedProduct[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
  };
  statistics: {
    total: number;
    emag_main: number;
    emag_fbe: number;
    local: number;
  };
  filters: {
    source: string;
    search?: string;
    is_active?: boolean;
  };
  timestamp: string;
}

export interface GetUnifiedProductsParams {
  page?: number;
  page_size?: number;
  source?: 'all' | 'emag_main' | 'emag_fbe' | 'local';
  search?: string;
  is_active?: boolean;
}

/**
 * Fetch unified products from all sources (eMAG + local)
 */
export async function getUnifiedProducts(
  params: GetUnifiedProductsParams = {}
): Promise<UnifiedProductsResponse> {
  const {
    page = 1,
    page_size = 50,
    source = 'all',
    search,
    is_active,
  } = params;

  const response = await api.get<UnifiedProductsResponse>(
    '/emag/enhanced/products/unified/all',
    {
      params: {
        page,
        page_size,
        source,
        search: search || undefined,
        is_active: is_active !== undefined ? is_active : undefined,
      },
    }
  );

  return response.data;
}

/**
 * Get product statistics across all sources
 */
export async function getProductStatistics(): Promise<{
  total: number;
  emag_main: number;
  emag_fbe: number;
  local: number;
}> {
  const response = await getUnifiedProducts({ page: 1, page_size: 1 });
  return response.statistics;
}

/**
 * Search products across all sources
 */
export async function searchProducts(
  searchTerm: string,
  source: 'all' | 'emag_main' | 'emag_fbe' | 'local' = 'all'
): Promise<UnifiedProduct[]> {
  const response = await getUnifiedProducts({
    search: searchTerm,
    source,
    page_size: 100, // Get more results for search
  });
  return response.products;
}

/**
 * Get products by source type
 */
export async function getProductsBySource(
  source: 'emag_main' | 'emag_fbe' | 'local',
  page: number = 1,
  pageSize: number = 50
): Promise<UnifiedProductsResponse> {
  return getUnifiedProducts({
    source,
    page,
    page_size: pageSize,
  });
}

/**
 * Get active products only
 */
export async function getActiveProducts(
  page: number = 1,
  pageSize: number = 50
): Promise<UnifiedProductsResponse> {
  return getUnifiedProducts({
    is_active: true,
    page,
    page_size: pageSize,
  });
}

/**
 * Get inactive products only
 */
export async function getInactiveProducts(
  page: number = 1,
  pageSize: number = 50
): Promise<UnifiedProductsResponse> {
  return getUnifiedProducts({
    is_active: false,
    page,
    page_size: pageSize,
  });
}

export default {
  getUnifiedProducts,
  getProductStatistics,
  searchProducts,
  getProductsBySource,
  getActiveProducts,
  getInactiveProducts,
};
