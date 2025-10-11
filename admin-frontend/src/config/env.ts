/**
 * Environment Configuration
 * 
 * Centralized environment variables with type safety and validation
 */

/**
 * Environment variables interface
 */
interface EnvironmentVariables {
  // API Configuration
  apiUrl: string;
  apiTimeout: number;
  
  // App Configuration
  appName: string;
  appVersion: string;
  environment: 'development' | 'staging' | 'production';
  
  // Feature Flags
  enableDevTools: boolean;
  enableAnalytics: boolean;
  enableErrorTracking: boolean;
  
  // External Services
  sentryDsn?: string;
  googleAnalyticsId?: string;
}

/**
 * Get environment variable with fallback
 */
const getEnvVar = (key: string, defaultValue: string = ''): string => {
  return import.meta.env[key] || defaultValue;
};

/**
 * Get boolean environment variable
 */
const getEnvBool = (key: string, defaultValue: boolean = false): boolean => {
  const value = import.meta.env[key];
  if (value === undefined) return defaultValue;
  return value === 'true' || value === '1';
};

/**
 * Get number environment variable
 */
const getEnvNumber = (key: string, defaultValue: number): number => {
  const value = import.meta.env[key];
  if (value === undefined) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
};

/**
 * Environment configuration
 */
export const env: EnvironmentVariables = {
  // API Configuration
  apiUrl: getEnvVar('VITE_API_URL', 'http://localhost:8000/api/v1'),
  apiTimeout: getEnvNumber('VITE_API_TIMEOUT', 30000),
  
  // App Configuration
  appName: getEnvVar('VITE_APP_NAME', 'MagFlow ERP'),
  appVersion: getEnvVar('VITE_APP_VERSION', '3.0.0'),
  environment: (getEnvVar('VITE_ENVIRONMENT', 'development') as any),
  
  // Feature Flags
  enableDevTools: getEnvBool('VITE_ENABLE_DEV_TOOLS', import.meta.env.DEV),
  enableAnalytics: getEnvBool('VITE_ENABLE_ANALYTICS', false),
  enableErrorTracking: getEnvBool('VITE_ENABLE_ERROR_TRACKING', false),
  
  // External Services
  sentryDsn: getEnvVar('VITE_SENTRY_DSN'),
  googleAnalyticsId: getEnvVar('VITE_GA_ID'),
};

/**
 * Validate required environment variables
 */
const validateEnv = () => {
  const required: (keyof EnvironmentVariables)[] = [
    'apiUrl',
    'appName',
  ];

  const missing = required.filter(key => !env[key]);

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}`
    );
  }
};

// Validate on load
if (import.meta.env.PROD) {
  validateEnv();
}

/**
 * Helper functions
 */
export const isDevelopment = env.environment === 'development';
export const isStaging = env.environment === 'staging';
export const isProduction = env.environment === 'production';

/**
 * Log environment info in development
 */
if (isDevelopment) {
  console.log('🌍 Environment:', env);
}

export default env;
