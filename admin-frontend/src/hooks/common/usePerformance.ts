/**
 * Performance Monitoring Hook
 * 
 * React hook for monitoring application performance.
 */

import { useState, useEffect, useCallback } from 'react';
import { performanceApi } from '../../services/apiClient';

interface PerformanceOverview {
  total_requests: number;
  status_codes: Record<string, number>;
  slow_requests: number;
  slow_percentage: number;
}

interface EndpointMetric {
  endpoint: string;
  request_count: number;
  avg_duration: number;
  slow_requests: number;
  slow_percentage: number;
}

export const usePerformance = (autoRefresh = false, refreshInterval = 30000) => {
  const [overview, setOverview] = useState<PerformanceOverview | null>(null);
  const [endpoints, setEndpoints] = useState<EndpointMetric[]>([]);
  const [slowest, setSlowest] = useState<EndpointMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await performanceApi.getOverview();
      setOverview(data as any);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch performance overview');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchEndpoints = useCallback(async (limit = 20) => {
    try {
      setLoading(true);
      setError(null);
      const data = await performanceApi.getEndpoints(limit);
      setEndpoints((data as any).endpoints || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch endpoint metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSlowest = useCallback(async (limit = 10) => {
    try {
      setLoading(true);
      setError(null);
      const data = await performanceApi.getSlowest(limit);
      setSlowest((data as any).slowest_endpoints || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch slowest endpoints');
    } finally {
      setLoading(false);
    }
  }, []);

  const resetMetrics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await performanceApi.reset();
      // Refresh data after reset
      await Promise.all([fetchOverview(), fetchEndpoints(), fetchSlowest()]);
    } catch (err: any) {
      setError(err.message || 'Failed to reset metrics');
    } finally {
      setLoading(false);
    }
  }, [fetchOverview, fetchEndpoints, fetchSlowest]);

  const refresh = useCallback(async () => {
    await Promise.all([fetchOverview(), fetchEndpoints(), fetchSlowest()]);
  }, [fetchOverview, fetchEndpoints, fetchSlowest]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(refresh, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, refresh]);

  return {
    overview,
    endpoints,
    slowest,
    loading,
    error,
    refresh,
    resetMetrics,
  };
};
