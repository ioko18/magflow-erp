/**
 * Application configuration
 */

import { env } from './env';

export const APP_CONFIG = {
  // Application info
  name: 'MagFlow ERP',
  version: '1.0.0',
  
  // API configuration
  api: {
    baseURL: env.apiUrl,
    timeout: env.apiTimeout,
  },
  
  // Pagination defaults
  pagination: {
    defaultPageSize: 20,
    pageSizeOptions: [10, 20, 50, 100],
  },
  
  // Table configuration
  table: {
    defaultPageSize: 20,
    stickyHeader: true,
  },
  
  // File upload
  upload: {
    maxFileSize: 10 * 1024 * 1024, // 10MB
    acceptedFormats: ['.xlsx', '.xls', '.csv'],
  },
  
  // Debounce delays
  debounce: {
    search: 500,
    input: 300,
  },
  
  // Auto-refresh intervals (ms)
  refresh: {
    dashboard: 30000,
    orders: 60000,
    inventory: 120000,
  },
  
  // Date formats
  dateFormats: {
    display: 'DD.MM.YYYY',
    displayWithTime: 'DD.MM.YYYY HH:mm',
    api: 'YYYY-MM-DD',
  },
  
  // Notification duration (ms)
  notification: {
    success: 3000,
    error: 5000,
    warning: 4000,
    info: 3000,
  },
  
  // Feature flags
  features: {
    enableEmagSync: true,
    enableProductMatching: true,
    enableSupplierImport: true,
    enableAdvancedFilters: true,
    enableBulkOperations: true,
  },
} as const;

/**
 * Environment helpers
 */
export const isDevelopment = import.meta.env.DEV;
export const isProduction = import.meta.env.PROD;
export const apiBaseURL = APP_CONFIG.api.baseURL;
