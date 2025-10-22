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

interface FallbackProduct {
  id: number;
  supplier_id: number;
  supplier_product_name: string;
  supplier_product_chinese_name?: string | null;
  supplier_product_specification?: string | null;
  supplier_product_url?: string | null;
  supplier_image_url?: string | null;
  supplier_price: number | string | null;
  supplier_currency?: string | null;
  created_at?: string | null;
}

type ViewMode = 'unmatched' | 'all';

export type FetchSource = 'unmatched' | 'all' | 'error';

export interface FetchSummary {
  source: FetchSource;
  total: number;
  received: number;
  page: number;
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
  const [isFallback, setIsFallback] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('unmatched');
  const [lastFetchInfo, setLastFetchInfo] = useState<FetchSummary | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  const loadAllProducts = useCallback(
    async (page: number, opts: { manageLoading?: boolean } = {}) => {
      if (!options.supplierId) return false;

      if (opts.manageLoading) {
        setLoading(true);
        setError(null);
      }

      try {
        const skip = (page - 1) * options.pageSize;
        const fallbackResponse = await api.get(
          `/suppliers/${options.supplierId}/products/all`,
        );

        if (!isMountedRef.current) return false;

        if (fallbackResponse.data.status === 'success') {
          const supplierName = fallbackResponse.data.data?.supplier_name ?? 'Furnizor';
          const fallbackProducts: FallbackProduct[] =
            fallbackResponse.data.data?.products ?? [];
          const pagedFallback = fallbackProducts
            .slice(skip, skip + options.pageSize)
            .map((product) => {
              const rawPrice = product.supplier_price;
              const priceValue =
                typeof rawPrice === 'number'
                  ? rawPrice
                  : Number.parseFloat(rawPrice ?? '0');

              return {
                id: product.id,
                supplier_id: product.supplier_id,
                supplier_name: supplierName,
                supplier_product_name: product.supplier_product_name ?? 'Produs furnizor',
                supplier_product_chinese_name: product.supplier_product_chinese_name ?? undefined,
                supplier_product_specification: product.supplier_product_specification ?? undefined,
                supplier_product_url: product.supplier_product_url ?? '',
                supplier_image_url: product.supplier_image_url ?? '',
                supplier_price: Number.isFinite(priceValue) ? priceValue : 0,
                supplier_currency: product.supplier_currency ?? 'CNY',
                created_at: product.created_at ?? '',
                suggestions: [],
                suggestions_count: 0,
                best_match_score: 0,
              } satisfies SupplierProductWithSuggestions;
            });

          setIsFallback(true);
          setViewMode('all');
          setProducts(pagedFallback);
          setPagination({
            current: page,
            pageSize: options.pageSize,
            total: fallbackProducts.length,
          });
          setError(null);
          setLastFetchInfo({
            source: 'all',
            total: fallbackProducts.length,
            received: pagedFallback.length,
            page,
          });
          return true;
        }
      } catch (fallbackError) {
        if (!isMountedRef.current) return false;
        console.error('Error fetching fallback supplier products:', fallbackError);
        setIsFallback(false);
        setError(fallbackError as Error);
        setLastFetchInfo({
          source: 'error',
          total: 0,
          received: 0,
          page,
        });
      } finally {
        if (opts.manageLoading && isMountedRef.current) {
          setLoading(false);
        }
      }

      return false;
    },
    [options.pageSize, options.supplierId]
  );

  const fetchAllProducts = useCallback(
    async (page: number = 1) => {
      if (!options.supplierId) return false;

      // Cancel any in-flight unmatched request
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      return loadAllProducts(page, { manageLoading: true });
    },
    [loadAllProducts, options.supplierId]
  );

  const fetchProducts = useCallback(
    async (page: number = 1) => {
      if (!options.supplierId) return;

      // Validate parameters before making the request
      if (
        options.minSimilarity < 0 ||
        options.minSimilarity > 1 ||
        options.maxSuggestions < 1 ||
        options.maxSuggestions > 10
      ) {
        setError(
          new Error(
            `Invalid parameters: minSimilarity (${options.minSimilarity}) must be between 0-1, maxSuggestions (${options.maxSuggestions}) must be between 1-10`
          )
        );
        return;
      }

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
          const responseData = response.data.data ?? {};
          const unmatchedProducts: SupplierProductWithSuggestions[] =
            (responseData.products as SupplierProductWithSuggestions[]) ?? [];
          const paginationTotal = responseData.pagination?.total ?? unmatchedProducts.length;

          if (unmatchedProducts.length > 0) {
            setIsFallback(false);
            setViewMode('unmatched');
            setProducts(unmatchedProducts);
            setPagination({
              current: page,
              pageSize: options.pageSize,
              total: paginationTotal,
            });
            setLastFetchInfo({
              source: 'unmatched',
              total: paginationTotal,
              received: unmatchedProducts.length,
              page,
            });
            return;
          }

          const fallbackLoaded = await loadAllProducts(page);
          if (fallbackLoaded) {
            return;
          }
        }
      } catch (err) {
        if (!isMountedRef.current) return;
        if ((err as any).name === 'AbortError') return;

        console.error('Error in fetchProducts:', err.response?.data);
        if (err instanceof Error) {
          setError(err);
        } else {
          setError(new Error(String(err)));
        }

        const fallbackLoaded = await loadAllProducts(page);
        if (fallbackLoaded) {
          return;
        }

        setIsFallback(false);
        setViewMode('unmatched');
        setLastFetchInfo({
          source: 'error',
          total: 0,
          received: 0,
          page,
        });
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
      loadAllProducts,
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
    fetchAllProducts,
    confirmMatch,
    removeSuggestion,
    updatePrice,
    isFallback,
    viewMode,
    lastFetchInfo,
  };
};
