import { apiClient } from './client';
import type { Household, HouseholdMembership } from '../types';

export interface CreateHouseholdDto {
  name: string;
  currency?: string;
}

export interface InviteMemberDto {
  invited_email: string;
  role: 'ADMIN' | 'MEMBER';
}

export const householdsApi = {
  getAll: async (): Promise<Household[]> => {
    const res = await apiClient.get<Household[]>('/households');
    return res.data;
  },

  create: async (data: CreateHouseholdDto): Promise<Household> => {
    const res = await apiClient.post<Household>('/households', data);
    return res.data;
  },

  getMembers: async (householdId: string): Promise<HouseholdMembership[]> => {
    const res = await apiClient.get<HouseholdMembership[]>(`/households/${householdId}/members`);
    return res.data;
  },

  invite: async (householdId: string, data: InviteMemberDto) => {
    const res = await apiClient.post(`/households/${householdId}/invitations`, data);
    return res.data;
  },

  removeMember: async (householdId: string, userId: string) => {
    await apiClient.delete(`/households/${householdId}/members/${userId}`);
  },
};

