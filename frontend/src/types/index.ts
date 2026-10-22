// Base and Domain TypeScript Types matching Backend Pydantic Schemas

export type Role = 'OWNER' | 'ADMIN' | 'MEMBER';
export type ReceiptStatus = 'PENDING' | 'PROCESSED' | 'REVISION_NEEDED' | 'ERROR';
export type ImportStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface HouseholdSettings {
  mercadona_online_enabled?: boolean;
  mercadona_postal_code?: string;
  [key: string]: any;
}

export interface Household {
  id: string;
  name: string;
  currency: string;
  role: Role;
  settings?: HouseholdSettings;
  created_at: string;
}

export interface HouseholdMembership {
  id: string;
  household_id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  role: Role;
  joined_at: string;
}

export interface ReceiptTaxLine {
  id: string;
  tax_rate_percent: number;
  taxable_base: number;
  tax_amount: number;
  total_with_tax: number;
}

export interface ReceiptLine {
  id: string;
  line_order: number;
  raw_description: string;
  product_id?: string | null;
  product_name?: string | null;
  category_name?: string | null;
  quantity: number;
  unit_of_measure: string;
  unit_price: number;
  discount_amount: number;
  line_total: number;
  is_weighed_item: boolean;
  weight_in_kg?: number | null;
  validation_status: string;
  is_manual_override: boolean;
  image_url?: string | null;
  brand?: string | null;
  enriched_name?: string | null;
  packaging?: string | null;
}

export interface ReceiptLineUpdate {
  raw_description?: string;
  product_name?: string;
  product_id?: string;
  category_name?: string;
  quantity?: number;
  unit_of_measure?: string;
  unit_price?: number;
  discount_amount?: number;
  line_total?: number;
}

export interface Receipt {
  id: string;
  household_id: string;
  company_name: string;
  company_cif: string;
  store_address?: string | null;
  store_city?: string | null;
  invoice_number: string;
  store_code?: string | null;
  purchase_datetime: string;
  purchase_date: string;
  total_amount: number;
  payment_method?: string | null;
  card_last_four?: string | null;
  status: ReceiptStatus;
  extraction_warnings: string[];
  is_manual_override: boolean;
  created_at: string;
  lines?: ReceiptLine[];
  tax_lines?: ReceiptTaxLine[];
  lines_count?: number;
}

export interface ReceiptUpdate {
  household_id?: string;
  store_address?: string;
  store_city?: string;
  purchase_date?: string;
  total_amount?: number;
  status?: string;
}

export type ReceiptResponse = Receipt;

export interface Category {
  id: string;
  parent_id?: string | null;
  name: string;
  slug: string;
  icon?: string | null;
  color_hex?: string | null;
  is_system?: boolean;
  product_count?: number;
}

export interface Product {
  id: string;
  canonical_name: string;
  category_id: string;
  category_name?: string | null;
  category_color?: string | null;
  default_unit: string;
  format_description?: string | null;
  latest_price?: number | null;
  latest_price_per_kg_or_l?: number | null;
  latest_date?: string | null;
  observations_count?: number;
  min_price?: number | null;
  max_price?: number | null;
  aliases?: string[];
  created_at: string;
  // Mercadona Online integration
  mercadona_online_id?: string | null;
  enriched_name?: string | null;
  image_url?: string | null;
  brand?: string | null;
  packaging?: string | null;
  mercadona_url?: string | null;
  enrichment_status?: 'AUTO' | 'MANUALLY_CONFIRMED' | 'PENDING_SUGGESTION' | 'REJECTED' | 'UNMATCHED' | null;
  enrichment_confidence?: number | null;
}

export interface MercadonaOnlineProduct {
  id: string;
  display_name: string;
  slug?: string | null;
  brand?: string | null;
  packaging?: string | null;
  thumbnail_url?: string | null;
  share_url?: string | null;
  unit_price?: number | null;
  reference_price?: number | null;
  reference_format?: string | null;
  category_path?: string | null;
  warehouse_code?: string | null;
}

export interface MercadonaSyncResponse {
  warehouse_code: string;
  subcategories_processed: number;
  products_upserted: number;
  synced_at: string;
}

export interface MercadonaEnrichResponse {
  total_products_checked: number;
  auto_enriched_count: number;
  pending_suggestions_count: number;
  threshold_used: number;
}

export interface MercadonaSuggestionItem {
  product: Product;
  candidates: Array<{
    mercadona_product: MercadonaOnlineProduct;
    score: number;
    price_match?: boolean;
  }>;
}

export interface PriceObservation {
  id: string;
  household_id: string;
  product_id: string;
  receipt_line_id: string;
  observed_at: string;
  observed_date: string;
  unit_price: number;
  price_per_kg_or_l?: number | null;
  store_code?: string | null;
  raw_description?: string | null;
}

export interface PriceHistory {
  product_id: string;
  product_name: string;
  category_name?: string | null;
  category_color?: string | null;
  default_unit: string;
  current_price?: number | null;
  min_price?: number | null;
  max_price?: number | null;
  price_change_pct?: number | null;
  observations: PriceObservation[];
}

export interface AnalyticsSummary {
  total_spend: number;
  previous_spend: number;
  spend_variation_pct: number;
  receipt_count: number;
  average_ticket: number;
  median_ticket: number;
  total_items_count?: number;
  last_purchase_date?: string | null;
  last_sync_at?: string | null;
  period_label?: string | null;
}

export interface SpendingEvolutionPoint {
  date: string;
  total_amount: number;
  receipt_count: number;
}

export interface CategoryDistributionItem {
  category_name: string;
  color_hex: string;
  total_spend: number;
  percentage: number;
  items_count?: number;
}

export interface TopProductItem {
  product_id?: string | null;
  product_name: string;
  category_name: string;
  total_spend: number;
  total_quantity: number;
  purchases_count: number;
  average_price: number;
  image_url?: string | null;
  enriched_name?: string | null;
  brand?: string | null;
}
