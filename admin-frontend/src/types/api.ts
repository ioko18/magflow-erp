/**
 * API request/response types
 */

// Generic API response
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
}

// Paginated response
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// List response
export interface ListResponse<T> {
  items: T[];
  total?: number;
}

// Error response
export interface ErrorResponse {
  status: 'error';
  message: string;
  errors?: Record<string, string[]>;
  code?: string;
}

// Upload response
export interface UploadResponse {
  filename: string;
  url: string;
  size: number;
}

// Bulk operation response
export interface BulkOperationResponse {
  success_count: number;
  error_count: number;
  errors?: Array<{
    id: number;
    error: string;
  }>;
}

// Import response
export interface ImportResponse {
  total: number;
  imported: number;
  updated: number;
  failed: number;
  errors?: Array<{
    row: number;
    error: string;
  }>;
}

// Export response (blob)
export type ExportResponse = Blob;

// Sync response
export interface SyncResponse {
  status: 'success' | 'partial' | 'failed';
  synced: number;
  failed: number;
  total: number;
  errors?: string[];
}

// eMAG Order Details
export interface EmagOrderDetails {
  id: string;
  emag_order_id: number;
  account_type: 'main' | 'fbe';
  status: number;
  status_name: string | null;
  customer_id?: number | null;
  customer_name: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  total_amount: number;
  currency: string;
  payment_method: string | null;
  payment_status?: number | null;
  delivery_mode: string | null;
  shipping_address?: {
    contact?: string;
    phone?: string;
    country?: string;
    city?: string;
    street?: string;
    postal_code?: string;
  } | null;
  billing_address?: {
    contact?: string;
    phone?: string;
    country?: string;
    city?: string;
    street?: string;
    postal_code?: string;
  } | null;
  products?: Array<{
    id?: string;
    sku: string;
    name: string;
    quantity: number;
    sale_price: number;
    price?: number;
    total?: number;
  }>;
  vouchers?: Array<{
    code: string;
    amount: number;
  }>;
  awb_number?: string | null;
  invoice_url?: string | null;
  order_date: string | null;
  acknowledged_at?: string | null;
  finalized_at?: string | null;
  sync_status: string;
  last_synced_at: string | null;
}
