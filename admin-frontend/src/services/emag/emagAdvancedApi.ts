/**
 * eMAG Advanced API v4.4.9 Service
 * 
 * This service provides functions for the new eMAG API v4.4.9 features:
 * - Light Offer API for quick offer updates
 * - EAN matching for product discovery
 * - Measurements API for product dimensions
 * - Categories synchronization
 * - VAT rates and handling times
 */

import api from '../api';

// ========== Types ==========

export interface LightOfferUpdateRequest {
  product_id: number;
  account_type: 'main' | 'fbe';
  sale_price?: number;
  recommended_price?: number;
  min_sale_price?: number;
  max_sale_price?: number;
  stock_value?: number;
  warehouse_id?: number;
  handling_time_value?: number;
  vat_id?: number;
  status?: 0 | 1 | 2; // 0=inactive, 1=active, 2=end of life
  currency_type?: 'EUR' | 'PLN';
}

export interface EANSearchRequest {
  eans: string[];
  account_type: 'main' | 'fbe';
}

export interface EANSearchResult {
  ean: string;
  part_number_key: string;
  product_name: string;
  brand_name: string;
  category_name: string;
  doc_category_id: number;
  site_url?: string;
  allowed_to_add_offer: boolean;
  vendor_has_offer: boolean;
  hotness: string;
  product_image?: string;
}

export interface MeasurementsRequest {
  product_id: number;
  account_type: 'main' | 'fbe';
  length: number; // millimeters
  width: number; // millimeters
  height: number; // millimeters
  weight: number; // grams
}

export interface VATRate {
  vat_id: number;
  vat_rate: number;
  is_default?: boolean;
}

export interface HandlingTime {
  id: number;
}

export interface EmagCategory {
  id: number;
  name: string;
  is_allowed: number;
  parent_id?: number;
  is_ean_mandatory?: number;
  is_warranty_mandatory?: number;
  characteristics?: any[];
  family_types?: any[];
}

// ========== API Functions ==========

/**
 * Update existing offer using Light Offer API (v4.4.9)
 * 
 * This is the simplified endpoint for updating EXISTING offers only.
 * Much faster than the full product_offer/save endpoint.
 * 
 * @param data - Light offer update request
 * @returns API response with updated offer data
 */
export const updateOfferLight = async (data: LightOfferUpdateRequest) => {
  const response = await api.post('/emag/advanced/offers/update-light', data);
  return response.data;
};

/**
 * Search products by EAN codes (v4.4.9)
 * 
 * Quickly check if products already exist on eMAG before creating offers.
 * 
 * @param data - EAN search request with up to 100 EAN codes
 * @returns Matched products with offer information
 */
export const findProductsByEANs = async (data: EANSearchRequest): Promise<{
  status: string;
  message: string;
  data: {
    products: Record<string, { products: EANSearchResult[] }>;
    total: number;
    searched_eans: number;
  };
}> => {
  const response = await api.post('/emag/advanced/products/find-by-eans', data);
  return response.data;
};

/**
 * Save volume measurements (dimensions and weight) for a product
 * 
 * @param data - Measurements request
 * @returns API response
 */
export const saveProductMeasurements = async (data: MeasurementsRequest) => {
  const response = await api.post('/emag/advanced/products/measurements', data);
  return response.data;
};

/**
 * Get eMAG categories with characteristics and family types
 * 
 * @param accountType - Account type ('main' or 'fbe')
 * @param categoryId - Specific category ID for detailed info (optional)
 * @param page - Page number (default: 1)
 * @param itemsPerPage - Items per page (default: 100, max: 100)
 * @param language - Response language (default: 'ro')
 * @returns Categories data
 */
export const getEmagCategories = async (
  accountType: 'main' | 'fbe',
  categoryId?: number,
  page: number = 1,
  itemsPerPage: number = 100,
  language: string = 'ro'
): Promise<{
  status: string;
  message: string;
  data: {
    categories: EmagCategory[];
    total: number;
    page: number;
    items_per_page: number;
  };
}> => {
  const params: any = {
    account_type: accountType,
    page,
    items_per_page: itemsPerPage,
    language,
  };
  
  if (categoryId) {
    params.category_id = categoryId;
  }
  
  const response = await api.get('/emag/advanced/categories', { params });
  return response.data;
};

/**
 * Get available VAT rates from eMAG
 * 
 * @param accountType - Account type ('main' or 'fbe')
 * @returns VAT rates data
 */
export const getVATRates = async (accountType: 'main' | 'fbe'): Promise<{
  status: string;
  message: string;
  data: {
    vat_rates: VATRate[];
    total: number;
  };
}> => {
  const response = await api.get('/emag/advanced/vat-rates', {
    params: { account_type: accountType },
  });
  return response.data;
};

/**
 * Get available handling time values from eMAG
 * 
 * @param accountType - Account type ('main' or 'fbe')
 * @returns Handling times data
 */
export const getHandlingTimes = async (accountType: 'main' | 'fbe'): Promise<{
  status: string;
  message: string;
  data: {
    handling_times: HandlingTime[];
    total: number;
  };
}> => {
  const response = await api.get('/emag/advanced/handling-times', {
    params: { account_type: accountType },
  });
  return response.data;
};

/**
 * Batch update offers using Light API
 * 
 * @param offers - Array of light offer update requests
 * @returns Results for each offer update
 */
export const batchUpdateOffersLight = async (offers: LightOfferUpdateRequest[]) => {
  const results = await Promise.allSettled(
    offers.map(offer => updateOfferLight(offer))
  );
  
  return results.map((result, index) => ({
    product_id: offers[index].product_id,
    success: result.status === 'fulfilled',
    data: result.status === 'fulfilled' ? result.value : null,
    error: result.status === 'rejected' ? result.reason : null,
  }));
};

/**
 * Batch save measurements for multiple products
 * 
 * @param measurements - Array of measurement requests
 * @returns Results for each measurement save
 */
export const batchSaveMeasurements = async (measurements: MeasurementsRequest[]) => {
  const results = await Promise.allSettled(
    measurements.map(measurement => saveProductMeasurements(measurement))
  );
  
  return results.map((result, index) => ({
    product_id: measurements[index].product_id,
    success: result.status === 'fulfilled',
    data: result.status === 'fulfilled' ? result.value : null,
    error: result.status === 'rejected' ? result.reason : null,
  }));
};

export default {
  updateOfferLight,
  findProductsByEANs,
  saveProductMeasurements,
  getEmagCategories,
  getVATRates,
  getHandlingTimes,
  batchUpdateOffersLight,
  batchSaveMeasurements,
};
