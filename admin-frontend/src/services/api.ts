import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestHeaders,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import { logError, logWarning } from '../utils/errorLogger';

// Extend the AxiosRequestConfig interface to include our custom _retry property
interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _retryCount?: number;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000/api/v1';
const REFRESH_ENDPOINT = '/auth/refresh-token';
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// Create axios instance with base URL
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for sending cookies with CORS
  timeout: 300000, // 5 minutes timeout for long-running operations (imports, exports)
});

let isRefreshing = false;
const pendingRequests: Array<(token: string | null) => void> = [];

const processQueue = (token: string | null) => {
  pendingRequests.forEach(callback => callback(token));
  pendingRequests.length = 0;
};

const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

const clearAuth = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem('user');
};

const refreshAccessToken = async (refreshToken: string): Promise<string | null> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}${REFRESH_ENDPOINT}`,
      null,
      {
        withCredentials: true,
        headers: {
          Authorization: `Bearer ${refreshToken}`,
        },
      }
    );

    const newAccessToken = response.data?.access_token ?? null;
    const newRefreshToken = response.data?.refresh_token;

    if (newRefreshToken && typeof newRefreshToken === 'string') {
      localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
    }

    return newAccessToken;
  } catch (error) {
    const axiosError = error as AxiosError;
    if (axiosError.response?.status === 404) {
      // Refresh endpoint unavailable; allow caller to handle as unauthenticated
      return null;
    }
    throw error;
  }
};

// Helper function to get auth token
export const getAuthToken = (): string | null => {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

// Helper function to check if user is authenticated
export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};

// Add a request interceptor to include the auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from local storage
    const token = getAuthToken();

    // If token exists, add it to the headers
    const headers: AxiosRequestHeaders = (config.headers ??= {} as AxiosRequestHeaders);

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    } else if ('Authorization' in headers) {
      delete headers.Authorization;
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle 401 errors and rate limiting
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryConfig | undefined;

    // Handle rate limiting (429)
    if (error.response?.status === 429 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      // Wait for the retry-after header or default to 2 seconds
      const retryAfter = error.response.headers['retry-after'] || '2';
      const delay = parseInt(retryAfter) * 1000;
      
      logWarning(`Rate limited. Retrying after ${delay}ms`, {
        url: originalRequest.url,
        method: originalRequest.method,
      });
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return api(originalRequest);
    }

    // Log API errors
    if (error.response?.status && error.response.status >= 500) {
      logError(error, {
        component: 'API',
        url: originalRequest?.url,
        method: originalRequest?.method,
        status: error.response.status,
      });
    }

    if (error.response?.status !== 401 || !originalRequest) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    const refreshToken = getRefreshToken();

    const isEmagRequest = typeof originalRequest.url === 'string' && originalRequest.url.includes('/emag/');

    if (!refreshToken) {
      if (isEmagRequest) {
        return Promise.reject(error);
      }
      clearAuth();
      window.location.href = '/login';
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingRequests.push(token => {
          if (!token) {
            reject(error);
            return;
          }

          const headers: AxiosRequestHeaders = (originalRequest.headers ??= {} as AxiosRequestHeaders);
          headers.Authorization = `Bearer ${token}`;
          resolve(api(originalRequest));
        });
      });
    }

    isRefreshing = true;

    try {
      const newAccessToken = await refreshAccessToken(refreshToken);

      if (!newAccessToken) {
        throw new Error('No access token returned during refresh');
      }

      setAuthToken(newAccessToken);
      api.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`;

      processQueue(newAccessToken);

      const headers: AxiosRequestHeaders = (originalRequest.headers ??= {} as AxiosRequestHeaders);
      headers.Authorization = `Bearer ${newAccessToken}`;

      return api(originalRequest);
    } catch (refreshError) {
      logError(refreshError as Error, {
        component: 'API',
        action: 'Token refresh failed',
        url: originalRequest?.url,
      });
      processQueue(null);
      if (!isEmagRequest) {
        clearAuth();
        window.location.href = '/login';
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

// Helper function to set auth token
export const setAuthToken = (token: string): void => {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
};

// Helper function to remove auth token
export const removeAuthToken = (): void => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
};

export default api;
