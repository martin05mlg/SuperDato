import { apiClient } from './client';
import type {
  ShoppingItem,
  ShoppingListSummary,
  ShoppingSuggestion,
  ShoppingItemCreatePayload,
  ShoppingItemUpdatePayload,
} from '../types';

export const shoppingApi = {
  getList: async (householdId: string): Promise<ShoppingListSummary> => {
    const res = await apiClient.get<ShoppingListSummary>('/shopping/items', {
      params: { household_id: householdId },
    });
    return res.data;
  },

  addItem: async (data: ShoppingItemCreatePayload): Promise<ShoppingItem> => {
    const res = await apiClient.post<ShoppingItem>('/shopping/items', data);
    return res.data;
  },

  updateItem: async (
    itemId: string,
    householdId: string,
    data: ShoppingItemUpdatePayload
  ): Promise<ShoppingItem> => {
    const res = await apiClient.patch<ShoppingItem>(`/shopping/items/${itemId}`, data, {
      params: { household_id: householdId },
    });
    return res.data;
  },

  deleteItem: async (itemId: string, householdId: string): Promise<void> => {
    await apiClient.delete(`/shopping/items/${itemId}`, {
      params: { household_id: householdId },
    });
  },

  clearChecked: async (householdId: string): Promise<{ cleared_count: number }> => {
    const res = await apiClient.post<{ cleared_count: number }>(
      '/shopping/clear-checked',
      {},
      { params: { household_id: householdId } }
    );
    return res.data;
  },

  getSuggestions: async (householdId: string): Promise<ShoppingSuggestion[]> => {
    const res = await apiClient.get<ShoppingSuggestion[]>('/shopping/suggestions', {
      params: { household_id: householdId },
    });
    return res.data;
  },
};

