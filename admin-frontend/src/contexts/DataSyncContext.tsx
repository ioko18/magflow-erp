/**
 * Data Synchronization Context
 * 
 * Provides a global mechanism to synchronize data updates across different pages.
 * When data is updated in one page (e.g., SupplierProducts), other pages (e.g., LowStockSuppliers)
 * can automatically refresh their data.
 * 
 * Usage:
 * 1. Wrap your app with <DataSyncProvider>
 * 2. Call triggerSupplierProductsUpdate() after updating supplier products
 * 3. Listen to supplierProductsLastUpdate in useEffect to reload data
 */

import React, { createContext, useContext, useState, useCallback } from 'react';

interface DataSyncContextType {
  supplierProductsLastUpdate: number;
  triggerSupplierProductsUpdate: () => void;
  lowStockProductsLastUpdate: number;
  triggerLowStockProductsUpdate: () => void;
  productsLastUpdate: number;
  triggerProductsUpdate: () => void;
}

const DataSyncContext = createContext<DataSyncContextType | undefined>(undefined);

export const DataSyncProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [supplierProductsLastUpdate, setSupplierProductsLastUpdate] = useState(Date.now());
  const [lowStockProductsLastUpdate, setLowStockProductsLastUpdate] = useState(Date.now());
  const [productsLastUpdate, setProductsLastUpdate] = useState(Date.now());

  const triggerSupplierProductsUpdate = useCallback(() => {
    const now = Date.now();
    setSupplierProductsLastUpdate(now);
    // Also trigger low stock products update since they depend on supplier products
    setLowStockProductsLastUpdate(now);
  }, []);

  const triggerLowStockProductsUpdate = useCallback(() => {
    setLowStockProductsLastUpdate(Date.now());
  }, []);

  const triggerProductsUpdate = useCallback(() => {
    const now = Date.now();
    setProductsLastUpdate(now);
    // Products update affects supplier products and low stock
    setSupplierProductsLastUpdate(now);
    setLowStockProductsLastUpdate(now);
  }, []);

  return (
    <DataSyncContext.Provider
      value={{
        supplierProductsLastUpdate,
        triggerSupplierProductsUpdate,
        lowStockProductsLastUpdate,
        triggerLowStockProductsUpdate,
        productsLastUpdate,
        triggerProductsUpdate,
      }}
    >
      {children}
    </DataSyncContext.Provider>
  );
};

/**
 * Hook to access data synchronization context
 * 
 * @throws Error if used outside DataSyncProvider
 * @returns DataSyncContextType
 */
export const useDataSync = (): DataSyncContextType => {
  const context = useContext(DataSyncContext);
  if (!context) {
    throw new Error('useDataSync must be used within DataSyncProvider');
  }
  return context;
};
