import { apiClient } from './client';
import type { Category, PriceHistory, Product } from '../types';

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
};

