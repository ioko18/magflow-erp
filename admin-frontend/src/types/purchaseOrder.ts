/**
 * Purchase Order Types
 * Types for the Purchase Orders system
 */

export type PurchaseOrderStatus =
  | 'draft'
  | 'sent'
  | 'confirmed'
  | 'partially_received'
  | 'received'
  | 'cancelled';

export type UnreceivedItemStatus =
  | 'pending'
  | 'partial'
  | 'resolved'
  | 'cancelled';

export interface PurchaseOrderLine {
  id?: number;
  product_id: number;
  product?: {
    id: number;
    name: string;
    sku: string;
    image_url?: string;
  };
  quantity: number;
  received_quantity?: number;
  pending_quantity?: number;
  unit_cost: number;
  discount_percent?: number;
  tax_percent?: number;
  line_total?: number;
  notes?: string;
}

export interface PurchaseOrder {
  id?: number;
  order_number?: string;
  supplier_id: number;
  supplier?: {
    id: number;
    name: string;
    email?: string;
    phone?: string;
  };
  order_date: string;
  expected_delivery_date?: string;
  actual_delivery_date?: string;
  status: PurchaseOrderStatus;
  total_amount: number;
  tax_amount?: number;
  discount_amount?: number;
  shipping_cost?: number;
  currency: string;
  payment_terms?: string;
  notes?: string;
  delivery_address?: string;
  tracking_number?: string;
  lines: PurchaseOrderLine[];
  unreceived_items?: UnreceivedItem[];
  total_ordered_quantity?: number;
  total_received_quantity?: number;
  is_fully_received?: boolean;
  is_partially_received?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UnreceivedItem {
  id: number;
  purchase_order_id: number;
  purchase_order_item_id: number;
  product_id: number;
  product?: {
    id: number;
    name: string;
    sku: string;
  };
  ordered_quantity: number;
  received_quantity: number;
  unreceived_quantity: number;
  expected_date?: string;
  follow_up_date?: string;
  status: UnreceivedItemStatus;
  notes?: string;
  resolution_notes?: string;
  resolved_at?: string;
  resolved_by?: number;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrderHistory {
  id: number;
  purchase_order_id: number;
  action: string;
  old_status?: string;
  new_status?: string;
  notes?: string;
  changed_by?: number;
  changed_at: string;
  extra_data?: Record<string, any>;
}

export interface SupplierStatistics {
  supplier_id: number;
  supplier_name: string;
  total_orders: number;
  total_value: number;
  average_order_value: number;
  on_time_delivery_rate: number;
  pending_orders: number;
  completed_orders: number;
  cancelled_orders: number;
}

export interface PendingOrder {
  purchase_order_id: number;
  order_number: string;
  supplier_id: number;
  supplier_name: string;
  ordered_quantity: number;
  received_quantity: number;
  pending_quantity: number;
  expected_delivery_date?: string;
  order_date?: string;
  status: PurchaseOrderStatus;
}

export interface LowStockProductWithPO {
  // Existing low stock fields
  product_id: number;
  name: string;
  sku: string;
  current_stock: number;
  reorder_point: number;
  reorder_quantity: number;
  
  // New PO fields
  pending_orders?: PendingOrder[];
  total_pending_quantity?: number;
  adjusted_reorder_quantity?: number;
  has_pending_orders?: boolean;
  
  // Supplier info
  suppliers?: Array<{
    supplier_id: number;
    supplier_name: string;
    unit_cost: number;
    lead_time_days?: number;
  }>;
}

// API Request/Response types
export interface CreatePurchaseOrderRequest {
  supplier_id: number;
  order_date: string;
  expected_delivery_date?: string;
  currency?: string;
  payment_terms?: string;
  notes?: string;
  delivery_address?: string;
  lines: Array<{
    product_id: number;
    quantity: number;
    unit_cost: number;
    discount_percent?: number;
    tax_percent?: number;
    notes?: string;
  }>;
}

export interface UpdatePurchaseOrderStatusRequest {
  status: PurchaseOrderStatus;  // Backend expects 'status', not 'new_status'
  notes?: string;
  metadata?: Record<string, any>;
}

export interface ReceivePurchaseOrderRequest {
  receipt_date: string;
  lines: Array<{
    purchase_order_line_id: number;
    received_quantity: number;
    notes?: string;
  }>;
  notes?: string;
}

export interface ResolveUnreceivedItemRequest {
  resolution_notes: string;
  resolved_by: number;
}

export interface PurchaseOrderListParams {
  skip?: number;
  limit?: number;
  status?: PurchaseOrderStatus;
  supplier_id?: number;
  search?: string;
  order_date_from?: string;
  order_date_to?: string;
}

export interface UnreceivedItemsListParams {
  skip?: number;
  limit?: number;
  status?: UnreceivedItemStatus;
  supplier_id?: number;
}

// API Response wrapper
export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: string;
  message?: string;
}
