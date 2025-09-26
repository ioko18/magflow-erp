import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestHeaders,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';

// Extend the AxiosRequestConfig interface to include our custom _retry property
interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

const API_BASE_URL = (import.meta as ImportMeta).env?.VITE_API_BASE_URL?.trim() || '/api/v1';
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
  const response = await axios.post(
    `${API_BASE_URL}${REFRESH_ENDPOINT}`,
    { refresh_token: refreshToken },
    {
      withCredentials: true,
    }
  );

  return response.data?.access_token ?? null;
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

// Add a response interceptor to handle 401 errors
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryConfig | undefined;

    if (error.response?.status !== 401 || !originalRequest) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    const refreshToken = getRefreshToken();

    if (!refreshToken) {
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
      console.error('Token refresh failed:', refreshError);
      processQueue(null);
      clearAuth();
      window.location.href = '/login';
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
