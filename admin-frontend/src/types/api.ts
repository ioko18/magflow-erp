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
