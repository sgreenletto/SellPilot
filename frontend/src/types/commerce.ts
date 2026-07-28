export interface Product {
  product_id: string;
  title: string;
  site: string;
  category_name: string;
  currency: string;
  price: string;
  sales_count: number;
  rating: string;
  review_count: number;
  status: string;
  is_mock_data: boolean;
}

export interface InventoryItem {
  inventory_id: string;
  sku_id: string;
  product_id: string;
  warehouse_id: string;
  available_stock: number;
  reserved_stock: number;
  safety_stock: number;
  stock_status: string;
  updated_at?: string | null;
  is_mock_data: boolean;
}

export interface Order {
  order_id: string;
  buyer_id: string;
  site: string;
  currency: string;
  order_status: string;
  payment_status: string;
  total_amount: string;
  created_at: string;
  is_mock_data: boolean;
}

export interface LogisticsTrack {
  track_id: string;
  status: string;
  location: string;
  description: string;
  event_time: string;
}

export interface Logistics {
  logistics_id: string;
  order_id: string;
  tracking_number: string;
  carrier: string;
  status: string;
  latest_location: string | null;
  tracks: LogisticsTrack[];
  is_mock_data: boolean;
}

export interface ReturnRefund {
  return_id: string;
  order_id: string;
  request_type: string;
  reason_type: string;
  amount: string;
  status: string;
  requested_at: string;
  completed_at: string | null;
  is_mock_data: boolean;
}

export interface ConfirmationTask {
  id: string;
  operation_type: string;
  target_id: string | null;
  status: string;
  idempotency_key: string;
  created_at?: string;
}

export interface SelectionCandidate {
  product_id: string;
  title: string;
  source_type: string;
  is_mock_data: boolean;
  created_at: string;
}

export interface ProductDraftPayload {
  product_id?: string;
  source_shop_id: string;
  title: string;
  category_id: string;
  category_name: string;
  description: string;
  site: string;
  currency: string;
  price: number;
  cost: number;
  shipping_cost: number;
  source_type: string;
}

export type CommerceRow = Product | InventoryItem | Order;
