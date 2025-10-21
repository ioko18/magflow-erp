import { useState, useCallback, useEffect } from 'react';
import api from '../services/api';

export interface Supplier {
  id: number;
  name: string;
  country?: string;
}

export const useSuppliers = () => {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSuppliers = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get('/suppliers', {
        params: { limit: 1000, active_only: true },
      });

      if (response.data.status === 'success') {
        const suppliersList = response.data.data?.suppliers || response.data.data;

        if (Array.isArray(suppliersList)) {
          setSuppliers(suppliersList);
        } else {
          console.error('Suppliers data is not an array:', suppliersList);
          setSuppliers([]);
        }
      }
    } catch (err) {
      setError(err as Error);
      console.error('Error fetching suppliers:', err);
      setSuppliers([]);
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
    refetch: fetchSuppliers,
  };
};
