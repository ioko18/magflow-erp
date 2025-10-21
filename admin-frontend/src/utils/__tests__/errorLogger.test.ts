/**
 * Tests for Error Logger Utility
 *
 * Ensures centralized logging works correctly across the application
 */

// @vitest-environment jsdom

/// <reference types="vitest" />

import { errorLogger, logError, logWarning, logInfo } from '../errorLogger';

// Define global types for testing
declare global {
  var Storage: {
    prototype: Storage;
    new(): Storage;
  };
}

// Ensure Vitest globals are available
declare const vi: typeof import('vitest').vi;
declare const describe: typeof import('vitest').describe;
declare const it: typeof import('vitest').it;
declare const expect: typeof import('vitest').expect;
declare const beforeEach: typeof import('vitest').beforeEach;
declare const afterEach: typeof import('vitest').afterEach;

describe('ErrorLogger', () => {
  let consoleErrorSpy: any;
  let consoleWarnSpy: any;
  let consoleInfoSpy: any;
  let localStorageMock: { [key: string]: string };

  beforeEach(() => {
    // Mock console methods
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    consoleInfoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});

    // Mock localStorage
    localStorageMock = {};
    global.Storage.prototype.getItem = vi.fn((key: string) => localStorageMock[key] || null);
    global.Storage.prototype.setItem = vi.fn((key: string, value: string) => {
      localStorageMock[key] = value;
    });
    global.Storage.prototype.removeItem = vi.fn((key: string) => {
      delete localStorageMock[key];
    });

    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost:3000/test' },
      writable: true,
    });

    // Mock navigator
    Object.defineProperty(window, 'navigator', {
      value: { userAgent: 'test-agent' },
      writable: true,
    });

    // Clear stored errors before each test
    errorLogger.clearStoredErrors();
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleInfoSpy.mockRestore();
    vi.clearAllMocks();
  });

  describe('logError', () => {
    it('should log error with context', () => {
      const error = new Error('Test error');
      const context = { component: 'TestComponent', action: 'testAction' };

      logError(error, context);

      expect(consoleErrorSpy).toHaveBeenCalled();
      const loggedData = consoleErrorSpy.mock.calls[0][1];
      expect(loggedData.message).toBe('Test error');
      expect(loggedData.context).toEqual(context);
      expect(loggedData.level).toBe('error');
    });

    it('should handle non-Error objects', () => {
      const errorString = 'String error';

      logError(errorString);

      expect(consoleErrorSpy).toHaveBeenCalled();
      const loggedData = consoleErrorSpy.mock.calls[0][1];
      expect(loggedData.message).toBe('String error');
    });

    it('should include stack trace for Error objects', () => {
      const error = new Error('Test error with stack');

      logError(error);

      expect(consoleErrorSpy).toHaveBeenCalled();
      const loggedData = consoleErrorSpy.mock.calls[0][1];
      expect(loggedData.stack).toBeDefined();
    });

    it('should include timestamp and user agent', () => {
      const error = new Error('Test error');

      logError(error);

      expect(consoleErrorSpy).toHaveBeenCalled();
      const loggedData = consoleErrorSpy.mock.calls[0][1];
      expect(loggedData.timestamp).toBeDefined();
      expect(loggedData.userAgent).toBeDefined();
    });
  });

  describe('logWarning', () => {
    it('should log warning with context', () => {
      const message = 'Test warning';
      const context = { component: 'TestComponent' };

      logWarning(message, context);

      expect(consoleWarnSpy).toHaveBeenCalled();
      const loggedData = consoleWarnSpy.mock.calls[0][1];
      expect(loggedData.message).toBe(message);
      expect(loggedData.context).toEqual(context);
      expect(loggedData.level).toBe('warning');
    });

    it('should include timestamp', () => {
      logWarning('Test warning');

      expect(consoleWarnSpy).toHaveBeenCalled();
      const loggedData = consoleWarnSpy.mock.calls[0][1];
      expect(loggedData.timestamp).toBeDefined();
    });
  });

  describe('logInfo', () => {
    it('should log info message with context', () => {
      const message = 'Test info';
      const context = { component: 'TestComponent', userId: '123' };

      logInfo(message, context);

      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should work without context', () => {
      logInfo('Simple info message');

      expect(consoleInfoSpy).toHaveBeenCalled();
    });
  });

  describe('Error Storage', () => {
    it('should store errors in localStorage (production mode)', () => {
      // Mock import.meta.env.DEV directly
      const originalImportMeta = (global as any).import?.meta;
      (global as any).import = {
        meta: {
          env: { DEV: false }
        }
      };

      const error = new Error('Test error for storage');
      logError(error);

      const storedErrors = errorLogger.getStoredErrors();
      expect(storedErrors.length).toBeGreaterThan(0);

      // Restore original
      if (originalImportMeta) {
        (global as any).import.meta = originalImportMeta;
      }
    });

    it('should limit stored errors to 50', () => {
      // Mock import.meta.env.DEV directly
      (global as any).import = {
        meta: {
          env: { DEV: false }
        }
      };

      // Log 60 errors
      for (let i = 0; i < 60; i++) {
        logError(new Error(`Error ${i}`));
      }

      const storedErrors = errorLogger.getStoredErrors();
      expect(storedErrors.length).toBeLessThanOrEqual(50);

      // Restore original
      (global as any).import = {
        meta: {
          env: { DEV: true }
        }
      };
    });

    it('should clear stored errors', () => {
      logError(new Error('Test error'));

      errorLogger.clearStoredErrors();

      const storedErrors = errorLogger.getStoredErrors();
      expect(storedErrors.length).toBe(0);
    });
  });

  describe('Context Handling', () => {
    it('should handle complex context objects', () => {
      const error = new Error('Test error');
      const context = {
        component: 'ComplexComponent',
        action: 'complexAction',
        metadata: {
          userId: '123',
          sessionId: 'abc-def',
          nested: {
            value: 42
          }
        }
      };

      logError(error, context);

      expect(consoleErrorSpy).toHaveBeenCalled();
      const loggedData = consoleErrorSpy.mock.calls[0][1];
      expect(loggedData.context).toEqual(context);
    });

    it('should handle undefined context gracefully', () => {
      const error = new Error('Test error');

      expect(() => logError(error)).not.toThrow();
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('Error Formatting', () => {
    it('should format error with all required fields', () => {
      const error = new Error('Formatted error');
      const context = { component: 'TestComponent' };

      logError(error, context);

      const loggedData = consoleErrorSpy.mock.calls[0][1];
      expect(loggedData).toHaveProperty('level');
      expect(loggedData).toHaveProperty('message');
      expect(loggedData).toHaveProperty('stack');
      expect(loggedData).toHaveProperty('context');
      expect(loggedData).toHaveProperty('timestamp');
      expect(loggedData).toHaveProperty('userAgent');
      expect(loggedData).toHaveProperty('url');
    });

    it('should include current URL', () => {
      const error = new Error('Test error');

      logError(error);

      const loggedData = consoleErrorSpy.mock.calls[0][1];
      expect(loggedData.url).toBe(window.location.href);
    });
  });
});
