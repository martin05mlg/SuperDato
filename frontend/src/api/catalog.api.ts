import { apiClient } from './client';
import type {
  Category,
  MercadonaEnrichResponse,
  MercadonaOnlineProduct,
  MercadonaSuggestionItem,
  MercadonaSyncResponse,
  PriceHistory,
  Product,
} from '../types';

export interface ProductFilters {
  category_id?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export const catalogApi = {
  getCategories: async (): Promise<Category[]> => {
    const res = await apiClient.get<Category[]>('/catalog/categories');
    return res.data;
  },

  getProducts: async (filters?: ProductFilters): Promise<Product[]> => {
    const res = await apiClient.get<Product[]>('/catalog/products', {
      params: filters,
    });
    return res.data;
  },

  getProduct: async (id: string): Promise<Product> => {
    const res = await apiClient.get<Product>(`/catalog/products/${id}`);
    return res.data;
  },

  getPriceHistory: async (productId: string, householdId?: string): Promise<PriceHistory> => {
    const res = await apiClient.get<PriceHistory>(`/catalog/products/${productId}/price-history`, {
      params: householdId ? { household_id: householdId } : undefined,
    });
    return res.data;
  },

  createProduct: async (data: {
    canonical_name: string;
    category_id: string;
    default_unit?: string;
    format_description?: string;
    initial_alias?: string;
  }): Promise<Product> => {
    const res = await apiClient.post<Product>('/catalog/products', data);
    return res.data;
  },

  updateProduct: async (
    id: string,
    data: {
      canonical_name?: string;
      category_id?: string;
      default_unit?: string;
      format_description?: string;
    }
  ): Promise<Product> => {
    const res = await apiClient.patch<Product>(`/catalog/products/${id}`, data);
    return res.data;
  },

  addAlias: async (
    productId: string,
    data: {
      raw_name_normalized: string;
      source?: string;
    }
  ) => {
    const res = await apiClient.post(`/catalog/products/${productId}/aliases`, data);
    return res.data;
  },

  // Mercadona Online Integration
  syncMercadonaCatalog: async (postalCode?: string, limitSubcategories?: number): Promise<MercadonaSyncResponse> => {
    const res = await apiClient.post<MercadonaSyncResponse>('/catalog/mercadona/sync', {
      postal_code: postalCode,
      limit_subcategories: limitSubcategories,
    });
    return res.data;
  },

  enrichMercadonaProducts: async (autoThreshold?: number): Promise<MercadonaEnrichResponse> => {
    const res = await apiClient.post<MercadonaEnrichResponse>('/catalog/mercadona/enrich', {
      auto_threshold: autoThreshold ?? 0.85,
    });
    return res.data;
  },

  getMercadonaSuggestions: async (limitProducts?: number): Promise<MercadonaSuggestionItem[]> => {
    const res = await apiClient.get<MercadonaSuggestionItem[]>('/catalog/mercadona/suggestions', {
      params: limitProducts ? { limit_products: limitProducts } : undefined,
    });
    return res.data;
  },

  confirmMercadonaMatch: async (
    productId: string,
    params: { mercadonaOnlineId?: string; urlOrId?: string }
  ): Promise<Product> => {
    const res = await apiClient.post<Product>('/catalog/mercadona/confirm-match', {
      product_id: productId,
      mercadona_online_id: params.mercadonaOnlineId,
      url_or_id: params.urlOrId,
    });
    return res.data;
  },

  rejectMercadonaMatch: async (productId: string): Promise<Product> => {
    const res = await apiClient.post<Product>('/catalog/mercadona/reject-match', {
      product_id: productId,
    });
    return res.data;
  },

  searchMercadonaOnline: async (query: string): Promise<MercadonaOnlineProduct[]> => {
    const res = await apiClient.get<MercadonaOnlineProduct[]>('/catalog/mercadona/search', {
      params: { query },
    });
    return res.data;
  },

  recategorizeAll: async (onlyOtros: boolean = true) => {
    const res = await apiClient.post('/catalog/recategorize-all', null, {
      params: { only_otros: onlyOtros },
    });
    return res.data;
  },
};

