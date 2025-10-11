/**
 * Pagination Hook
 * 
 * Reusable hook for managing pagination state
 */

import { useState, useCallback } from 'react';

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
}

export const usePagination = (initialLimit: number = 20) => {
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    limit: initialLimit,
    total: 0,
  });

  const setPage = useCallback((page: number) => {
    setPagination(prev => ({ ...prev, page }));
  }, []);

  const setLimit = useCallback((limit: number) => {
    setPagination(prev => ({ ...prev, limit, page: 1 }));
  }, []);

  const setTotal = useCallback((total: number) => {
    setPagination(prev => ({ ...prev, total }));
  }, []);

  const nextPage = useCallback(() => {
    setPagination(prev => {
      const maxPage = Math.ceil(prev.total / prev.limit);
      return { ...prev, page: Math.min(prev.page + 1, maxPage) };
    });
  }, []);

  const prevPage = useCallback(() => {
    setPagination(prev => ({ ...prev, page: Math.max(prev.page - 1, 1) }));
  }, []);

  const reset = useCallback(() => {
    setPagination({ page: 1, limit: initialLimit, total: 0 });
  }, [initialLimit]);

  return {
    pagination,
    setPage,
    setLimit,
    setTotal,
    nextPage,
    prevPage,
    reset,
  };
};
