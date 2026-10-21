import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Household } from '../types';
import { apiClient } from '../api/client';
import { useAuth } from './AuthContext';

interface HouseholdContextType {
  households: Household[];
  activeHousehold: Household | null;
  isLoading: boolean;
  setActiveHousehold: (household: Household) => void;
  refreshHouseholds: () => Promise<void>;
}

const HouseholdContext = createContext<HouseholdContextType | undefined>(undefined);

export const HouseholdProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [households, setHouseholds] = useState<Household[]>([]);
  const [activeHousehold, setActiveHouseholdState] = useState<Household | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchHouseholds = async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const response = await apiClient.get<Household[]>('/households');
      setHouseholds(response.data);

      const storedId = localStorage.getItem('active_household_id');
      const found = response.data.find((h) => h.id === storedId);

      if (found) {
        setActiveHouseholdState(found);
      } else if (response.data.length > 0) {
        setActiveHouseholdState(response.data[0]);
        localStorage.setItem('active_household_id', response.data[0].id);
      } else {
        setActiveHouseholdState(null);
      }
    } catch {
      setHouseholds([]);
      setActiveHouseholdState(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchHouseholds();
    } else {
      setHouseholds([]);
      setActiveHouseholdState(null);
    }
  }, [isAuthenticated]);

  const setActiveHousehold = (household: Household) => {
    setActiveHouseholdState(household);
    localStorage.setItem('active_household_id', household.id);
  };

  return (
    <HouseholdContext.Provider
      value={{
        households,
        activeHousehold,
        isLoading,
        setActiveHousehold,
        refreshHouseholds: fetchHouseholds,
      }}
    >
      {children}
    </HouseholdContext.Provider>
  );
};

export const useHousehold = (): HouseholdContextType => {
  const context = useContext(HouseholdContext);
  if (!context) {
    throw new Error('useHousehold must be used within a HouseholdProvider');
  }
  return context;
};
