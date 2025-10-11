/**
 * Status constants for various entities
 */

export const ORDER_STATUS = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  PROCESSING: 'processing',
  SHIPPED: 'shipped',
  DELIVERED: 'delivered',
  CANCELLED: 'cancelled',
  RETURNED: 'returned',
} as const;

export const PAYMENT_STATUS = {
  PENDING: 'pending',
  PAID: 'paid',
  FAILED: 'failed',
  REFUNDED: 'refunded',
} as const;

export const PRODUCT_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  OUT_OF_STOCK: 'out_of_stock',
  DISCONTINUED: 'discontinued',
} as const;

export const SYNC_STATUS = {
  IDLE: 'idle',
  SYNCING: 'syncing',
  SUCCESS: 'success',
  ERROR: 'error',
} as const;

export const MATCH_STATUS = {
  UNMATCHED: 'unmatched',
  PENDING: 'pending',
  MATCHED: 'matched',
  REJECTED: 'rejected',
} as const;

/**
 * Status colors for UI
 */
export const STATUS_COLORS = {
  // Order statuses
  pending: 'warning',
  confirmed: 'info',
  processing: 'primary',
  shipped: 'primary',
  delivered: 'success',
  cancelled: 'error',
  returned: 'warning',
  
  // Payment statuses
  paid: 'success',
  failed: 'error',
  refunded: 'warning',
  
  // Product statuses
  active: 'success',
  inactive: 'default',
  out_of_stock: 'warning',
  discontinued: 'error',
  
  // Sync statuses
  idle: 'default',
  syncing: 'primary',
  success: 'success',
  error: 'error',
  
  // Match statuses
  unmatched: 'default',
  matched: 'success',
  rejected: 'error',
} as const;

/**
 * Status labels (Romanian)
 */
export const STATUS_LABELS = {
  // Order statuses
  pending: 'În așteptare',
  confirmed: 'Confirmată',
  processing: 'În procesare',
  shipped: 'Expediată',
  delivered: 'Livrată',
  cancelled: 'Anulată',
  returned: 'Returnată',
  
  // Payment statuses
  paid: 'Plătită',
  failed: 'Eșuată',
  refunded: 'Rambursată',
  
  // Product statuses
  active: 'Activ',
  inactive: 'Inactiv',
  out_of_stock: 'Stoc epuizat',
  discontinued: 'Discontinuu',
  
  // Sync statuses
  idle: 'Inactiv',
  syncing: 'Sincronizare...',
  success: 'Succes',
  error: 'Eroare',
  
  // Match statuses
  unmatched: 'Nepotrivit',
  matched: 'Potrivit',
  rejected: 'Respins',
} as const;
