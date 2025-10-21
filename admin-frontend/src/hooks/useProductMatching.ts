import { useState, useCallback, useRef, useEffect } from 'react';
import api from '../services/api';

export interface LocalProductSuggestion {
  local_product_id: number;
  local_product_name: string;
  local_product_chinese_name?: string;
  local_product_sku: string;
  local_product_brand?: string;
  local_product_image_url?: string;
  similarity_score: number;
  similarity_percent: number;
  common_tokens: string[];
  common_tokens_count: number;
  confidence_level: 'high' | 'medium' | 'low';
}

export interface SupplierProductWithSuggestions {
  id: number;
  supplier_id: number;
  supplier_name: string;
  supplier_product_name: string;
  supplier_product_chinese_name?: string;
  supplier_product_specification?: string;
  supplier_product_url: string;
  supplier_image_url: string;
  supplier_price: number;
  supplier_currency: string;
  created_at: string;
  suggestions: LocalProductSuggestion[];
  suggestions_count: number;
  best_match_score: number;
}

interface UseProductMatchingOptions {
  supplierId: number | null;
  minSimilarity: number;
  maxSuggestions: number;
  pageSize: number;
  filterType: string;
}

interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

export const useProductMatching = (options: UseProductMatchingOptions) => {
  const [products, setProducts] = useState<SupplierProductWithSuggestions[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: options.pageSize,
    total: 0,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  const fetchProducts = useCallback(
    async (page: number = 1) => {
      if (!options.supplierId) return;

      // Cancel previous request
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      setLoading(true);
      setError(null);

      try {
        const skip = (page - 1) * options.pageSize;
        const response = await api.get(
          `/suppliers/${options.supplierId}/products/unmatched-with-suggestions`,
          {
            params: {
              skip,
              limit: options.pageSize,
              min_similarity: options.minSimilarity,
              max_suggestions: options.maxSuggestions,
              filter_type: options.filterType,
            },
            signal: abortControllerRef.current.signal,
          }
        );

        if (!isMountedRef.current) return;

        if (response.data.status === 'success') {
          setProducts(response.data.data.products);
          setPagination({
            current: page,
            pageSize: options.pageSize,
            total: response.data.data.pagination.total,
          });
        }
      } catch (err) {
        if (!isMountedRef.current) return;
        if ((err as any).name === 'AbortError') return;

        setError(err as Error);
        console.error('Error fetching products:', err);
      } finally {
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    },
    [
      options.supplierId,
      options.minSimilarity,
      options.maxSuggestions,
      options.pageSize,
      options.filterType,
    ]
  );

  const confirmMatch = useCallback(
    async (supplierProductId: number, localProductId: number) => {
      try {
        await api.post(
          `/suppliers/${options.supplierId}/products/${supplierProductId}/match`,
          {
            local_product_id: localProductId,
            confidence_score: 1.0,
            manual_confirmed: true,
          }
        );
        return { success: true };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [options.supplierId]
  );

  const removeSuggestion = useCallback(
    async (supplierProductId: number, localProductId: number) => {
      // Optimistic update
      setProducts((prev) =>
        prev.map((p) => {
          if (p.id === supplierProductId) {
            const updatedSuggestions = p.suggestions.filter(
              (s) => s.local_product_id !== localProductId
            );
            return {
              ...p,
              suggestions: updatedSuggestions,
              suggestions_count: updatedSuggestions.length,
              best_match_score:
                updatedSuggestions.length > 0
                  ? updatedSuggestions[0].similarity_score
                  : 0,
            };
          }
          return p;
        })
      );

      try {
        await api.delete(
          `/suppliers/${options.supplierId}/products/${supplierProductId}/suggestions/${localProductId}`
        );
        return { success: true };
      } catch (err) {
        // Rollback on error
        await fetchProducts(pagination.current);
        return { success: false, error: err };
      }
    },
    [options.supplierId, pagination.current, fetchProducts]
  );

  const updatePrice = useCallback(
    async (supplierProductId: number, newPrice: number) => {
      try {
        await api.patch(
          `/suppliers/${options.supplierId}/products/${supplierProductId}`,
          {
            supplier_price: newPrice,
          }
        );

        // Optimistic update
        setProducts((prev) =>
          prev.map((p) =>
            p.id === supplierProductId ? { ...p, supplier_price: newPrice } : p
          )
        );

        return { success: true };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [options.supplierId]
  );

  return {
    products,
    loading,
    error,
    pagination,
    fetchProducts,
    confirmMatch,
    removeSuggestion,
    updatePrice,
  };
};
