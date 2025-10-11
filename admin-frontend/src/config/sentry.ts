/**
 * Sentry Configuration for Error Tracking
 * 
 * Provides centralized error tracking and performance monitoring
 * for the MagFlow ERP frontend application.
 */

import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

/**
 * Initialize Sentry for error tracking and performance monitoring
 */
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  const environment = import.meta.env.VITE_ENVIRONMENT || 'development';
  const release = `magflow-admin@${import.meta.env.VITE_APP_VERSION || '1.0.0'}`;

  // Only initialize in production or if explicitly enabled
  if (!dsn) {
    console.info('Sentry DSN not configured, error tracking disabled');
    return;
  }

  try {
    Sentry.init({
      dsn,
      environment,
      release,
      
      // Performance Monitoring and Integrations
      integrations: [
        new BrowserTracing({
          tracingOrigins: ['localhost', /^\//],
          // routingInstrumentation will be set up separately with React Router
        }),
        new Sentry.Integrations.Breadcrumbs({
          console: true,
          dom: true,
          fetch: true,
          history: true,
          sentry: true,
          xhr: true,
        }),
      ],

      // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring
      tracesSampleRate: environment === 'production' ? 0.1 : 1.0,

      // Set sample rate for error events
      sampleRate: environment === 'production' ? 1.0 : 1.0,

      // Filter out sensitive data
      beforeSend(event: Sentry.Event, _hint: Sentry.EventHint) {
        // Don't send events in development unless explicitly enabled
        if (environment === 'development' && !import.meta.env.VITE_SENTRY_DEBUG) {
          return null;
        }

        // Filter out sensitive information
        if (event.request) {
          // Remove sensitive headers
          if (event.request.headers) {
            delete event.request.headers['Authorization'];
            delete event.request.headers['Cookie'];
          }

          // Remove sensitive query parameters
          if (event.request.query_string && typeof event.request.query_string === 'string') {
            const sensitiveParams = ['token', 'password', 'api_key', 'secret'];
            let queryString = event.request.query_string;
            sensitiveParams.forEach(param => {
              if (queryString.includes(param)) {
                queryString = queryString.replace(
                  new RegExp(`${param}=[^&]*`, 'gi'),
                  `${param}=[REDACTED]`
                );
              }
            });
            event.request.query_string = queryString;
          }
        }

        // Add custom context
        if (event.extra) {
          event.extra.userAgent = navigator.userAgent;
          event.extra.timestamp = new Date().toISOString();
        }

        return event;
      },

      // Ignore specific errors
      ignoreErrors: [
        // Browser extensions
        'top.GLOBALS',
        'chrome-extension://',
        'moz-extension://',
        // Network errors
        'Network request failed',
        'NetworkError',
        // Common non-critical errors
        'ResizeObserver loop limit exceeded',
        'Non-Error promise rejection captured',
      ],

      // Set user context
      beforeBreadcrumb(breadcrumb: Sentry.Breadcrumb) {
        // Filter out noisy breadcrumbs
        if (breadcrumb.category === 'console' && breadcrumb.level === 'log') {
          return null;
        }
        return breadcrumb;
      },
    });

    console.info('Sentry initialized successfully');
  } catch (error) {
    console.error('Failed to initialize Sentry:', error);
  }
}

/**
 * Set user context for Sentry
 */
export function setSentryUser(user: { id: string; email?: string; username?: string }) {
  Sentry.setUser({
    id: user.id,
    email: user.email,
    username: user.username,
  });
}

/**
 * Clear user context from Sentry
 */
export function clearSentryUser() {
  Sentry.setUser(null);
}

/**
 * Add custom context to Sentry
 */
export function setSentryContext(key: string, value: any) {
  Sentry.setContext(key, value);
}

/**
 * Add breadcrumb to Sentry
 */
export function addSentryBreadcrumb(message: string, category: string, level: Sentry.SeverityLevel = 'info', data?: any) {
  Sentry.addBreadcrumb({
    message,
    category,
    level,
    data,
    timestamp: Date.now() / 1000,
  });
}

/**
 * Capture exception manually
 */
export function captureSentryException(error: Error, context?: any) {
  Sentry.captureException(error, {
    extra: context,
  });
}

/**
 * Capture message manually
 */
export function captureSentryMessage(message: string, level: Sentry.SeverityLevel = 'info', context?: any) {
  Sentry.captureMessage(message, {
    level,
    extra: context,
  });
}

/**
 * Start a new transaction for performance monitoring
 */
export function startSentryTransaction(name: string, op: string) {
  return Sentry.startTransaction({
    name,
    op,
  });
}

export default Sentry;
