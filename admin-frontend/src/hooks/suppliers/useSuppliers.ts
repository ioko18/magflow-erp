/**
 * Suppliers Hook
 * 
 * React hook for managing suppliers data and operations
 */

import { useState, useEffect, useCallback } from 'react';
import { suppliersApi, Supplier } from '../../services/suppliers';

export const useSuppliers = (params?: { search?: string; is_active?: boolean }) => {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSuppliers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await suppliersApi.getSuppliers(params) as any;
      setSuppliers((data.items || data.suppliers || []) as Supplier[]);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch suppliers');
    } finally {
      setLoading(false);
    }
  }, [params]);

  const createSupplier = useCallback(async (supplier: Partial<Supplier>) => {
    try {
      setLoading(true);
      setError(null);
      const newSupplier = await suppliersApi.createSupplier(supplier) as Supplier;
      setSuppliers(prev => [newSupplier, ...prev]);
      return newSupplier;
    } catch (err: any) {
      setError(err.message || 'Failed to create supplier');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateSupplier = useCallback(async (id: number, supplier: Partial<Supplier>) => {
    try {
      setLoading(true);
      setError(null);
      const updatedSupplier = await suppliersApi.updateSupplier(id, supplier) as Supplier;
      setSuppliers(prev => prev.map(s => s.id === id ? updatedSupplier : s));
      return updatedSupplier;
    } catch (err: any) {
      setError(err.message || 'Failed to update supplier');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteSupplier = useCallback(async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      await suppliersApi.deleteSupplier(id);
      setSuppliers(prev => prev.filter(s => s.id !== id));
    } catch (err: any) {
      setError(err.message || 'Failed to delete supplier');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSuppliers();
  }, [fetchSuppliers]);

  return {
    suppliers,
    loading,
    error,
    refresh: fetchSuppliers,
    createSupplier,
    updateSupplier,
    deleteSupplier,
  };
};
