/**
 * Centralized Error Logging Utility
 * 
 * Provides consistent error logging and reporting across the application.
 */

interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  [key: string]: any;
}

class ErrorLogger {
  private isDevelopment = import.meta.env.DEV;

  /**
   * Log an error with context
   */
  logError(error: Error | unknown, context?: ErrorContext): void {
    const errorInfo = this.formatError(error, context);

    if (this.isDevelopment) {
      console.error('[Error]', errorInfo);
    }

    // In production, send to error tracking service (Sentry, LogRocket, etc.)
    this.sendToErrorTracking(errorInfo);
  }

  /**
   * Log a warning
   */
  logWarning(message: string, context?: ErrorContext): void {
    const warningInfo = {
      level: 'warning',
      message,
      context,
      timestamp: new Date().toISOString(),
    };

    if (this.isDevelopment) {
      console.warn('[Warning]', warningInfo);
    }

    this.sendToErrorTracking(warningInfo);
  }

  /**
   * Log an info message
   */
  logInfo(message: string, context?: ErrorContext): void {
    if (this.isDevelopment) {
      console.info('[Info]', message, context);
    }
  }

  /**
   * Format error for logging
   */
  private formatError(error: Error | unknown, context?: ErrorContext) {
    const errorObj = error instanceof Error ? error : new Error(String(error));

    return {
      level: 'error',
      message: errorObj.message,
      stack: errorObj.stack,
      context,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    };
  }

  /**
   * Send error to tracking service
   */
  private sendToErrorTracking(errorInfo: any): void {
    // In production, integrate with error tracking service
    // Example: Sentry.captureException(errorInfo)
    
    // For now, store in localStorage for debugging
    if (!this.isDevelopment) {
      try {
        const errors = JSON.parse(localStorage.getItem('app_errors') || '[]');
        errors.push(errorInfo);
        // Keep only last 50 errors
        if (errors.length > 50) {
          errors.shift();
        }
        localStorage.setItem('app_errors', JSON.stringify(errors));
      } catch (e) {
        // Ignore localStorage errors
      }
    }
  }

  /**
   * Get stored errors (for debugging)
   */
  getStoredErrors(): any[] {
    try {
      return JSON.parse(localStorage.getItem('app_errors') || '[]');
    } catch {
      return [];
    }
  }

  /**
   * Clear stored errors
   */
  clearStoredErrors(): void {
    localStorage.removeItem('app_errors');
  }
}

export const errorLogger = new ErrorLogger();

// Helper functions for common use cases
export const logError = (error: Error | unknown, context?: ErrorContext) => {
  errorLogger.logError(error, context);
};

export const logWarning = (message: string, context?: ErrorContext) => {
  errorLogger.logWarning(message, context);
};

export const logInfo = (message: string, context?: ErrorContext) => {
  errorLogger.logInfo(message, context);
};
