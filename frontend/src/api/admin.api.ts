import { apiClient } from './client';
import type {
  AdminStats,
  AdminUserUpdate,
  AdminHouseholdUpdate,
  RegistrationToken,
  RegistrationTokenCreate,
  SystemInfo,
  User,
  Household,
} from '../types';

export const adminApi = {
  getStats: async (): Promise<AdminStats> => {
    const res = await apiClient.get<AdminStats>('/admin/stats');
    return res.data;
  },

  getSystemInfo: async (): Promise<SystemInfo> => {
    const res = await apiClient.get<SystemInfo>('/admin/system-info');
    return res.data;
  },

  listUsers: async (): Promise<User[]> => {
    const res = await apiClient.get<User[]>('/admin/users');
    return res.data;
  },

  updateUser: async (userId: string, data: AdminUserUpdate): Promise<User> => {
    const res = await apiClient.patch<User>(`/admin/users/${userId}`, data);
    return res.data;
  },

  resetUserPassword: async (userId: string, newPassword: string):Promise<{ message: string }> => {
    const res = await apiClient.post<{ message: string }>(`/admin/users/${userId}/reset-password`, {
      new_password: newPassword,
    });
    return res.data;
  },

  deleteUser: async (userId: string): Promise<{ message: string }> => {
    const res = await apiClient.delete<{ message: string }>(`/admin/users/${userId}`);
    return res.data;
  },

  listHouseholds: async (): Promise<Household[]> => {
    const res = await apiClient.get<Household[]>('/admin/households');
    return res.data;
  },

  updateHousehold: async (householdId: string, data: AdminHouseholdUpdate): Promise<Household> => {
    const res = await apiClient.patch<Household>(`/admin/households/${householdId}`, data);
    return res.data;
  },

  deleteHousehold: async (householdId: string): Promise<{ message: string }> => {
    const res = await apiClient.delete<{ message: string }>(`/admin/households/${householdId}`);
    return res.data;
  },

  listTokens: async (): Promise<RegistrationToken[]> => {
    const res = await apiClient.get<RegistrationToken[]>('/admin/tokens');
    return res.data;
  },

  createToken: async (data: RegistrationTokenCreate): Promise<RegistrationToken> => {
    const res = await apiClient.post<RegistrationToken>('/admin/tokens', data);
    return res.data;
  },

  revokeToken: async (tokenId: string): Promise<{ message: string }> => {
    const res = await apiClient.delete<{ message: string }>(`/admin/tokens/${tokenId}`);
    return res.data;
  },
};

