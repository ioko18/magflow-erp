/**
 * Custom hook for handling price input with support for both dot and comma separators
 * Maintains input as string for free editing, converts to number only when needed
 */

import { useState, useCallback } from 'react';

export interface UsePriceInputReturn {
  displayValue: string;
  numericValue: number;
  handleChange: (inputValue: string) => void;
  reset: (initialValue?: number) => void;
  isValid: boolean;
}

/**
 * Hook for managing price input state
 * @param initialValue - Initial numeric value
 * @returns Object with display value, numeric value, and handlers
 */
export const usePriceInput = (initialValue: number = 0): UsePriceInputReturn => {
  // Store as string to preserve user input format
  const [displayValue, setDisplayValue] = useState<string>(initialValue.toFixed(2));
  const [isValid, setIsValid] = useState<boolean>(true);

  // Regex to validate price format: digits, optional separator (. or ,), optional digits
  const priceRegex = /^\d*[.,]?\d*$/;

  const handleChange = useCallback((inputValue: string) => {
    // Allow empty string for clearing
    if (inputValue === '') {
      setDisplayValue('');
      setIsValid(true);
      return;
    }

    // Validate format
    if (!priceRegex.test(inputValue)) {
      setIsValid(false);
      return;
    }

    // Check for multiple separators
    const separatorCount = (inputValue.match(/[.,]/g) || []).length;
    if (separatorCount > 1) {
      setIsValid(false);
      return;
    }

    // Valid input
    setDisplayValue(inputValue);
    setIsValid(true);
  }, []);

  const numericValue = useCallback((): number => {
    if (displayValue === '' || displayValue === undefined) {
      return 0;
    }
    // Normalize: replace comma with dot
    const normalized = displayValue.replace(',', '.');
    const parsed = parseFloat(normalized);
    return isNaN(parsed) ? 0 : parsed;
  }, [displayValue])();

  const reset = useCallback((initialValue: number = 0) => {
    setDisplayValue(initialValue.toFixed(2));
    setIsValid(true);
  }, []);

  return {
    displayValue,
    numericValue,
    handleChange,
    reset,
    isValid,
  };
};
