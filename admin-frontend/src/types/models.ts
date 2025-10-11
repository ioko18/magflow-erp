/**
 * Core data models and interfaces
 */

// Base interfaces
export interface BaseModel {
  id: number;
  created_at?: string;
  updated_at?: string;
}

// Product interfaces
export interface Product extends BaseModel {
  name: string;
  sku: string;
  price: number;
  stock: number;
  category_id?: number;
  supplier_id?: number;
  chinese_name?: string;
  specifications?: Record<string, any>;
  status?: ProductStatus;
  images?: string[];
  description?: string;
}

export interface ProductFilters {
  search?: string;
  category_id?: number;
  supplier_id?: number;
  status?: ProductStatus;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  page?: number;
  limit?: number;
}

// Supplier interfaces
export interface Supplier extends BaseModel {
  name: string;
  code?: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  is_active?: boolean;
  country?: string;
  tax_id?: string;
}

export interface SupplierProduct extends BaseModel {
  supplier_id: number;
  product_id?: number;
  supplier_sku: string;
  supplier_price: number;
  supplier_name?: string;
  chinese_name?: string;
  specifications?: Record<string, any>;
  is_matched?: boolean;
  confidence_score?: number;
  match_status?: MatchStatus;
}

// Order interfaces
export interface Order extends BaseModel {
  order_number: string;
  customer_id?: number;
  customer_name?: string;
  customer_email?: string;
  customer_phone?: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  total_amount: number;
  shipping_address?: string;
  billing_address?: string;
  notes?: string;
  items?: OrderItem[];
}

export interface OrderItem extends BaseModel {
  order_id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  price: number;
  total: number;
}

// Customer interface
export interface Customer extends BaseModel {
  name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  country?: string;
  postal_code?: string;
  total_orders?: number;
  total_spent?: number;
}

// User interfaces
export interface User extends BaseModel {
  username: string;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active?: boolean;
  last_login?: string;
  permissions?: string[];
}

// Category interface
export interface Category extends BaseModel {
  name: string;
  parent_id?: number;
  description?: string;
  image?: string;
  is_active?: boolean;
  product_count?: number;
}

// Enums
export type ProductStatus = 'active' | 'inactive' | 'out_of_stock' | 'discontinued';
export type OrderStatus = 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'returned';
export type PaymentStatus = 'pending' | 'paid' | 'failed' | 'refunded';
export type MatchStatus = 'unmatched' | 'pending' | 'matched' | 'rejected';
export type UserRole = 'admin' | 'manager' | 'operator' | 'viewer';
export type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';
