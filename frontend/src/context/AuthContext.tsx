import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  needsSetup: boolean;
  checkSetupStatus: () => Promise<boolean>;
  login: (accessToken: string, refreshToken: string, userData: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [needsSetup, setNeedsSetup] = useState<boolean>(false);

  const checkSetupStatus = async (): Promise<boolean> => {
    try {
      const response = await apiClient.get<{ needs_setup: boolean }>('/auth/setup-status');
      const isNeeded = !!response.data.needs_setup;
      setNeedsSetup(isNeeded);
      return isNeeded;
    } catch {
      return false;
    }
  };

  useEffect(() => {
    checkSetupStatus();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await apiClient.get<User>('/auth/me');
      setUser(response.data);
    } catch {
      setUser(null);
      setToken(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    } else {
      setIsLoading(false);
    }
  }, [token]);

  const login = (accessToken: string, refreshToken: string, userData: User) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    setToken(accessToken);
    setUser(userData);
    setNeedsSetup(false);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('active_household_id');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        needsSetup,
        checkSetupStatus,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
