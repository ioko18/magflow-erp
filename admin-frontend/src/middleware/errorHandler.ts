/**
 * Global error handler middleware
 */

import { AxiosError } from 'axios';
import { ErrorResponse } from '../types/api';

export class AppError extends Error {
  constructor(
    message: string,
    public code?: string,
    public statusCode?: number,
    public errors?: Record<string, string[]>
  ) {
    super(message);
    this.name = 'AppError';
  }
}

/**
 * Handle API errors
 */
export const handleApiError = (error: unknown): AppError => {
  if (error instanceof AxiosError) {
    const response = error.response?.data as ErrorResponse;
    
    return new AppError(
      response?.message || error.message || 'An error occurred',
      response?.code,
      error.response?.status,
      response?.errors
    );
  }

  if (error instanceof Error) {
    return new AppError(error.message);
  }

  return new AppError('An unknown error occurred');
};

/**
 * Log error to console (development) or service (production)
 */
export const logError = (error: Error | AppError, context?: Record<string, any>): void => {
  if (import.meta.env.DEV) {
    console.error('Error:', error);
    if (context) {
      console.error('Context:', context);
    }
  } else {
    // In production, send to error tracking service (e.g., Sentry)
    // sentry.captureException(error, { extra: context });
  }
};

/**
 * Get user-friendly error message
 */
export const getErrorMessage = (error: unknown): string => {
  const appError = handleApiError(error);
  return appError.message;
};

/**
 * Check if error is authentication error
 */
export const isAuthError = (error: unknown): boolean => {
  if (error instanceof AppError) {
    return error.statusCode === 401 || error.code === 'UNAUTHORIZED';
  }
  return false;
};

/**
 * Check if error is validation error
 */
export const isValidationError = (error: unknown): boolean => {
  if (error instanceof AppError) {
    return error.statusCode === 422 || !!error.errors;
  }
  return false;
};
