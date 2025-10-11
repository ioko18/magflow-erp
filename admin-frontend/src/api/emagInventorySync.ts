/**
 * eMag Inventory Synchronization API
 * 
 * API client for syncing eMag FBE stock to inventory_items
 */

import apiClient from './client';

export interface SyncStats {
  warehouse_created: boolean;
  products_synced: number;
  created: number;
  updated: number;
  errors: number;
  low_stock_count: number;
}

export interface SyncResponse {
  success: boolean;
  message: string;
  account_type: string;
  async_mode: boolean;
  stats?: SyncStats;
}

export interface SyncStatusResponse {
  warehouse_exists: boolean;
  message?: string;
  warehouse?: {
    id: number;
    name: string;
    code: string;
  };
  statistics?: {
    total_items: number;
    total_quantity: number;
    out_of_stock: number;
    critical: number;
    low_stock: number;
    needs_reorder: number;
  };
}

/**
 * Sync eMag FBE stock to inventory_items
 */
export const syncEmagInventory = async (
  accountType: string = 'fbe',
  asyncMode: boolean = false
): Promise<SyncResponse> => {
  const response = await apiClient.raw.post<SyncResponse>(
    '/inventory/emag-inventory-sync/sync',
    null,
    {
      params: {
        account_type: accountType,
        async_mode: asyncMode,
      },
    }
  );
  return response.data;
};

/**
 * Get current eMag inventory sync status
 */
export const getEmagInventorySyncStatus = async (): Promise<SyncStatusResponse> => {
  const response = await apiClient.raw.get<SyncStatusResponse>(
    '/inventory/emag-inventory-sync/status'
  );
  return response.data;
};
