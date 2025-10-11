/**
 * Application routes constants
 */

export const ROUTES = {
  // Auth
  LOGIN: '/login',
  
  // Dashboard
  DASHBOARD: '/',
  
  // Products
  PRODUCTS: '/products',
  PRODUCT_IMPORT: '/products/import',
  PRODUCT_MATCHING: '/products/matching',
  INVENTORY: '/inventory',
  
  // Suppliers
  SUPPLIERS: '/suppliers',
  SUPPLIER_MATCHING: '/suppliers/matching',
  SUPPLIER_PRODUCTS: '/suppliers/:id/products',
  SUPPLIER_PRODUCTS_SHEET: '/suppliers/:id/sheet',
  
  // Orders
  ORDERS: '/orders',
  CUSTOMERS: '/customers',
  
  // eMAG
  EMAG_AWB: '/emag/awb',
  EMAG_ADDRESSES: '/emag/addresses',
  EMAG_EAN: '/emag/ean',
  EMAG_INVOICES: '/emag/invoices',
  EMAG_PRODUCT_PUBLISHING: '/emag/products/publishing',
  EMAG_PRODUCT_SYNC: '/emag/products/sync',
  EMAG_PRODUCT_SYNC_V2: '/emag/products/sync-v2',
  
  // System
  SETTINGS: '/settings',
  USERS: '/users',
  NOTIFICATIONS: '/notifications',
} as const;

/**
 * Helper to build route with params
 */
export const buildRoute = (route: string, params: Record<string, string | number>): string => {
  let result = route;
  for (const [key, value] of Object.entries(params)) {
    result = result.replace(`:${key}`, String(value));
  }
  return result;
};
