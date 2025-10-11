/**
 * Products Hook
 * 
 * React hook for managing products data and operations
 */

import { useState, useEffect, useCallback } from 'react';
import { productsApi, Product, ProductFilters } from '../../services/products';

export const useProducts = (initialFilters?: ProductFilters) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ProductFilters>(initialFilters || {});
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    limit: 20,
  });

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await productsApi.getProducts({ ...filters, page: pagination.page, limit: pagination.limit }) as any;
      setProducts((data.items || data.products || []) as Product[]);
      setPagination(prev => ({
        ...prev,
        total: (data.total || 0) as number,
      }));
    } catch (err: any) {
      setError(err.message || 'Failed to fetch products');
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.limit]);

  const createProduct = useCallback(async (product: Partial<Product>) => {
    try {
      setLoading(true);
      setError(null);
      const newProduct = await productsApi.createProduct(product) as Product;
      setProducts(prev => [newProduct, ...prev]);
      return newProduct;
    } catch (err: any) {
      setError(err.message || 'Failed to create product');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateProduct = useCallback(async (id: number, product: Partial<Product>) => {
    try {
      setLoading(true);
      setError(null);
      const updatedProduct = await productsApi.updateProduct(id, product) as Product;
      setProducts(prev => prev.map(p => p.id === id ? updatedProduct : p));
      return updatedProduct;
    } catch (err: any) {
      setError(err.message || 'Failed to update product');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteProduct = useCallback(async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      await productsApi.deleteProduct(id);
      setProducts(prev => prev.filter(p => p.id !== id));
    } catch (err: any) {
      setError(err.message || 'Failed to delete product');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const bulkUpdate = useCallback(async (updates: Array<{ id: number; data: Partial<Product> }>) => {
    try {
      setLoading(true);
      setError(null);
      await productsApi.bulkUpdateProducts(updates);
      await fetchProducts(); // Refresh the list
    } catch (err: any) {
      setError(err.message || 'Failed to bulk update products');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchProducts]);

  const importProducts = useCallback(async (file: File, options?: { supplier_id?: number }) => {
    try {
      setLoading(true);
      setError(null);
      const result = await productsApi.importProducts(file, options);
      await fetchProducts(); // Refresh the list
      return result;
    } catch (err: any) {
      setError(err.message || 'Failed to import products');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchProducts]);

  const exportProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const blob = await productsApi.exportProducts(filters) as Blob;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `products_${new Date().toISOString().split('T')[0]}.xlsx`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || 'Failed to export products');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  return {
    products,
    loading,
    error,
    filters,
    setFilters,
    pagination,
    setPagination,
    refresh: fetchProducts,
    createProduct,
    updateProduct,
    deleteProduct,
    bulkUpdate,
    importProducts,
    exportProducts,
  };
};
