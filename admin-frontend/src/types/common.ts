/**
 * Common utility types
 */

// Make all properties optional
export type Partial<T> = {
  [P in keyof T]?: T[P];
};

// Make all properties required
export type Required<T> = {
  [P in keyof T]-?: T[P];
};

// Pick specific properties
export type Pick<T, K extends keyof T> = {
  [P in K]: T[P];
};

// Omit specific properties
export type Omit<T, K extends keyof T> = Pick<T, Exclude<keyof T, K>>;

// Nullable type
export type Nullable<T> = T | null;

// Maybe type
export type Maybe<T> = T | null | undefined;

// Dictionary type
export type Dictionary<T = any> = Record<string, T>;

// ID type
export type ID = number | string;

// Timestamp
export type Timestamp = string | Date;

// Callback types
export type Callback = () => void;
export type CallbackWithParam<T> = (param: T) => void;
export type AsyncCallback = () => Promise<void>;
export type AsyncCallbackWithParam<T> = (param: T) => Promise<void>;

// Component props with children
export interface WithChildren {
  children?: React.ReactNode;
}

// Component props with className
export interface WithClassName {
  className?: string;
}

// Loading state
export interface LoadingState {
  loading: boolean;
  error?: string | null;
}

// Pagination state
export interface PaginationState {
  page: number;
  limit: number;
  total: number;
}

// Sort state
export interface SortState<T = string> {
  field: T;
  order: 'asc' | 'desc';
}

// Filter state
export type FilterState<T> = Partial<T>;

// Table column
export interface TableColumn<T = any> {
  key: string;
  title: string;
  dataIndex?: keyof T;
  render?: (value: any, record: T, index: number) => React.ReactNode;
  sortable?: boolean;
  filterable?: boolean;
  width?: number | string;
  align?: 'left' | 'center' | 'right';
}

// Action button
export interface ActionButton {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
  disabled?: boolean;
  loading?: boolean;
}
