/**
 * API Interceptors
 * 
 * Request and response interceptors for axios
 */

import { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { message } from 'antd';
import { logger } from '../utils/logger';

/**
 * Setup request interceptor
 */
export const setupRequestInterceptor = (api: AxiosInstance) => {
  api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Add timestamp to prevent caching
      if (config.method === 'get') {
        config.params = {
          ...config.params,
          _t: Date.now(),
        };
      }

      // Add correlation ID for request tracking
      config.headers['X-Request-ID'] = `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

      // Log request
      logger.apiRequest(config.method || 'GET', config.url || '', config.data);

      return config;
    },
    (error: AxiosError) => {
      logger.error('Request interceptor error', error);
      return Promise.reject(error);
    }
  );
};

/**
 * Setup response interceptor
 */
export const setupResponseInterceptor = (api: AxiosInstance) => {
  api.interceptors.response.use(
    (response: AxiosResponse) => {
      // Log response
      logger.apiResponse(response.status, response.config.url || '', response.data);

      return response;
    },
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

      // Log error
      logger.apiError(
        error.response?.status,
        error.config?.url || '',
        error.message,
        error.response?.data
      );

      // Handle 401 Unauthorized
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        try {
          // Try to refresh token
          const refreshToken = localStorage.getItem('refresh_token');
          
          if (refreshToken) {
            const response = await api.post('/auth/refresh', {
              refresh_token: refreshToken,
            });

            const { access_token } = response.data;
            localStorage.setItem('access_token', access_token);
            api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
            
            // Retry original request
            if (originalRequest.headers) {
              originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
            }
            return api(originalRequest);
          }
        } catch (refreshError) {
          // Refresh failed, logout user
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }

      // Handle 403 Forbidden
      if (error.response?.status === 403) {
        message.error('Nu aveți permisiunea de a accesa această resursă');
      }

      // Handle 404 Not Found
      if (error.response?.status === 404) {
        message.error('Resursa solicitată nu a fost găsită');
      }

      // Handle 500 Server Error
      if (error.response?.status === 500) {
        message.error('Eroare de server. Vă rugăm încercați mai târziu.');
      }

      // Handle network errors
      if (!error.response) {
        message.error('Eroare de conexiune. Verificați conexiunea la internet.');
      }

      return Promise.reject(error);
    }
  );
};

/**
 * Setup all interceptors
 */
export const setupInterceptors = (api: AxiosInstance) => {
  setupRequestInterceptor(api);
  setupResponseInterceptor(api);
};
