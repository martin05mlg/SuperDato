import { apiClient } from './client';
import type {
  Receipt,
  ReceiptResponse,
  ReceiptLine,
  ReceiptLineUpdate,
  ReceiptUpdate,
  AnalyticsSummary,
  CategoryDistributionItem,
  SpendingEvolutionPoint,
  TopProductItem,
} from '../types';

export interface AnalyticsFilterParams {
  household_id?: string;
  start_date?: string;
  end_date?: string;
}

export const receiptsApi = {
  getAll: async (params?: AnalyticsFilterParams): Promise<ReceiptResponse[]> => {
    const res = await apiClient.get<ReceiptResponse[]>('/receipts', { params });
    return res.data;
  },

  getById: async (id: string): Promise<Receipt> => {
    const res = await apiClient.get<Receipt>(`/receipts/${id}`);
    return res.data;
  },

  updateReceipt: async (id: string, data: ReceiptUpdate): Promise<Receipt> => {
    const res = await apiClient.patch<Receipt>(`/receipts/${id}`, data);
    return res.data;
  },

  updateLine: async (receiptId: string, lineId: string, data: ReceiptLineUpdate): Promise<ReceiptLine> => {
    const res = await apiClient.patch<ReceiptLine>(`/receipts/${receiptId}/lines/${lineId}`, data);
    return res.data;
  },

  uploadPdf: async (file: File): Promise<Receipt> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<Receipt>('/receipts/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  getAnalyticsSummary: async (params?: AnalyticsFilterParams): Promise<AnalyticsSummary> => {
    const res = await apiClient.get<AnalyticsSummary>('/analytics/summary', { params });
    return res.data;
  },

  getCategoryDistribution: async (params?: AnalyticsFilterParams): Promise<CategoryDistributionItem[]> => {
    const res = await apiClient.get<CategoryDistributionItem[]>('/analytics/category-distribution', { params });
    return res.data;
  },

  getSpendingEvolution: async (params?: AnalyticsFilterParams): Promise<SpendingEvolutionPoint[]> => {
    const res = await apiClient.get<SpendingEvolutionPoint[]>('/analytics/spending-evolution', { params });
    return res.data;
  },

  getTopProducts: async (params?: AnalyticsFilterParams & { limit?: number }): Promise<TopProductItem[]> => {
    const res = await apiClient.get<TopProductItem[]>('/analytics/top-products', { params });
    return res.data;
  },
};
