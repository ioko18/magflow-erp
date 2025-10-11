/**
 * Structured Logging Utility for MagFlow Admin Frontend
 * 
 * Provides a centralized logging system that:
 * - Disables logs in production
 * - Adds timestamps and context
 * - Supports different log levels
 * - Can be integrated with external services (Sentry, etc.)
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  component?: string;
  action?: string;
  [key: string]: any;
}

class Logger {
  private isDevelopment: boolean;
  private isEnabled: boolean;

  constructor() {
    this.isDevelopment = import.meta.env.DEV;
    this.isEnabled = import.meta.env.VITE_ENABLE_LOGGING !== 'false';
  }

  /**
   * Format log message with timestamp and context
   */
  private formatMessage(level: LogLevel, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const contextStr = context ? ` | ${JSON.stringify(context)}` : '';
    return `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`;
  }

  /**
   * Check if logging is enabled for the given level
   */
  private shouldLog(level: LogLevel): boolean {
    if (!this.isEnabled) return false;
    
    // In production, only log warnings and errors
    if (!this.isDevelopment) {
      return level === 'warn' || level === 'error';
    }
    
    return true;
  }

  /**
   * Debug level logging (only in development)
   */
  debug(message: string, context?: LogContext): void {
    if (this.shouldLog('debug')) {
      console.debug(this.formatMessage('debug', message, context));
    }
  }

  /**
   * Info level logging
   */
  info(message: string, context?: LogContext): void {
    if (this.shouldLog('info')) {
      console.log(this.formatMessage('info', message, context));
    }
  }

  /**
   * Warning level logging
   */
  warn(message: string, context?: LogContext): void {
    if (this.shouldLog('warn')) {
      console.warn(this.formatMessage('warn', message, context));
    }
  }

  /**
   * Error level logging
   */
  error(message: string, error?: Error | any, context?: LogContext): void {
    if (this.shouldLog('error')) {
      const errorContext = {
        ...context,
        error: error?.message || error,
        stack: error?.stack,
      };
      console.error(this.formatMessage('error', message, errorContext));
      
      // In production, send to error tracking service (Sentry, etc.)
      if (!this.isDevelopment && window.Sentry) {
        window.Sentry.captureException(error, {
          extra: context,
        });
      }
    }
  }

  /**
   * API request logging
   */
  apiRequest(method: string, url: string, data?: any): void {
    if (this.isDevelopment && this.isEnabled) {
      console.log('🚀 API Request:', {
        method: method.toUpperCase(),
        url,
        data,
        timestamp: new Date().toISOString(),
      });
    }
  }

  /**
   * API response logging
   */
  apiResponse(status: number, url: string, data?: any): void {
    if (this.isDevelopment && this.isEnabled) {
      console.log('✅ API Response:', {
        status,
        url,
        data,
        timestamp: new Date().toISOString(),
      });
    }
  }

  /**
   * API error logging
   */
  apiError(status: number | undefined, url: string, message: string, error?: any): void {
    if (this.shouldLog('error')) {
      console.error('❌ API Error:', {
        status,
        url,
        message,
        error: error?.message || error,
        timestamp: new Date().toISOString(),
      });
    }
  }
}

// Export singleton instance
export const logger = new Logger();

// Export type for context
export type { LogContext };

// Declare Sentry on window for TypeScript
declare global {
  interface Window {
    Sentry?: any;
  }
}
