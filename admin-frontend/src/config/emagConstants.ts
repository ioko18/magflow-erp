/**
 * eMAG API Constants
 * 
 * Constante pentru validarea și limitările impuse de API-ul eMAG
 * Bazate pe eMAG API v4.4.9 specifications
 */

export const EMAG_LIMITS = {
  // Field length constraints
  MAX_NAME_LENGTH: 255,
  MAX_DESCRIPTION_LENGTH: 16777215,
  MAX_BRAND_LENGTH: 255,
  MAX_PART_NUMBER_LENGTH: 25,
  MAX_URL_LENGTH: 1024,
  
  // Image constraints
  MAX_IMAGE_SIZE_MB: 8,
  MAX_IMAGE_DIMENSION: 6000,
  ALLOWED_IMAGE_FORMATS: ['.jpg', '.jpeg', '.png'],
  
  // Price constraints
  MIN_PRICE: 0.01,
  MAX_PRICE: 999999.99,
  
  // Warning thresholds (percentage of max)
  NAME_WARNING_THRESHOLD: 0.9, // 90% din limită
  DESCRIPTION_WARNING_THRESHOLD: 0.95,
} as const;

/**
 * Verifică dacă lungimea unui text depășește limita eMAG
 */
export const isTextTooLong = (text: string | null | undefined, maxLength: number): boolean => {
  if (!text) return false;
  return text.length > maxLength;
};

/**
 * Verifică dacă lungimea unui text este aproape de limită (>90%)
 */
export const isTextNearLimit = (text: string | null | undefined, maxLength: number, threshold: number = 0.9): boolean => {
  if (!text) return false;
  return text.length > maxLength * threshold;
};

/**
 * Returnează culoarea pentru tag-ul de lungime text
 */
export const getTextLengthColor = (text: string | null | undefined, maxLength: number): 'green' | 'orange' | 'red' => {
  if (!text) return 'green';
  const length = text.length;
  
  if (length > maxLength) return 'red';
  if (length > maxLength * EMAG_LIMITS.NAME_WARNING_THRESHOLD) return 'orange';
  return 'green';
};

/**
 * Returnează mesajul tooltip pentru lungimea textului
 */
export const getTextLengthTooltip = (text: string | null | undefined, maxLength: number, fieldName: string = 'Text'): string => {
  if (!text) return `Limita eMAG: ${maxLength} caractere`;
  
  const length = text.length;
  
  if (length > maxLength) {
    return `${fieldName} prea lung pentru eMAG! Limita: ${maxLength} caractere (depășire: ${length - maxLength})`;
  }
  
  if (length > maxLength * EMAG_LIMITS.NAME_WARNING_THRESHOLD) {
    return `Atenție: Aproape de limita eMAG (${maxLength} caractere). Rămân: ${maxLength - length} caractere`;
  }
  
  return `Limita eMAG: ${maxLength} caractere. Rămân: ${maxLength - length} caractere`;
};

export default EMAG_LIMITS;
