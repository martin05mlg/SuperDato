import { apiClient } from './client';

export interface GoogleConnection {
  id: string;
  user_id: string;
  user_email?: string | null;
  user_full_name?: string | null;
  household_id: string;
  google_email: string;
  scopes: string[];
  initial_sync_date: string;
  last_sync_at?: string | null;
  sync_status: string;
  last_error?: string | null;
  created_at: string;
}

export interface ImportJobItem {
  id: string;
  household_id: string;
  connection_id?: string | null;
  source_type: string;
  status: string;
  messages_found: number;
  receipts_imported: number;
  receipts_skipped: number;
  errors_count: number;
  error_details: any[];
  started_at: string;
  completed_at?: string | null;
}

export const integrationsApi = {
  getGoogleAuthUrl: async (householdId: string): Promise<string> => {
    const res = await apiClient.get<{ authorization_url: string }>(
      `/integrations/google/authorize-url?household_id=${householdId}`
    );
    return res.data.authorization_url;
  },

  getGoogleStatus: async (householdId: string): Promise<GoogleConnection | null> => {
    const res = await apiClient.get<GoogleConnection | null>(
      `/integrations/google/status?household_id=${householdId}`
    );
    return res.data;
  },

  getGoogleConnections: async (householdId: string): Promise<GoogleConnection[]> => {
    const res = await apiClient.get<GoogleConnection[]>(
      `/integrations/google/connections?household_id=${householdId}`
    );
    return res.data;
  },

  connectMockGoogle: async (householdId: string, email?: string): Promise<GoogleConnection> => {
    const res = await apiClient.post<GoogleConnection>(
      `/integrations/google/connect-mock?household_id=${householdId}&email=${encodeURIComponent(
        email || 'mi.cuenta.mercadona@gmail.com'
      )}`
    );
    return res.data;
  },

  disconnectGoogle: async (householdId: string, connectionId?: string): Promise<void> => {
    const url = connectionId
      ? `/integrations/google/disconnect?household_id=${householdId}&connection_id=${connectionId}`
      : `/integrations/google/disconnect?household_id=${householdId}`;
    await apiClient.post(url);
  },

  triggerSync: async (householdId: string, connectionId?: string): Promise<ImportJobItem> => {
    const url = connectionId
      ? `/integrations/sync?household_id=${householdId}&connection_id=${connectionId}`
      : `/integrations/sync?household_id=${householdId}`;
    const res = await apiClient.post<ImportJobItem>(url);
    return res.data;
  },

  getImportJobs: async (householdId: string): Promise<ImportJobItem[]> => {
    const res = await apiClient.get<ImportJobItem[]>(
      `/integrations/imports?household_id=${householdId}`
    );
    return res.data;
  },
};
