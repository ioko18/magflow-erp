/**
 * Object manipulation helpers
 */

export const objectHelpers = {
  /**
   * Deep clone object
   */
  deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
  },

  /**
   * Pick specific keys from object
   */
  pick<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
    const result = {} as Pick<T, K>;
    keys.forEach(key => {
      if (key in obj) {
        result[key] = obj[key];
      }
    });
    return result;
  },

  /**
   * Omit specific keys from object
   */
  omit<T extends object, K extends keyof T>(obj: T, keys: K[]): Omit<T, K> {
    const result = { ...obj };
    keys.forEach(key => {
      delete result[key];
    });
    return result;
  },

  /**
   * Check if object is empty
   */
  isEmpty(obj: object): boolean {
    return Object.keys(obj).length === 0;
  },

  /**
   * Merge objects deeply
   */
  deepMerge<T extends object>(target: T, ...sources: Partial<T>[]): T {
    if (!sources.length) return target;
    
    const source = sources.shift();
    if (!source) return target;

    for (const key in source) {
      const targetValue = target[key];
      const sourceValue = source[key];

      if (
        sourceValue &&
        typeof sourceValue === 'object' &&
        !Array.isArray(sourceValue)
      ) {
        if (!targetValue || typeof targetValue !== 'object') {
          (target as any)[key] = {};
        }
        objectHelpers.deepMerge(
          (target as any)[key],
          sourceValue as any
        );
      } else {
        (target as any)[key] = sourceValue;
      }
    }

    return objectHelpers.deepMerge(target, ...sources);
  },

  /**
   * Get nested property value safely
   */
  getNestedValue<T>(obj: any, path: string, defaultValue?: T): T | undefined {
    const keys = path.split('.');
    let result = obj;

    for (const key of keys) {
      if (result === null || result === undefined) {
        return defaultValue;
      }
      result = result[key];
    }

    return result !== undefined ? result : defaultValue;
  },

  /**
   * Set nested property value
   */
  setNestedValue(obj: any, path: string, value: any): void {
    const keys = path.split('.');
    const lastKey = keys.pop()!;
    let current = obj;

    for (const key of keys) {
      if (!(key in current) || typeof current[key] !== 'object') {
        current[key] = {};
      }
      current = current[key];
    }

    current[lastKey] = value;
  },

  /**
   * Compare two objects for equality
   */
  isEqual(obj1: any, obj2: any): boolean {
    return JSON.stringify(obj1) === JSON.stringify(obj2);
  },
};
