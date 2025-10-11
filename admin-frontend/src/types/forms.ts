/**
 * Form-related types
 */

// Form field error
export interface FieldError {
  message: string;
  type?: string;
}

// Form errors
export type FormErrors<T> = Partial<Record<keyof T, FieldError | string>>;

// Form state
export interface FormState<T> {
  values: T;
  errors: FormErrors<T>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isValid: boolean;
}

// Form field props
export interface FormFieldProps<T = any> {
  name: string;
  value: T;
  error?: string;
  touched?: boolean;
  onChange: (value: T) => void;
  onBlur?: () => void;
}

// Select option
export interface SelectOption<T = any> {
  label: string;
  value: T;
  disabled?: boolean;
  icon?: React.ReactNode;
}

// File upload
export interface FileUpload {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  url?: string;
}
