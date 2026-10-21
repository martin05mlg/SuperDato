import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Household } from '../types';
import { apiClient } from '../api/client';
import { useAuth } from './AuthContext';

export const DEV_HOUSEHOLD: Household = {
  id: '00000000-0000-0000-0000-000000000002',
  name: 'Casa Principal',
  currency: 'EUR',
  role: 'OWNER',
  created_at: new Date().toISOString(),
};

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
  const [households, setHouseholds] = useState<Household[]>([DEV_HOUSEHOLD]);
  const [activeHousehold, setActiveHouseholdState] = useState<Household | null>(DEV_HOUSEHOLD);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchHouseholds = async () => {
    if (!isAuthenticated) {
      setHouseholds([DEV_HOUSEHOLD]);
      setActiveHouseholdState(DEV_HOUSEHOLD);
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiClient.get<Household[]>('/households');
      if (response.data && response.data.length > 0) {
        setHouseholds(response.data);
        const storedId = localStorage.getItem('active_household_id');
        const found = response.data.find((h) => h.id === storedId);
        if (found) {
          setActiveHouseholdState(found);
        } else {
          setActiveHouseholdState(response.data[0]);
          localStorage.setItem('active_household_id', response.data[0].id);
        }
      } else {
        setHouseholds([DEV_HOUSEHOLD]);
        setActiveHouseholdState(DEV_HOUSEHOLD);
      }
    } catch {
      setHouseholds([DEV_HOUSEHOLD]);
      setActiveHouseholdState(DEV_HOUSEHOLD);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHouseholds();
  }, [isAuthenticated]);

  const setActiveHousehold = (household: Household) => {
    setActiveHouseholdState(household);
    localStorage.setItem('active_household_id', household.id);
  };

  const refreshHouseholds = async () => {
    await fetchHouseholds();
  };

  return (
    <HouseholdContext.Provider
      value={{
        households,
        activeHousehold: activeHousehold || DEV_HOUSEHOLD,
        isLoading,
        setActiveHousehold,
        refreshHouseholds,
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
