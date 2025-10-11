/**
 * Common validation utilities
 */

export const validators = {
  /**
   * Validate email format
   */
  isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  /**
   * Validate phone number (Romanian format)
   */
  isValidPhone(phone: string): boolean {
    const phoneRegex = /^(\+40|0)?[0-9]{9}$/;
    return phoneRegex.test(phone.replace(/\s/g, ''));
  },

  /**
   * Validate SKU format
   */
  isValidSKU(sku: string): boolean {
    return sku.length >= 3 && sku.length <= 50 && /^[A-Z0-9-_]+$/i.test(sku);
  },

  /**
   * Validate price (positive number)
   */
  isValidPrice(price: number): boolean {
    return typeof price === 'number' && price >= 0 && !isNaN(price);
  },

  /**
   * Validate stock quantity (non-negative integer)
   */
  isValidStock(stock: number): boolean {
    return Number.isInteger(stock) && stock >= 0;
  },

  /**
   * Validate required field
   */
  isRequired(value: any): boolean {
    if (typeof value === 'string') {
      return value.trim().length > 0;
    }
    return value !== null && value !== undefined;
  },

  /**
   * Validate string length
   */
  hasValidLength(value: string, min: number, max: number): boolean {
    const length = value.trim().length;
    return length >= min && length <= max;
  },

  /**
   * Validate URL format
   */
  isValidURL(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Validate Romanian VAT number (CUI)
   */
  isValidVAT(vat: string): boolean {
    const vatRegex = /^RO[0-9]{2,10}$/;
    return vatRegex.test(vat.replace(/\s/g, ''));
  },
};

/**
 * Form validation helper
 */
export const validateForm = <T extends Record<string, any>>(
  data: T,
  rules: Partial<Record<keyof T, (value: any) => string | null>>
): Record<keyof T, string | null> => {
  const errors = {} as Record<keyof T, string | null>;
  
  for (const field in rules) {
    const validator = rules[field];
    if (validator) {
      errors[field] = validator(data[field]);
    }
  }
  
  return errors;
};
