import { message } from 'antd';
import axios, { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  details?: any;
}

export class AppError extends Error {
  public status?: number;
  public code?: string;
  public details?: any;

  constructor(message: string, status?: number, code?: string, details?: any) {
    super(message);
    this.name = 'AppError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/**
 * Parse error from various sources
 */
export function parseError(error: unknown): ApiError {
  // Axios error
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<any>;
    
    return {
      message: axiosError.response?.data?.detail || 
               axiosError.response?.data?.message || 
               axiosError.message || 
               'A apărut o eroare de rețea',
      status: axiosError.response?.status,
      code: axiosError.code,
      details: axiosError.response?.data,
    };
  }

  // AppError
  if (error instanceof AppError) {
    return {
      message: error.message,
      status: error.status,
      code: error.code,
      details: error.details,
    };
  }

  // Standard Error
  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }

  // Unknown error
  return {
    message: 'A apărut o eroare necunoscută',
  };
}

/**
 * Get user-friendly error message
 */
export function getUserFriendlyMessage(error: ApiError): string {
  // Network errors
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
    return 'Nu se poate conecta la server. Verificați conexiunea la internet.';
  }

  // Timeout
  if (error.code === 'ECONNREFUSED' || error.message.includes('timeout')) {
    return 'Serverul nu răspunde. Vă rugăm încercați din nou.';
  }

  // HTTP status codes
  switch (error.status) {
    case 400:
      return 'Datele trimise sunt invalide. Verificați formularul.';
    case 401:
      return 'Sesiunea a expirat. Vă rugăm autentificați-vă din nou.';
    case 403:
      return 'Nu aveți permisiunea de a accesa această resursă.';
    case 404:
      return 'Resursa solicitată nu a fost găsită.';
    case 409:
      return 'Există un conflict cu datele existente.';
    case 422:
      return 'Datele trimise nu pot fi procesate. Verificați formularul.';
    case 429:
      return 'Prea multe cereri. Vă rugăm așteptați puțin.';
    case 500:
      return 'Eroare internă de server. Echipa tehnică a fost notificată.';
    case 502:
    case 503:
      return 'Serverul este temporar indisponibil. Încercați din nou în câteva momente.';
    case 504:
      return 'Serverul nu răspunde la timp. Încercați din nou.';
    default:
      return error.message || 'A apărut o eroare. Vă rugăm încercați din nou.';
  }
}

/**
 * Show error notification
 */
export function showError(error: unknown, customMessage?: string) {
  const apiError = parseError(error);
  const userMessage = customMessage || getUserFriendlyMessage(apiError);

  message.error({
    content: userMessage,
    duration: 5,
    key: 'error-message',
  });

  // Log to console in development
  if (import.meta.env.DEV) {
    console.error('Error details:', apiError);
  }
}

/**
 * Show success notification
 */
export function showSuccess(content: string, duration: number = 3) {
  message.success({
    content,
    duration,
    key: 'success-message',
  });
}

/**
 * Show warning notification
 */
export function showWarning(content: string, duration: number = 4) {
  message.warning({
    content,
    duration,
    key: 'warning-message',
  });
}

/**
 * Show info notification
 */
export function showInfo(content: string, duration: number = 3) {
  message.info({
    content,
    duration,
    key: 'info-message',
  });
}

/**
 * Retry function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000,
  onRetry?: (attempt: number, error: any) => void
): Promise<T> {
  let lastError: any;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt);
        
        if (onRetry) {
          onRetry(attempt + 1, error);
        }

        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  const apiError = parseError(error);

  // Network errors are retryable
  if (apiError.code === 'ERR_NETWORK' || apiError.code === 'ECONNABORTED') {
    return true;
  }

  // Timeout errors are retryable
  if (apiError.code === 'ECONNREFUSED' || apiError.message.includes('timeout')) {
    return true;
  }

  // 5xx errors are retryable
  if (apiError.status && apiError.status >= 500) {
    return true;
  }

  // 429 (rate limit) is retryable
  if (apiError.status === 429) {
    return true;
  }

  return false;
}

/**
 * Log error to external service (Sentry)
 */
export function logErrorToService(error: Error, errorInfo?: any) {
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    try {
      // Dynamically import Sentry to avoid loading in development
      import('@sentry/react').then(({ captureException }) => {
        captureException(error, {
          extra: errorInfo,
          tags: {
            component: errorInfo?.componentStack ? 'React Component' : 'General',
          },
        });
      });
    } catch (sentryError) {
      console.error('Failed to log to Sentry:', sentryError);
    }
  } else if (import.meta.env.DEV) {
    console.error('Error logged (dev mode):', error, errorInfo);
  }
}
