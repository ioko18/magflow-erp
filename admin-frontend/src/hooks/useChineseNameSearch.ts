import { useCallback, useEffect, useMemo, useState } from 'react';
import { searchByChineseName, linkSupplierProduct, updateLocalChineseName, updateSupplierProductName } from '../services/api';

export interface SupplierMatch {
  supplier_product_id: number;
  supplier_id: number;
  supplier_name?: string;
  supplier_product_name?: string;
  supplier_product_chinese_name?: string;
  supplier_product_specification?: string;
  supplier_product_url?: string;
  supplier_image_url?: string | null;
  supplier_price?: number;
  supplier_currency?: string;
  similarity_score: number;
  similarity_percent?: number;
  local_product_id?: number | null;
  local_product?: {
    id?: number;
    name?: string;
    sku?: string;
    brand?: string | null;
    image_url?: string | null;
    chinese_name?: string | null;
  } | null;
  manual_confirmed?: boolean;
  confidence_score?: number;
}

export interface LocalProductMatch {
  id: number;
  name: string;
  chinese_name?: string | null;
  sku: string;
  brand?: string | null;
  image_url?: string | null;
  similarity_score: number;
  similarity_percent?: number;
  supplier_match_count?: number;
}

interface ChineseNameSearchState {
  supplierMatches: SupplierMatch[];
  localMatches: LocalProductMatch[];
}

const DEFAULT_STATE: ChineseNameSearchState = {
  supplierMatches: [],
  localMatches: [],
};

export default function useChineseNameSearch() {
  const [searchTerm, setSearchTerm] = useState('');
  const [state, setState] = useState<ChineseNameSearchState>(DEFAULT_STATE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [linkingIds, setLinkingIds] = useState<Set<number>>(new Set());
  const [updatingLocalIds, setUpdatingLocalIds] = useState<Set<number>>(new Set());
  const [updatingSupplierNameIds, setUpdatingSupplierNameIds] = useState<Set<number>>(new Set());

  const clearResults = useCallback(() => {
    setState(DEFAULT_STATE);
    setError(null);
    setUpdatingLocalIds(new Set());
    setUpdatingSupplierNameIds(new Set());
  }, []);

  const fetchMatches = useCallback(
    async (term: string) => {
      const trimmed = term.trim();
      if (!trimmed) {
        clearResults();
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await searchByChineseName(trimmed);
        if (response.data.status === 'success') {
          const data = response.data.data ?? {};
          setState({
            supplierMatches: data.supplier_matches ?? [],
            localMatches: data.local_matches ?? [],
          });
        } else {
          throw new Error(response.data.message || 'Search failed');
        }
      } catch (err) {
        const errorObj = err as Error;
        console.error('Error searching Chinese name', errorObj);
        setError(errorObj);
      } finally {
        setLoading(false);
      }
    },
    [clearResults]
  );

  useEffect(() => {
    fetchMatches(searchTerm);
  }, [fetchMatches, searchTerm]);

  const linkSupplierProductToLocal = useCallback(
    async (supplierProductId: number, localProductId: number) => {
      setLinkingIds(prev => {
        const next = new Set(prev);
        next.add(supplierProductId);
        return next;
      });

      try {
        await linkSupplierProduct(supplierProductId, localProductId);
        await fetchMatches(searchTerm);
      } catch (err) {
        const errorObj = err as Error;
        console.error('Error linking supplier product', errorObj);
        setError(errorObj);
        throw errorObj;
      } finally {
        setLinkingIds(prev => {
          const next = new Set(prev);
          next.delete(supplierProductId);
          return next;
        });
      }
    },
    [fetchMatches, searchTerm]
  );

  const linkingSet = useMemo(() => new Set(linkingIds), [linkingIds]);
  const updatingLocalSet = useMemo(() => new Set(updatingLocalIds), [updatingLocalIds]);
  const updatingSupplierNameSet = useMemo(() => new Set(updatingSupplierNameIds), [updatingSupplierNameIds]);

  const updateLocalProductChineseName = useCallback(
    async (productId: number, chineseName: string | null) => {
      setUpdatingLocalIds(prev => {
        const next = new Set(prev);
        next.add(productId);
        return next;
      });

      try {
        const response = await updateLocalChineseName(productId, chineseName);
        const updatedName = response.data?.data?.chinese_name ?? chineseName ?? null;
        setState(prev => ({
          ...prev,
          localMatches: prev.localMatches.map(match =>
            match.id === productId
              ? { ...match, chinese_name: updatedName }
              : match
          ),
        }));
      } catch (err) {
        const errorObj = err as Error;
        setError(errorObj);
        throw errorObj;
      } finally {
        setUpdatingLocalIds(prev => {
          const next = new Set(prev);
          next.delete(productId);
          return next;
        });
      }
    },
    []
  );

  const updateSupplierProductDisplayName = useCallback(
    async (supplierProductId: number, supplierId: number, name: string) => {
      setUpdatingSupplierNameIds(prev => {
        const next = new Set(prev);
        next.add(supplierProductId);
        return next;
      });

      try {
        const trimmedName = name.trim();
        if (!trimmedName) {
          throw new Error('Numele produsului nu poate fi gol.');
        }

        await updateSupplierProductName(supplierId, supplierProductId, trimmedName);
        setState(prev => ({
          ...prev,
          supplierMatches: prev.supplierMatches.map(match =>
            match.supplier_product_id === supplierProductId
              ? { ...match, supplier_product_name: trimmedName }
              : match
          ),
        }));
      } catch (err) {
        const errorObj = err as Error;
        setError(errorObj);
        throw errorObj;
      } finally {
        setUpdatingSupplierNameIds(prev => {
          const next = new Set(prev);
          next.delete(supplierProductId);
          return next;
        });
      }
    },
    []
  );

  return {
    supplierMatches: state.supplierMatches,
    localMatches: state.localMatches,
    loading,
    error,
    setChineseName: setSearchTerm,
    linkSupplierProduct: linkSupplierProductToLocal,
    linkingIds: linkingSet,
    updateLocalChineseName: updateLocalProductChineseName,
    updatingLocalIds: updatingLocalSet,
    updateSupplierProductName: updateSupplierProductDisplayName,
    updatingSupplierNameIds: updatingSupplierNameSet,
    searchTerm,
    refetch: () => fetchMatches(searchTerm),
  };
}
