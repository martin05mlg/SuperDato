import { apiClient } from './client';
import type {
  Receipt,
  ReceiptResponse,
  AnalyticsSummary,
  CategoryDistributionItem,
  SpendingEvolutionPoint,
} from '../types';

export const receiptsApi = {
  getAll: async (): Promise<ReceiptResponse[]> => {
    const res = await apiClient.get<ReceiptResponse[]>('/receipts');
    return res.data;
  },

  getById: async (id: string): Promise<Receipt> => {
    const res = await apiClient.get<Receipt>(`/receipts/${id}`);
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

  getAnalyticsSummary: async (): Promise<AnalyticsSummary> => {
    const res = await apiClient.get<AnalyticsSummary>('/analytics/summary');
    return res.data;
  },

  getCategoryDistribution: async (): Promise<CategoryDistributionItem[]> => {
    const res = await apiClient.get<CategoryDistributionItem[]>('/analytics/category-distribution');
    return res.data;
  },

  getSpendingEvolution: async (): Promise<SpendingEvolutionPoint[]> => {
    const res = await apiClient.get<SpendingEvolutionPoint[]>('/analytics/spending-evolution');
    return res.data;
  },
};

